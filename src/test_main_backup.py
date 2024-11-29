import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget, QLineEdit, QComboBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer
from pypylon import pylon


class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Detection and Image Acquisition")
        self.setGeometry(100, 100, 800, 600)

        # Initialize variables
        self.camera = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_live_view)

        # GUI Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Live View Label
        self.live_view_label = QLabel("Live View")
        self.live_view_label.setStyleSheet("border: 1px solid black;")
        self.live_view_label.setFixedSize(640, 480)
        self.layout.addWidget(self.live_view_label)

        # Ethernet Adapter Selector
        self.adapter_combo = QComboBox()
        self.adapter_combo.addItem("Select Ethernet Adapter")
        self.adapter_combo.addItems(self.get_ethernet_adapters())
        self.layout.addWidget(self.adapter_combo)

        # IP Range Inputs
        self.min_ip_input = QLineEdit()
        self.min_ip_input.setPlaceholderText("Min IP Range (e.g., 192.168.0.1)")
        self.layout.addWidget(self.min_ip_input)

        self.max_ip_input = QLineEdit()
        self.max_ip_input.setPlaceholderText("Max IP Range (e.g., 192.168.0.254)")
        self.layout.addWidget(self.max_ip_input)

        # Buttons
        self.detect_button = QPushButton("Detect Camera")
        self.detect_button.clicked.connect(self.detect_camera)
        self.layout.addWidget(self.detect_button)

        self.start_live_button = QPushButton("Start Live View")
        self.start_live_button.clicked.connect(self.start_live_view)
        self.start_live_button.setEnabled(False)
        self.layout.addWidget(self.start_live_button)

        self.stop_live_button = QPushButton("Stop Live View")
        self.stop_live_button.clicked.connect(self.stop_live_view)
        self.stop_live_button.setEnabled(False)
        self.layout.addWidget(self.stop_live_button)

        self.single_grab_button = QPushButton("Single Image Grab")
        self.single_grab_button.clicked.connect(self.single_image_grab)
        self.single_grab_button.setEnabled(False)
        self.layout.addWidget(self.single_grab_button)

    def get_ethernet_adapters(self):
        """Retrieve a list of Ethernet adapters available on the system."""
        try:
            import psutil
            adapters = []
            for iface, addrs in psutil.net_if_addrs().items():
                if any(addr.family == psutil.AF_INET for addr in addrs):
                    adapters.append(iface)
            return adapters
        except ImportError:
            return ["Ethernet0", "Ethernet1"]  # Fallback example adapters

    def detect_camera(self):
        """Detect cameras within the specified IP range."""
        try:
            min_ip = self.min_ip_input.text().strip()
            max_ip = self.max_ip_input.text().strip()

            if not min_ip or not max_ip:
                self.detect_button.setText("Enter valid IP range!")
                return

            # Enumerate connected devices
            devices = pylon.TlFactory.GetInstance().EnumerateDevices()
            for device in devices:
                try:
                    # Initialize the camera for any detected device
                    self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(device))
                    self.camera.Open()

                    # Update UI and enable buttons
                    self.detect_button.setText(f"Camera Detected: {device.GetModelName()}")
                    self.start_live_button.setEnabled(True)
                    self.single_grab_button.setEnabled(True)
                    return
                except Exception as e:
                    print(f"Error processing device: {e}")

            self.detect_button.setText("No Camera Detected in Range")
        except Exception as e:
            self.detect_button.setText("Error Detecting Camera")
            print(f"Error: {e}")

    def start_live_view(self):
        """Start live image view."""
        if self.camera:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.timer.start(30)  # Update every 30ms
            self.start_live_button.setEnabled(False)
            self.stop_live_button.setEnabled(True)

    def stop_live_view(self):
        """Stop live image view."""
        if self.camera and self.camera.IsGrabbing():
            self.timer.stop()
            self.camera.StopGrabbing()
            self.live_view_label.clear()
            self.start_live_button.setEnabled(True)
            self.stop_live_button.setEnabled(False)

    def update_live_view(self):
        """Update the live view with the latest image."""
        if self.camera.IsGrabbing():
            grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                height, width = image.shape
                qimage = QImage(image.data, width, height, QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimage)
                self.live_view_label.setPixmap(pixmap)
            grab_result.Release()

    def single_image_grab(self):
        """Capture a single image and save it."""
        if self.camera:
            grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                save_path = "captured_image.png"
                pylon.ImagePersistence.Save(pylon.ImageFileFormat_Png, save_path, grab_result)
                print(f"Image saved at {save_path}")
            grab_result.Release()

    def closeEvent(self, event):
        """Clean up resources on application close."""
        if self.camera:
            if self.camera.IsGrabbing():
                self.camera.StopGrabbing()
            self.camera.Close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
