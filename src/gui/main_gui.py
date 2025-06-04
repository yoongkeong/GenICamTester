# main_gui.py

import sys, time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QStackedWidget, QDialog, QLineEdit, QDialogButtonBox, QFormLayout, 
    QMessageBox, QGroupBox, QTextEdit, QProgressBar, QSpinBox, QSplitter, QFrame,
    QFileDialog
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QDateTime
import cv2
import numpy as np
from gui.presenter import CameraPresenter

class CameraSelectionDialog(QDialog):
    def __init__(self, parent=None, cameras=None):
        super().__init__(parent)
        self.cameras = cameras or []
        self.selected_camera = None
        
        self.setWindowTitle("Select Camera")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Add description
        description = QLabel("Multiple cameras found. Please select a camera to proceed:")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Create camera list group
        list_group = QGroupBox("Available Cameras")
        list_layout = QVBoxLayout()
        
        self.camera_buttons = []
        for camera in self.cameras:
            button = QPushButton()
            button.setCheckable(True)
            button.setAutoExclusive(True)  # Make buttons behave like radio buttons
            
            # Format button text with camera details
            button_text = (
                f"{camera.get('name', 'Unknown')}\n"
                f"Serial Number: {camera.get('id', 'Unknown')}\n"
                f"Interface: {camera.get('interface', 'Unknown')}"
            )
            button.setText(button_text)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    min-height: 80px;
                }
                QPushButton:checked {
                    background-color: #E3F2FD;
                    border: 2px solid #1976D2;
                }
            """)
            
            self.camera_buttons.append(button)
            list_layout.addWidget(button)
            
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Add button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def accept_selection(self):
        """Handle OK button click"""
        for button, camera in zip(self.camera_buttons, self.cameras):
            if button.isChecked():
                self.selected_camera = camera
                self.accept()
                return
        
        QMessageBox.warning(self, "Selection Required", "Please select a camera to proceed.")
        
    def get_selected_camera(self):
        """Return the selected camera info"""
        return self.selected_camera

class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_styles()
        self.setup_ui_components()
        self.presenter = CameraPresenter(self)
        
        # Initialize image update timer
        self.live_timer = QTimer()
        self.live_timer.timeout.connect(self.update_live_view)
        self.live_timer.setInterval(33)  # ~30 FPS
        
        self.initUI()

    def init_styles(self):
        """Initialize application-wide styles"""
        # Define the color palette based on Basler web theme
        self.style_dict = {
            'primary': '#00427E',      # Basler blue
            'secondary': '#005CAB',    # Lighter blue
            'success': '#4CAF50',      # Green
            'warning': '#FFC107',      # Amber
            'error': '#DC3545',        # Red
            'background': '#F8F9FA',   # Light gray
            'text': '#333333',         # Dark gray
            'border': '#E9ECEF',       # Light border
            'white': '#FFFFFF',
            'dark-bg': '#1A1A1A'       # Dark background
        }
        
        # Set application style
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.style_dict['background']};
            }}
            
            QLabel {{
                color: {self.style_dict['text']};
                font-size: 12px;
            }}
            
            QLabel[title="true"] {{
                font-size: 24px;
                font-weight: bold;
                color: {self.style_dict['primary']};
                margin: 20px;
            }}
            
            QPushButton {{
                background-color: {self.style_dict['primary']};
                color: {self.style_dict['white']};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 120px;
            }}
            
            QPushButton:hover {{
                background-color: {self.style_dict['secondary']};
            }}
            
            QPushButton:disabled {{
                background-color: {self.style_dict['border']};
            }}
            
            QGroupBox {{
                background-color: {self.style_dict['white']};
                border-radius: 8px;
                padding: 12px;
                margin-top: 16px;
                font-weight: bold;
            }}
            
            QProgressBar {{
                border: 1px solid {self.style_dict['border']};
                border-radius: 4px;
                text-align: center;
            }}
            
            QProgressBar::chunk {{
                background-color: {self.style_dict['secondary']};
            }}
        """)

    def setup_ui_components(self):
        """Initialize UI components that need to be available early"""
        # Create the log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMinimumHeight(150)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #333333;
            }
        """)

    def initUI(self):
        self.setWindowTitle("GenICam Camera Tester")
        self.setGeometry(100, 100, 1200, 800)  # Increased default size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        
        # Add logo (you can replace this with your actual logo)
        logo_label = QLabel("GenICam")
        logo_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: {self.style_dict['primary']};
        """)
        header_layout.addWidget(logo_label)
        
        # Add version info
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(f"color: {self.style_dict['secondary']};")
        header_layout.addWidget(version_label)
        header_layout.addStretch()
        
        self.main_layout.addWidget(header)

        # Create a splitter for main content and log viewer
        self.splitter = QSplitter(Qt.Vertical)
        
        # Add stacked widget to splitter
        self.stacked_widget = QStackedWidget()
        self.splitter.addWidget(self.stacked_widget)
        
        # Initialize and add log viewer
        self.init_log_viewer()
        self.splitter.addWidget(self.log_viewer)
        
        # Add splitter to main layout
        self.main_layout.addWidget(self.splitter)

        # Initialize pages
        self.init_welcome_page()
        self.init_camera_detection_page()
        self.init_test_selection_page()
        self.init_live_view_page()

        self.stacked_widget.setCurrentWidget(self.welcome_page)
        
        # Set initial splitter sizes (70% main content, 30% log)
        self.splitter.setSizes([int(self.height() * 0.7), int(self.height() * 0.3)])
        
    def init_welcome_page(self):
        """Initialize welcome page with software description"""
        self.welcome_page = QWidget()
        layout = QVBoxLayout(self.welcome_page)
        layout.setContentsMargins(40, 40, 40, 40)  # Add some padding
        
        # Welcome title
        title = QLabel("Welcome to GenICam Camera Tester")
        title.setProperty('title', True)  # Used for styling
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Software description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.style_dict['white']};
                border: none;
                border-radius: 8px;
                padding: 16px;
                font-size: 14px;
            }}
        """)
        
        description_text = """
        <h2 style='color: #00427E;'>About GenICam Camera Tester</h2>
        <p>GenICam Camera Tester is a comprehensive testing suite designed for Basler cameras using the GenICam standard. 
        This software provides tools for:</p>
        <ul>
            <li>Camera detection and connection (USB and GigE)</li>
            <li>Live image viewing and capture</li>
            <li>Image quality assessment</li>
            <li>Performance testing</li>
            <li>Long-duration stability testing</li>
            <li>Feature access verification</li>
        </ul>
        <p>Click the button below to start by detecting your camera.</p>
        """
        description.setHtml(description_text)
        layout.addWidget(description)
        
        # Get Started button
        start_button = QPushButton("Get Started")
        start_button.setMinimumHeight(40)
        start_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.camera_detection_page))
        
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.addStretch()
        button_layout.addWidget(start_button)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        layout.addStretch()
        
        self.stacked_widget.addWidget(self.welcome_page)

    def init_camera_detection_page(self):
        self.camera_detection_page = QWidget()
        layout = QVBoxLayout(self.camera_detection_page)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Title and description
        title = QLabel("Camera Detection")
        title.setProperty('title', True)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        description = QLabel(
            "Select your camera interface type below. The software will automatically "
            "detect and connect to available cameras."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"""
            font-size: 14px;
            color: {self.style_dict['text']};
            margin: 20px 0;
        """)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        # Camera selection group
        selection_group = QGroupBox("Camera Interface Selection")
        selection_layout = QVBoxLayout()

        # USB Camera section
        usb_widget = QWidget()
        usb_layout = QHBoxLayout(usb_widget)
        
        usb_info = QWidget()
        usb_info_layout = QVBoxLayout(usb_info)
        usb_title = QLabel("USB3 Camera")
        usb_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        usb_desc = QLabel("Connect to USB3 Vision compliant cameras")
        usb_desc.setWordWrap(True)
        usb_info_layout.addWidget(usb_title)
        usb_info_layout.addWidget(usb_desc)
        
        self.usb_button = QPushButton("Detect USB Camera")
        self.usb_button.clicked.connect(self.presenter.detect_usb_camera)
        
        usb_layout.addWidget(usb_info)
        usb_layout.addWidget(self.usb_button)
        selection_layout.addWidget(usb_widget)

        # Add separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {self.style_dict['border']};")
        selection_layout.addWidget(line)

        # GigE Camera section
        gige_widget = QWidget()
        gige_layout = QHBoxLayout(gige_widget)
        
        gige_info = QWidget()
        gige_info_layout = QVBoxLayout(gige_info)
        gige_title = QLabel("GigE Camera")
        gige_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        gige_desc = QLabel("Connect to GigE Vision compliant cameras")
        gige_desc.setWordWrap(True)
        gige_info_layout.addWidget(gige_title)
        gige_info_layout.addWidget(gige_desc)
        
        self.gige_button = QPushButton("Detect GigE Camera")
        self.gige_button.clicked.connect(self.prompt_gige_configuration)
        
        gige_layout.addWidget(gige_info)
        gige_layout.addWidget(self.gige_button)
        selection_layout.addWidget(gige_widget)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        # Status section
        self.status_label = QLabel("Ready to detect cameras")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {self.style_dict['text']};
            font-size: 14px;
            margin-top: 20px;
        """)
        layout.addWidget(self.status_label)

        layout.addStretch()
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
        layout = QHBoxLayout(self.test_selection_page)
        
        # Left panel - Test buttons
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        title = QLabel("Camera Tests")
        title.setProperty('title', True)
        left_layout.addWidget(title)

        # Add buttons for different test categories
        test_buttons = [
            ("Live View", lambda: self.stacked_widget.setCurrentWidget(self.live_view_page)),
            ("Feature Tests", self.run_feature_tests),
            ("Image Quality Tests", self.run_image_quality_tests),
            ("Performance Tests", self.run_performance_tests),
            ("Long Run Test", self.run_long_run_test)
        ]

        for label, callback in test_buttons:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            left_layout.addWidget(btn)
            
        # Add disconnect button at the bottom
        disconnect_btn = QPushButton("Disconnect Camera")
        disconnect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['error']};
                color: {self.style_dict['white']};
            }}
            QPushButton:hover {{
                background-color: #c82333;
            }}
        """)
        disconnect_btn.clicked.connect(self.disconnect_camera)
        left_layout.addStretch()
        left_layout.addWidget(disconnect_btn)
        
        layout.addWidget(left_panel)
        
        # Right panel - Camera details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Camera info group
        info_group = QGroupBox("Camera Information")
        info_layout = QVBoxLayout()
        
        self.camera_details_widget = QTextEdit()
        self.camera_details_widget.setReadOnly(True)
        self.camera_details_widget.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: none;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(self.camera_details_widget)
        
        # Documentation link
        self.doc_link = QLabel()
        self.doc_link.setOpenExternalLinks(True)  # Enable clickable links
        info_layout.addWidget(self.doc_link)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        layout.addWidget(right_panel)
        
        # Set the stretch factor for panels (1:1 ratio)
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)
        
        self.stacked_widget.addWidget(self.test_selection_page)
        
    def update_camera_details(self, details):
        """Update the camera details panel with provided information"""
        if not details:
            return
            
        # Format camera details
        html_content = f"""
            <h3 style="color: {self.style_dict['primary']};">{details.get('name', 'N/A')}</h3>
            <p><b>Manufacturer:</b> {details.get('manufacturer', 'N/A')}</p>
            <p><b>Serial Number:</b> {details.get('serial_number', 'N/A')}</p>
            <p><b>Material Number:</b> {details.get('material_number', 'N/A')}</p>
            <p><b>Interface:</b> {details.get('interface', 'N/A')}</p>
            <p><b>Firmware Version:</b> {details.get('firmware_version', 'N/A')}</p>
            <p><b>Sensor Type:</b> {details.get('sensor_type', 'N/A')}</p>
            <p><b>Sensor Size:</b> {details.get('sensor_size', 'N/A')}</p>
            <p><b>Pixel Size:</b> {details.get('pixel_size', 'N/A')}</p>
        """
        self.camera_details_widget.setHtml(html_content)
        
        # Update documentation link
        if 'documentation_link' in details:
            link_text = (
                f'<a href="{details["documentation_link"]}" '
                f'style="color: {self.style_dict["secondary"]};">'
                f'View Camera Documentation →</a>'
            )
            self.doc_link.setText(link_text)
            
    def disconnect_camera(self):
        """Disconnect the current camera and return to welcome page"""
        try:
            self.presenter.disconnect_camera()
            self.stacked_widget.setCurrentWidget(self.welcome_page)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error disconnecting camera: {str(e)}")

    def closeEvent(self, event):
        """Handle application closure"""
        self.presenter.cleanup()
        event.accept()

    def init_log_viewer(self):
        """Initialize the log viewer component with Basler-themed styling"""
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        
        # Add header to log viewer
        log_header = QLabel("System Log")
        log_header.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {self.style_dict['primary']};
            padding: 4px;
        """)
        log_layout.addWidget(log_header)
        
        # Create log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.style_dict['white']};
                border: 1px solid {self.style_dict['border']};
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        log_layout.addWidget(self.log_text)
        
        self.log_viewer = log_container

    def run_feature_tests(self):
        """Run feature access tests"""
        self.presenter.run_feature_tests()

    def run_image_quality_tests(self):
        """Run image quality tests"""
        self.presenter.run_image_quality_tests()

    def run_performance_tests(self):
        """Run performance tests"""
        self.presenter.run_performance_tests()

    def run_long_run_test(self):
        """Show long run test dialog"""
        dialog = LongRunTestDialog(self)
        dialog.exec_()

    def update_live_view(self):
        """Update the live view with the current frame"""
        frame = self.presenter.get_current_frame()
        if frame is not None:
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
                self.log_message(f"Error updating live image: {str(e)}", "ERROR")

    def toggle_live_view(self):
        """Toggle live view on/off"""
        if self.live_button.text() == "Start Live View":
            if self.presenter.start_live_view():
                self.live_button.setText("Stop Live View")
                self.live_timer.start()
        else:
            self.presenter.stop_live_view()
            self.live_button.setText("Start Live View")
            self.live_timer.stop()
            self.image_label.clear()

    def snap_image(self):
        """Capture a single image"""
        self.presenter.snap_image()

    def log_message(self, message, level="INFO"):
        """Add a message to the log viewer"""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        color = {
            "INFO": "black",
            "WARNING": "#FFA500",
            "ERROR": "red",
            "SUCCESS": "green"        }.get(level.upper(), "black")
        html_message = f'<p style="margin: 0;"><span style="color: #666;">{timestamp}</span> <span style="color: {color};">[{level}]</span> {message}</p>'
        self.log_text.append(html_message)
        # Auto scroll to bottom
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def show_error(self, title, message):
        """Show an error dialog with the given title and message"""
        QMessageBox.critical(self, title, message)

    def update_test_results(self, title, results):
        """Update the test results in the UI"""
        # Create a dialog to show test results
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # Create a text area for results with monospace font
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setStyleSheet("QTextEdit { font-family: monospace; }")
        text_area.setText(results)
        
        # Make text selectable and copy-able
        text_area.setTextInteractionFlags(
            Qt.TextSelectableByMouse | 
            Qt.TextSelectableByKeyboard |
            Qt.LinksAccessibleByMouse
        )
        layout.addWidget(text_area)
        
        # Add OK button
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Save)
        buttons.accepted.connect(dialog.accept)
        buttons.button(QDialogButtonBox.Save).clicked.connect(
            lambda: self._save_test_results(results)
        )
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def _save_test_results(self, results):
        """Save test results to a file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Test Results",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write(results)
                self.log_message(f"Test results saved to {file_name}", "INFO")
            except Exception as e:
                self.show_error("Save Error", f"Could not save test results: {str(e)}")

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

class LongRunTestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Long Run Test")
        self.setMinimumWidth(800)  # Increased width for live view
        
        # Main layout as horizontal to put live view on the right
        layout = QHBoxLayout(self)
        
        # Left side with controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Duration input
        duration_group = QGroupBox("Test Duration")
        duration_layout = QFormLayout()
        
        self.hours_input = QSpinBox()
        self.hours_input.setRange(0, 999)
        self.minutes_input = QSpinBox()
        self.minutes_input.setRange(0, 59)
        
        duration_layout.addRow("Hours:", self.hours_input)
        duration_layout.addRow("Minutes:", self.minutes_input)
        duration_group.setLayout(duration_layout)
        left_layout.addWidget(duration_group)
        
        # Progress section
        progress_group = QGroupBox("Test Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to start")
        progress_layout.addWidget(self.status_label)
        
        self.stats_label = QLabel("")
        progress_layout.addWidget(self.stats_label)
        
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.start_button.clicked.connect(self.start_test)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Test")
        self.stop_button.clicked.connect(self.stop_test)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        left_layout.addLayout(button_layout)
        
        # Add left panel to main layout
        layout.addWidget(left_panel)
        
        # Right side with live view
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Live view group
        view_group = QGroupBox("Live View")
        view_layout = QVBoxLayout()
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color: #000000; }")
        view_layout.addWidget(self.image_label)
        
        view_group.setLayout(view_layout)
        right_layout.addWidget(view_group)
        
        # Add right panel to main layout
        layout.addWidget(right_panel)
        
        # Set layout ratios (40% controls, 60% live view)
        layout.setStretch(0, 4)
        layout.setStretch(1, 6)
        
        # Test state
        self.is_running = False
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.update_progress)
        self.start_time = None
        self.frame_count = 0
        self.current_fps = 0
        
        # Image update timer
        self.image_timer = QTimer()
        self.image_timer.timeout.connect(self.update_live_image)
        self.image_timer.start(33)  # ~30 FPS update rate

    def update_live_image(self):
        """Update the live image display"""
        if self.is_running:
            frame = self.parent.presenter.get_current_frame()
            if frame is not None:
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
                    self.parent.log_message(f"Error updating live image: {str(e)}", "ERROR")

    def closeEvent(self, event):
        """Handle dialog closure"""
        if self.is_running:
            self.stop_test()
        self.image_timer.stop()
        event.accept()
        
    def start_test(self):
        total_minutes = self.hours_input.value() * 60 + self.minutes_input.value()
        if total_minutes <= 0:
            QMessageBox.warning(self, "Invalid Duration", "Please set a test duration greater than 0 minutes.")
            return
            
        self.total_seconds = total_minutes * 60
        self.start_time = time.time()
        self.frame_count = 0
        self.progress_bar.setRange(0, self.total_seconds)
        
        self.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.hours_input.setEnabled(False)
        self.minutes_input.setEnabled(False)
        
        # Start the camera grabbing in the presenter
        self.parent.presenter.start_long_run_test()
        
        # Start progress update timer
        self.test_timer.start(1000)  # Update every second
        
    def stop_test(self):
        self.is_running = False
        self.test_timer.stop()
        self.parent.presenter.stop_long_run_test()
        self.reset_ui()
        
    def reset_ui(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.hours_input.setEnabled(True)
        self.minutes_input.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Test stopped")
        
    def update_progress(self):
        if not self.is_running:
            return
            
        elapsed = int(time.time() - self.start_time)
        self.progress_bar.setValue(elapsed)
        
        # Get current stats from presenter
        stats = self.parent.presenter.get_long_run_stats()
        self.frame_count = stats.get('frames_captured', 0)
        self.current_fps = stats.get('current_fps', 0)
        
        # Calculate remaining time
        remaining_seconds = self.total_seconds - elapsed
        remaining_str = time.strftime('%H:%M:%S', time.gmtime(remaining_seconds))
        
        # Format elapsed time
        elapsed_str = time.strftime('%H:%M:%S', time.gmtime(elapsed))
        
        # Calculate estimated total frames
        estimated_total_frames = int(self.current_fps * self.total_seconds)
        
        # Update status
        status_text = (
            f"Elapsed: {elapsed_str}\n"
            f"Remaining: {remaining_str}\n"
            f"Current FPS: {self.current_fps:.1f}\n"
            f"Frames Captured: {self.frame_count}\n"
            f"Estimated Total Frames: {estimated_total_frames:,}"
        )
        self.stats_label.setText(status_text)
        
        # Check if test is complete
        if elapsed >= self.total_seconds:
            self.is_running = False
            self.test_timer.stop()
            self.parent.presenter.stop_long_run_test()
            self.reset_ui()
            QMessageBox.information(self, "Test Complete", 
                                  f"Long run test completed!\n\n"
                                  f"Total frames captured: {self.frame_count:,}\n"
                                  f"Average FPS: {self.frame_count / self.total_seconds:.1f}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CameraTestGUI()
    gui.show()
    sys.exit(app.exec_())
