import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, 
    QStackedWidget
)
from PyQt5.QtCore import QDateTime

class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('GenICam Camera Testing Interface')
        self.setGeometry(100, 100, 400, 400)

        # Central widget and stacked layout
        self.central_widget = QStackedWidget(self)
        self.setCentralWidget(self.central_widget)

        # Initialize pages
        self.init_welcome_screen()
        self.init_homepage_usb()
        self.init_homepage_gige()

        # Set the initial page (Welcome screen)
        self.central_widget.setCurrentWidget(self.welcome_page)

    def init_welcome_screen(self):
        # Welcome screen layout
        self.welcome_page = QWidget(self)
        layout = QVBoxLayout(self.welcome_page)

        # Welcome text
        welcome_label = QLabel("Welcome to GenICAM Tester", self)
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(welcome_label)

        # USB and GigE Camera Buttons
        start_usb_button = QPushButton("Start Test USB Camera", self)
        start_usb_button.clicked.connect(self.start_usb_test)
        layout.addWidget(start_usb_button)

        start_gige_button = QPushButton("Start Test GigE Camera", self)
        start_gige_button.clicked.connect(self.start_gige_test)
        layout.addWidget(start_gige_button)

        # Version history
        version_label = QLabel("Version history: 2024 The end of the world", self)
        version_label.setStyleSheet("font-size: 12px; color: grey;")
        layout.addWidget(version_label)

        self.central_widget.addWidget(self.welcome_page)

    def init_homepage_usb(self):
        # USB Camera Test Homepage layout
        self.homepage_usb = QWidget(self)
        layout = QVBoxLayout(self.homepage_usb)

        # Camera detection header
        camera_detection_label = QLabel("Camera Detection (USB Camera)", self)
        camera_detection_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(camera_detection_label)

        # Button to start camera detection
        start_usb_detection_button = QPushButton("Start USB Camera Detection", self)
        start_usb_detection_button.clicked.connect(self.detect_usb_camera)
        layout.addWidget(start_usb_detection_button)

        # Area to display device information or error message
        self.device_info_usb = QLabel("", self)
        layout.addWidget(self.device_info_usb)

        # Go Back Button
        go_back_button = QPushButton("Go Back", self)
        go_back_button.clicked.connect(self.go_back)
        layout.addWidget(go_back_button)

        self.central_widget.addWidget(self.homepage_usb)

    def init_homepage_gige(self):
        # GigE Camera Test Homepage layout
        self.homepage_gige = QWidget(self)
        layout = QVBoxLayout(self.homepage_gige)

        # Camera detection header
        camera_detection_label = QLabel("Camera Detection (GigE Camera)", self)
        camera_detection_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(camera_detection_label)

        # Button to start camera detection
        start_gige_detection_button = QPushButton("Start GigE Camera Detection", self)
        start_gige_detection_button.clicked.connect(self.detect_gige_camera)
        layout.addWidget(start_gige_detection_button)

        # Area to display device information or error message
        self.device_info_gige = QLabel("", self)
        layout.addWidget(self.device_info_gige)

        # Go Back Button
        go_back_button = QPushButton("Go Back", self)
        go_back_button.clicked.connect(self.go_back)
        layout.addWidget(go_back_button)

        self.central_widget.addWidget(self.homepage_gige)

    def start_usb_test(self):
        # Navigate to USB camera test homepage
        self.central_widget.setCurrentWidget(self.homepage_usb)

    def start_gige_test(self):
        # Navigate to GigE camera test homepage
        self.central_widget.setCurrentWidget(self.homepage_gige)

    def detect_usb_camera(self):
        # Simulating USB camera detection logic
        camera_detected = True  # This will be replaced with actual detection logic

        if camera_detected:
            self.display_device_info(self.device_info_usb)
        else:
            self.device_info_usb.setText("No camera is detected, please check the following:\n"
                                         "Device Manager, Network adapters setting, etc.")

    def detect_gige_camera(self):
        # Simulating GigE camera detection logic
        camera_detected = False  # This will be replaced with actual detection logic

        if camera_detected:
            self.display_device_info(self.device_info_gige)
        else:
            self.device_info_gige.setText("No camera is detected, please check the following:\n"
                                          "Device Manager, Network adapters setting, etc.")

    def display_device_info(self, label):
        # Displaying simulated device information in table format
        current_time = QDateTime.currentDateTime()

        device_info = (
            f"Device Information:\n"
            f"DeviceID: 12345\n"
            f"Manufacturer ID: ABC Corp\n"
            f"MAC address: 00:1B:44:11:3A:B7\n"
            f"Date: {current_time.toString('yyyy-MM-dd')}\n"
            f"Time: {current_time.toString('hh:mm:ss')}"
        )
        label.setText(device_info)

    def go_back(self):
        # Navigate back to the welcome screen
        self.central_widget.setCurrentWidget(self.welcome_page)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = CameraTestGUI()
    gui.show()
    sys.exit(app.exec_())
