import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from pypylon import pylon


class CameraTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GenICam Camera Tester")
        self.setGeometry(100, 100, 800, 600)

        # Initialize camera and labels
        self.camera = None
        self.live_view_label = QLabel("Live View")
        self.image_info_label = QLabel("Image Information:\nNo image captured yet.")
        self.start_camera_button = QPushButton("Start Camera")
        self.single_grab_button = QPushButton("Single Grab & Save")

        # Setup live view label appearance
        self.live_view_label.setAlignment(Qt.AlignCenter)
        self.live_view_label.setStyleSheet("border: 1px solid black;")
        self.live_view_label.setFixedSize(400, 300)

        # Setup image info label
        self.image_info_label.setAlignment(Qt.AlignLeft)
        self.image_info_label.setStyleSheet("border: 1px solid black; padding: 5px;")
        self.image_info_label.setFixedSize(350, 300)

        # Connect buttons to actions
        self.start_camera_button.clicked.connect(self.start_camera)
        self.single_grab_button.clicked.connect(self.single_image_grab)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.start_camera_button)
        layout.addWidget(self.live_view_label)
        layout.addWidget(self.single_grab_button)
        layout.addWidget(self.image_info_label)

        # Central widget setup
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_camera(self):
        """Start and connect to the GenICam camera."""
        try:
            if self.camera is None:
                # Detect available devices and initialize camera
                devices = pylon.TlFactory.GetInstance().EnumerateDevices()
                if not devices:
                    QMessageBox.critical(self, "Error", "No camera devices found!")
                    return

                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(devices[0]))
                self.camera.Open()
                QMessageBox.information(self, "Camera Started", "Camera successfully started and connected!")
            else:
                QMessageBox.information(self, "Camera Info", "Camera is already started!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start the camera: {e}")

    def single_image_grab(self):
        """Capture a single image, display it, and ask the user if they want to save it."""
        if self.camera:
            try:
                # Try to grab a single image
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

                if grab_result is not None and grab_result.GrabSucceeded():
                    # Extract the image
                    image = grab_result.Array
                    height, width = image.shape
                    total_pixels = height * width

                    # Update the live view to display the grabbed image
                    qimage = QImage(image.data, width, height, QImage.Format_Grayscale8)
                    pixmap = QPixmap.fromImage(qimage)
                    self.live_view_label.setPixmap(pixmap)

                    # Update the image information on the UI
                    self.image_info_label.setText(
                        f"Image Information:\n"
                        f"Width: {width} px\n"
                        f"Height: {height} px\n"
                        f"Total Pixels: {total_pixels} px\n"
                    )

                    # Prompt the user if they want to save the image
                    response = QMessageBox.question(
                        self,
                        "Save Image",
                        "Do you want to save this image?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )

                    if response == QMessageBox.Yes:
                        # Ask for the file path to save
                        save_path, _ = QFileDialog.getSaveFileName(
                            self, "Save Image", "captured_image.png", "PNG Files (*.png);;All Files (*)"
                        )
                        if save_path:
                            pylon.ImagePersistence.Save(pylon.ImageFileFormat_Png, save_path, grab_result)
                            QMessageBox.information(self, "Save Successful", f"Image saved at {save_path}")
                        else:
                            print("Save operation canceled.")
                    else:
                        print("Image not saved.")
                else:
                    print("Error: Image grab failed. Please check the camera connection or settings.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Exception during image grab: {e}")
            finally:
                if grab_result is not None:
                    grab_result.Release()
        else:
            QMessageBox.warning(self, "Camera Not Started", "Please start the camera first!")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraTester()
    window.show()
    sys.exit(app.exec_())
