# main_gui_mvp.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QStackedWidget
)
from PyQt5.QtCore import QDateTime
from presenter import CameraPresenter  # Import the Presenter

class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.presenter = CameraPresenter(self)  # Initialize the presenter with the view
        self.initUI()

    def initUI(self):
        self.setWindowTitle('GenICam Camera Testing Interface')
        self.setGeometry(100, 100, 400, 400)

        self.central_widget = QStackedWidget(self)
        self.setCentralWidget(self.central_widget)

        self.init_welcome_screen()
        self.init_homepage_gige()

        self.central_widget.setCurrentWidget(self.welcome_page)

    def init_welcome_screen(self):
        self.welcome_page = QWidget(self)
        layout = QVBoxLayout(self.welcome_page)

        welcome_label = QLabel("Welcome to GenICAM Tester", self)
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(welcome_label)

        self.usb_button = QPushButton("Start Test USB Camera", self)
        self.usb_button.clicked.connect(self.presenter.detect_usb_camera)  # USB Camera button
        layout.addWidget(self.usb_button)

        self.gige_button = QPushButton("Start Test GigE Camera", self)
        self.gige_button.clicked.connect(self.start_gige_test)  # GigE Camera button
        layout.addWidget(self.gige_button)

        version_label = QLabel("Version history: 2024 The end of the world", self)
        version_label.setStyleSheet("font-size: 12px; color: grey;")
        layout.addWidget(version_label)

        self.central_widget.addWidget(self.welcome_page)

    def init_homepage_gige(self):
        self.homepage_gige = QWidget(self)
        layout = QVBoxLayout(self.homepage_gige)

        camera_detection_label = QLabel("Camera Detection (GigE Camera)", self)
        camera_detection_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(camera_detection_label)

        start_gige_detection_button = QPushButton("Start GigE Camera Detection", self)
        start_gige_detection_button.clicked.connect(self.presenter.detect_gige_camera)  # Use presenter
        layout.addWidget(start_gige_detection_button)

        self.device_info_gige = QLabel("", self)
        layout.addWidget(self.device_info_gige)

        go_back_button = QPushButton("Go Back", self)
        go_back_button.clicked.connect(self.go_back)
        layout.addWidget(go_back_button)

        self.central_widget.addWidget(self.homepage_gige)

    def start_gige_test(self):
        self.central_widget.setCurrentWidget(self.homepage_gige)

    def display_camera_info(self, info_text):
        # Display information in the GigE camera info label
        self.device_info_gige.setText(info_text)

    def go_back(self):
        self.central_widget.setCurrentWidget(self.welcome_page)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = CameraTestGUI()
    main_window.show()
    sys.exit(app.exec_())
