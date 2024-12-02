import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QTextEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from pypylon import pylon


class CameraTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GenICam Camera Tester")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize Widgets
        self.camera = None
        self.device_info_label = QLabel("Camera Information:\nNo camera connected.")
        self.live_view_label = QLabel("Live View")
        self.image_info_label = QLabel("Image Information:\nNo image captured yet.")
        self.test_log = QTextEdit()
        self.test_log.setReadOnly(True)

        self.start_camera_button = QPushButton("Start Camera")
        self.test_selector = QComboBox()
        self.run_test_button = QPushButton("Run Selected Test")

        # Populate Test Selector
        self.test_selector.addItems(
            ["Image Acquisition Test", "Max FPS Test", "Feature Access Test"]
        )

        # Style Live View
        self.live_view_label.setAlignment(Qt.AlignCenter)
        self.live_view_label.setStyleSheet("border: 1px solid black;")
        self.live_view_label.setFixedSize(400, 300)

        # Style Information Labels
        for label in [self.device_info_label, self.image_info_label]:
            label.setAlignment(Qt.AlignLeft)
            label.setStyleSheet("border: 1px solid black; padding: 10px;")

        self.device_info_label.setFixedHeight(150)
        self.image_info_label.setFixedHeight(150)

        # Layout Definitions
        main_layout = QGridLayout()

        # Top-left: Camera Information and Start Button
        top_left_layout = QVBoxLayout()
        top_left_layout.addWidget(self.device_info_label)
        top_left_layout.addWidget(self.start_camera_button)

        # Bottom-left: Image Information and Test Selection
        bottom_left_layout = QVBoxLayout()
        bottom_left_layout.addWidget(self.image_info_label)
        bottom_left_layout.addWidget(self.test_selector)
        bottom_left_layout.addWidget(self.run_test_button)

        # Left-side Layout
        left_layout = QVBoxLayout()
        left_layout.addLayout(top_left_layout)
        left_layout.addStretch()
        left_layout.addLayout(bottom_left_layout)

        # Right-side Layout: Live View and Test Log
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.live_view_label, alignment=Qt.AlignCenter)
        right_layout.addWidget(QLabel("Test Log"))
        right_layout.addWidget(self.test_log)

        # Combine Left and Right Layouts
        main_layout.addLayout(left_layout, 0, 0)
        main_layout.addLayout(right_layout, 0, 1)

        # Central Widget
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Button Connections
        self.start_camera_button.clicked.connect(self.start_camera)
        self.run_test_button.clicked.connect(self.run_selected_test)

    def log_message(self, message):
        """Log messages to the test log."""
        self.test_log.append(message)

    def start_camera(self):
        """Start and connect to the GenICam camera."""
        try:
            if self.camera is None:
                devices = pylon.TlFactory.GetInstance().EnumerateDevices()
                if not devices:
                    QMessageBox.critical(self, "Error", "No camera devices found!")
                    self.log_message("Error: No camera devices found.")
                    return

                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
                self.camera.Open()

                # Extract and display camera information
                device_info = self.camera.GetDeviceInfo()
                info_text = (
                    f"Device Info:\n"
                    f"Model Name: {device_info.GetModelName()}\n"
                    f"Manufacturer: {device_info.GetVendorName()}\n"
                    f"Serial Number: {device_info.GetSerialNumber()}\n"
                )
                if "GigE" in device_info.GetDeviceClass():
                    ip_address = device_info.GetPropertyValue("IpAddress")
                    info_text += f"IP Address: {ip_address}\n"

                self.device_info_label.setText(info_text)
                self.log_message("Camera successfully started and connected.")
            else:
                QMessageBox.information(self, "Camera Info", "Camera is already started!")
                self.log_message("Camera is already started.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start the camera: {e}")
            self.log_message(f"Error: Failed to start the camera: {e}")

    def run_selected_test(self):
        """Run the selected test based on the dropdown."""
        selected_test = self.test_selector.currentText()
        self.log_message(f"Running test: {selected_test}")

        if selected_test == "Image Acquisition Test":
            self.image_acquisition_test()
        elif selected_test == "Max FPS Test":
            self.max_fps_test()
        elif selected_test == "Feature Access Test":
            self.feature_access_test()
        else:
            self.log_message("Error: Unknown test selected.")

    def image_acquisition_test(self):
        """Test to acquire and display an image."""
        if self.camera:
            try:
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grab_result and grab_result.GrabSucceeded():
                    image = grab_result.Array
                    height, width = image.shape
                    qimage = QImage(image.data, width, height, QImage.Format_Grayscale8)
                    pixmap = QPixmap.fromImage(qimage)
                    self.live_view_label.setPixmap(pixmap)
                    self.log_message("Image Acquisition Test passed: Image displayed successfully.")
                else:
                    self.log_message("Image Acquisition Test failed: Image grab unsuccessful.")
            except Exception as e:
                self.log_message(f"Error during Image Acquisition Test: {e}")
        else:
            self.log_message("Image Acquisition Test failed: Camera not started.")

    def max_fps_test(self):
        """Test to determine the maximum FPS supported by the camera."""
        if self.camera:
            try:
                max_fps = self.camera.DeviceFrameRate.GetValue()
                self.log_message(f"Max FPS Test passed: Max FPS = {max_fps} fps.")
            except Exception as e:
                self.log_message(f"Error during Max FPS Test: {e}")
        else:
            self.log_message("Max FPS Test failed: Camera not started.")

    def feature_access_test(self):
        """Test to verify feature access on the camera."""
        if self.camera:
            try:
                features = self.camera.GetNodeMap().GetNodeNames()
                self.log_message(f"Feature Access Test passed: {len(features)} features accessible.")
            except Exception as e:
                self.log_message(f"Error during Feature Access Test: {e}")
        else:
            self.log_message("Feature Access Test failed: Camera not started.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraTester()
    window.show()
    sys.exit(app.exec_())
