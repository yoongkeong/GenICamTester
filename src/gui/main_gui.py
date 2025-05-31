# main_gui.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QStackedWidget, QDialog, QLineEdit, QDialogButtonBox, QFormLayout, 
    QMessageBox, QGroupBox
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
import cv2
import numpy as np
from gui.presenter import CameraPresenter

class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.presenter = CameraPresenter(self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("GenICam Camera Tester")
        self.setGeometry(100, 100, 1024, 768)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.stacked_widget = QStackedWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.addWidget(self.stacked_widget)

        self.init_camera_detection_page()
        self.init_test_selection_page()
        self.init_live_view_page()

        self.stacked_widget.setCurrentWidget(self.camera_detection_page)

    def init_camera_detection_page(self):
        self.camera_detection_page = QWidget()
        layout = QVBoxLayout(self.camera_detection_page)
        
        title = QLabel("Camera Detection")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("Select camera interface:")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        
        self.usb_button = QPushButton("Detect USB Camera")
        self.usb_button.clicked.connect(self.presenter.detect_usb_camera)
        button_layout.addWidget(self.usb_button)

        self.gige_button = QPushButton("Detect GigE Camera")
        self.gige_button.clicked.connect(self.prompt_gige_configuration)
        button_layout.addWidget(self.gige_button)

        layout.addLayout(button_layout)
        self.stacked_widget.addWidget(self.camera_detection_page)

    def prompt_gige_configuration(self):
        config_dialog = CameraConfigDialog(self)
        if config_dialog.exec_() == QDialog.Accepted:
            use_dhcp, ip_settings = config_dialog.get_configuration()
            self.presenter.detect_gige_camera(use_dhcp, ip_settings)

    def init_live_view_page(self):
        self.live_view_page = QWidget()
        layout = QVBoxLayout(self.live_view_page)

        # Camera info group
        info_group = QGroupBox("Camera Information")
        info_layout = QVBoxLayout()
        self.camera_info_label = QLabel()
        info_layout.addWidget(self.camera_info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Live view group
        view_group = QGroupBox("Live View")
        view_layout = QVBoxLayout()
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        view_layout.addWidget(self.image_label)

        # Controls
        control_layout = QHBoxLayout()
        self.live_button = QPushButton("Start Live View")
        self.live_button.clicked.connect(self.toggle_live_view)
        control_layout.addWidget(self.live_button)

        self.snap_button = QPushButton("Snap Image")
        self.snap_button.clicked.connect(self.snap_image)
        control_layout.addWidget(self.snap_button)

        view_layout.addLayout(control_layout)
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)

        # Navigation
        nav_layout = QHBoxLayout()
        back_button = QPushButton("Back to Tests")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.test_selection_page))
        nav_layout.addWidget(back_button)
        layout.addLayout(nav_layout)

        self.stacked_widget.addWidget(self.live_view_page)

    def init_test_selection_page(self):
        self.test_selection_page = QWidget()
        layout = QVBoxLayout(self.test_selection_page)

        # Add buttons for different test categories
        test_buttons = [
            ("Live View", lambda: self.stacked_widget.setCurrentWidget(self.live_view_page)),
            ("Feature Tests", self.run_feature_tests),
            ("Image Quality Tests", self.run_image_quality_tests),
            ("Performance Tests", self.run_performance_tests)
        ]

        for label, callback in test_buttons:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        self.stacked_widget.addWidget(self.test_selection_page)

    def display_camera_info(self, info):
        """Display camera information in the GUI"""
        self.camera_info_label.setText(info)

    def update_live_button_state(self, is_live):
        """Update the live view button text based on state"""
        self.live_button.setText("Stop Live View" if is_live else "Start Live View")

    def toggle_live_view(self):
        """Toggle live view on/off"""
        if self.live_button.text() == "Start Live View":
            self.presenter.start_live_grabbing()
        else:
            self.presenter.stop_live_grabbing()

    def snap_image(self):
        """Capture and save a single image"""
        pass  # TODO: Implement image capture

    def update_live_image(self, frame):
        """Update the live view with a new frame"""
        try:
            # Convert frame to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create QImage from frame
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale to fit the label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)
            
            # Display the image
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error updating live image: {str(e)}")

    def run_feature_tests(self):
        """Run feature access tests"""
        pass  # TODO: Implement feature tests

    def run_image_quality_tests(self):
        """Run image quality tests"""
        pass  # TODO: Implement image quality tests

    def run_performance_tests(self):
        """Run performance tests"""
        pass  # TODO: Implement performance tests

    def navigate_to_test_selection(self):
        """Navigate to the test selection page"""
        self.stacked_widget.setCurrentWidget(self.test_selection_page)

    def closeEvent(self, event):
        """Handle application closure"""
        self.presenter.cleanup()
        event.accept()

class CameraConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GigE Camera Configuration")
        
        # Dialog layout
        self.form_layout = QFormLayout(self)

        # DHCP option
        self.dhcp_option = QPushButton("Use DHCP")
        self.dhcp_option.clicked.connect(self.accept_dhcp)
        self.form_layout.addRow(self.dhcp_option)

        # Manual entry fields
        self.ip_address = QLineEdit()
        self.subnet_mask = QLineEdit()
        self.gateway = QLineEdit()
        self.form_layout.addRow("IP Address:", self.ip_address)
        self.form_layout.addRow("Subnet Mask:", self.subnet_mask)
        self.form_layout.addRow("Gateway:", self.gateway)

        # Dialog buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.form_layout.addRow(self.buttons)

        self.use_dhcp = True

    def accept_dhcp(self):
        self.use_dhcp = True
        self.accept()

    def accept(self):
        if not self.use_dhcp:
            if not self.ip_address.text() or not self.subnet_mask.text():
                QMessageBox.warning(self, "Input Error", "Please enter valid IP details.")
                return
        super().accept()

    def get_configuration(self):
        if self.use_dhcp:
            return True, None
        else:
            return False, {
                'ip_address': self.ip_address.text(),
                'subnet_mask': self.subnet_mask.text(),
                'gateway': self.gateway.text()
            }

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CameraTestGUI()
    gui.show()
    sys.exit(app.exec_())
