import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QMessageBox
import test_powerUSB
import test_powerGigE
import test_IO
import test_multicam
import test_imgQuality
import test_ROI
import funct_blurDetection
import funct_CalibCam
import funct_EdgeDetection
import adv_barcodeScan
import adv_textDetection


class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('GenICam Camera Testing Interface')
        self.setGeometry(100, 100, 400, 600)

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # Title label
        title_label = QLabel("GenICam Camera Test Suite", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Power Test Buttons
        layout.addWidget(QLabel("Power Tests", self).setStyleSheet("font-size: 14px;"))
        usb_button = QPushButton("Test Power (USB)", self)
        usb_button.clicked.connect(self.test_power_usb)
        layout.addWidget(usb_button)

        gige_button = QPushButton("Test Power (GigE)", self)
        gige_button.clicked.connect(self.test_power_gige)
        layout.addWidget(gige_button)

        # Basic Test Buttons
        layout.addWidget(QLabel("Basic Tests", self).setStyleSheet("font-size: 14px;"))
        io_button = QPushButton("Test I/O", self)
        io_button.clicked.connect(self.test_io)
        layout.addWidget(io_button)

        multicam_button = QPushButton("Test Multi-Camera", self)
        multicam_button.clicked.connect(self.test_multicam)
        layout.addWidget(multicam_button)

        image_quality_button = QPushButton("Test Image Quality", self)
        image_quality_button.clicked.connect(self.test_image_quality)
        layout.addWidget(image_quality_button)

        roi_button = QPushButton("Test ROI", self)
        roi_button.clicked.connect(self.test_roi)
        layout.addWidget(roi_button)

        # Functional Test Buttons
        layout.addWidget(QLabel("Functional Tests", self).setStyleSheet("font-size: 14px;"))
        blur_button = QPushButton("Blur Detection", self)
        blur_button.clicked.connect(self.blur_detection)
        layout.addWidget(blur_button)

        edge_button = QPushButton("Edge Detection", self)
        edge_button.clicked.connect(self.edge_detection)
        layout.addWidget(edge_button)

        calibration_button = QPushButton("Camera Calibration", self)
        calibration_button.clicked.connect(self.camera_calibration)
        layout.addWidget(calibration_button)

        # Advanced Test Buttons
        layout.addWidget(QLabel("Advanced Tests", self).setStyleSheet("font-size: 14px;"))
        barcode_button = QPushButton("Barcode Scanning", self)
        barcode_button.clicked.connect(self.barcode_scan)
        layout.addWidget(barcode_button)

        text_detection_button = QPushButton("Text Detection", self)
        text_detection_button.clicked.connect(self.text_detection)
        layout.addWidget(text_detection_button)

        # Exit Button
        exit_button = QPushButton("Exit", self)
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

    def show_message(self, title, message, is_error=False):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical if is_error else QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle(title)
        msg.exec_()

    def test_power_usb(self):
        try:
            test_powerUSB.test_power()
            self.show_message("Success", "USB Power Test Passed")
        except Exception as e:
            self.show_message("Error", f"USB Power Test Failed: {str(e)}", True)

    def test_power_gige(self):
        try:
            test_powerGigE.test_power()
            self.show_message("Success", "GigE Power Test Passed")
        except Exception as e:
            self.show_message("Error", f"GigE Power Test Failed: {str(e)}", True)

    def test_io(self):
        try:
            test_IO.test_io_trigger()
            self.show_message("Success", "I/O Test Passed")
        except Exception as e:
            self.show_message("Error", f"I/O Test Failed: {str(e)}", True)

    def test_multicam(self):
        try:
            test_multicam.test_multicam_acquisition()
            self.show_message("Success", "Multi-Camera Test Passed")
        except Exception as e:
            self.show_message("Error", f"Multi-Camera Test Failed: {str(e)}", True)

    def test_image_quality(self):
        try:
            test_imgQuality.test_image_quality()
            self.show_message("Success", "Image Quality Test Passed")
        except Exception as e:
            self.show_message("Error", f"Image Quality Test Failed: {str(e)}", True)

    def test_roi(self):
        try:
            test_ROI.test_roi_selection()
            self.show_message("Success", "ROI Test Passed")
        except Exception as e:
            self.show_message("Error", f"ROI Test Failed: {str(e)}", True)

    def blur_detection(self):
        try:
            funct_blurDetection.test_blur_detection()
            self.show_message("Success", "Blur Detection Test Passed")
        except Exception as e:
            self.show_message("Error", f"Blur Detection Test Failed: {str(e)}", True)

    def edge_detection(self):
        try:
            funct_EdgeDetection.test_edge_detection()
            self.show_message("Success", "Edge Detection Test Passed")
        except Exception as e:
            self.show_message("Error", f"Edge Detection Test Failed: {str(e)}", True)

    def camera_calibration(self):
        try:
            funct_CalibCam.test_camera_calibration()
            self.show_message("Success", "Camera Calibration Passed")
        except Exception as e:
            self.show_message("Error", f"Camera Calibration Failed: {str(e)}", True)

    def barcode_scan(self):
        try:
            adv_barcodeScan.test_barcode_scan()
            self.show_message("Success", "Barcode Scan Test Passed")
        except Exception as e:
            self.show_message("Error", f"Barcode Scan Test Failed: {str(e)}", True)

    def text_detection(self):
        try:
            adv_textDetection.test_text_detection()
            self.show_message("Success", "Text Detection Test Passed")
        except Exception as e:
            self.show_message("Error", f"Text Detection Test Failed: {str(e)}", True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = CameraTestGUI()
    gui.show()
    sys.exit(app.exec_())
