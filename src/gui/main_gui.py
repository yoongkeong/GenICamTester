# main_gui.py

import sys, time
import subprocess
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
from .presenter import CameraPresenter
import os

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

        # Separator
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

        # Simulation mode
        from PyQt5.QtWidgets import QCheckBox
        self.simulation_checkbox = QCheckBox("Simulation Mode")
        self.simulation_checkbox.setToolTip("Enable simulated camera (no hardware required)")
        self.simulation_checkbox.stateChanged.connect(self.on_simulation_toggled)
        selection_layout.addWidget(self.simulation_checkbox)

        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        # Status section
        self.status_container = QWidget()
        self.status_layout = QVBoxLayout(self.status_container)
        self.status_icon = QLabel("🔍")
        self.status_icon.setStyleSheet("font-size: 48px; margin: 20px 0;")
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_layout.addWidget(self.status_icon)
        self.status_label = QLabel("Ready to detect cameras")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {self.style_dict['text']};
            font-size: 16px;
            font-weight: bold;
            margin: 10px 0;
        """)
        self.status_layout.addWidget(self.status_label)
        self.status_description = QLabel("Click one of the detection buttons above to begin")
        self.status_description.setAlignment(Qt.AlignCenter)
        self.status_description.setStyleSheet(f"""
            color: {self.style_dict['text']};
            font-size: 14px;
            margin: 10px 0;
        """)
        self.status_layout.addWidget(self.status_description)

        # Reflect startup simulation state
        try:
            if hasattr(self.presenter, 'camera_helper') and getattr(self.presenter.camera_helper, 'simulation_enabled', False):
                self.simulation_checkbox.setChecked(True)
        except Exception:
            pass

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {self.style_dict['border']};
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                margin: 20px 0;
            }}
            QProgressBar::chunk {{
                background-color: {self.style_dict['primary']};
                border-radius: 8px;
            }}
        """)
        self.status_layout.addWidget(self.progress_bar)

        # Network configuration and system devices panel (PC info only)
        net_group = QGroupBox("Network Configuration")
        net_layout = QVBoxLayout()
        helper_label = QLabel(
            "View your PC's current devices. Use these to verify USB and GigE environments."
        )
        helper_label.setWordWrap(True)
        net_layout.addWidget(helper_label)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.btn_show_usb = QPushButton("Device Manager (USB)")
        self.btn_show_usb.setToolTip("List USB devices similar to Windows Device Manager")
        self.btn_show_usb.clicked.connect(self.show_device_manager_usb)
        btn_row.addWidget(self.btn_show_usb)

        self.btn_show_net = QPushButton("Network Adapters")
        self.btn_show_net.setToolTip("List network adapters and IPv4 addresses")
        self.btn_show_net.clicked.connect(self.show_network_adapters_info)
        btn_row.addWidget(self.btn_show_net)

        btn_row.addStretch()
        net_layout.addLayout(btn_row)

        # Output area
        self.pc_info_text = QTextEdit()
        self.pc_info_text.setReadOnly(True)
        self.pc_info_text.setMinimumHeight(140)
        self.pc_info_text.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; }")
        self.pc_info_text.setPlainText(
            "Click the buttons above to load USB or Network adapter information from this PC."
        )
        net_layout.addWidget(self.pc_info_text)

        net_group.setLayout(net_layout)
        layout.addWidget(net_group)
        # Success widget (status + summary)
        self.success_widget = QWidget()
        self.success_widget.setVisible(False)
        success_layout = QVBoxLayout(self.success_widget)
        success_icon = QLabel("✅")
        success_icon.setStyleSheet("font-size: 64px; margin: 20px 0;")
        success_icon.setAlignment(Qt.AlignCenter)
        success_layout.addWidget(success_icon)
        success_title = QLabel("Camera Detected Successfully!")
        success_title.setStyleSheet(f"""
            color: {self.style_dict['success']};
            font-size: 20px;
            font-weight: bold;
            margin: 10px 0;
        """)
        success_title.setAlignment(Qt.AlignCenter)
        success_layout.addWidget(success_title)
        self.camera_summary = QLabel()
        self.camera_summary.setStyleSheet(f"""
            color: {self.style_dict['text']};
            font-size: 14px;
            margin: 10px 0;
            padding: 16px;
            background-color: {self.style_dict['background']};
            border-radius: 8px;
        """)
        self.camera_summary.setAlignment(Qt.AlignCenter)
        self.camera_summary.setWordWrap(True)
        success_layout.addWidget(self.camera_summary)

        # Proceed button: always visible but disabled until a camera is connected
        self.proceed_button = QPushButton("Proceed to Tests")
        self.proceed_button.setEnabled(False)
        self.proceed_button.setToolTip("Connect a camera to proceed to tests")
        self.proceed_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['success']};
                color: {self.style_dict['white']};
                border: none;
                padding: 16px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                margin: 20px 0;
                min-width: 200px;
            }}
            QPushButton:disabled {{
                background-color: #9e9e9e;
                color: #f0f0f0;
            }}
            QPushButton:hover:!disabled {{
                background-color: #45a049;
            }}
        """)
        self.proceed_button.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.test_selection_page))

        # Order: status container -> success widget -> proceed button; button is outside success widget so it stays visible
        self.status_layout.addWidget(self.success_widget)
        self.status_layout.addWidget(self.proceed_button, alignment=Qt.AlignCenter)

        layout.addWidget(self.status_container)
        layout.addStretch()
        self.stacked_widget.addWidget(self.camera_detection_page)
        # Initialize system info panel with guidance text only (no default IPs)
        try:
            self.update_network_info()
        except Exception:
            pass

    def update_network_info(self):
        """Do not show default camera IPs; leave guidance text in the panel."""
        if hasattr(self, 'pc_info_text') and self.pc_info_text:
            # Keep existing text; nothing to auto-populate here.
            return

    def _run_powershell(self, command: str) -> str:
        """Run a PowerShell command and return stdout or error text."""
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=15
            )
            if completed.returncode == 0:
                return completed.stdout.strip() or "(no output)"
            else:
                err = completed.stderr.strip()
                return f"Error ({completed.returncode}): {err or completed.stdout.strip()}"
        except Exception as e:
            return f"Failed to run PowerShell: {e}"

    def show_device_manager_usb(self):
        """Display USB-related devices similar to Device Manager."""
        cmd = (
            "Get-PnpDevice -Class USB,USBHub | "
            "Select-Object Status,Class,Present,Problem,ProblemStatus, FriendlyName,InstanceId | "
            "Format-Table -AutoSize | Out-String"
        )
        output = self._run_powershell(cmd)
        if hasattr(self, 'pc_info_text'):
            self.pc_info_text.setPlainText(output)
        self.log_message("Loaded USB devices from system", "INFO")

    def show_network_adapters_info(self):
        """Display network adapter information and IPv4 addresses."""
        cmd_adapters = (
            "Get-NetAdapter | "
            "Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed | "
            "Format-Table -AutoSize | Out-String"
        )
        cmd_ips = (
            "Get-NetIPAddress -AddressFamily IPv4 | "
            "Select-Object InterfaceAlias,IPAddress,PrefixLength | "
            "Format-Table -AutoSize | Out-String"
        )
        adapters = self._run_powershell(cmd_adapters)
        ips = self._run_powershell(cmd_ips)
        combined = (
            "Network Adapters:\n" + adapters.strip() +
            "\n\nIPv4 Addresses:\n" + ips.strip()
        )
        if hasattr(self, 'pc_info_text'):
            self.pc_info_text.setPlainText(combined)
        self.log_message("Loaded Network adapter info from system", "INFO")
        
    def update_camera_detection_status(self, status, message, description="", show_progress=False, progress_value=0):
        """Update the camera detection status display"""
        if status == "detecting":
            self.status_icon.setText("🔍")
            self.status_label.setText("Detecting cameras...")
            self.status_description.setText("Please wait while we search for available cameras")
            self.progress_bar.setVisible(show_progress)
            if show_progress:
                self.progress_bar.setValue(progress_value)
            self.success_widget.setVisible(False)
            self.proceed_button.setEnabled(False)
            self.proceed_button.setToolTip("Connect a camera to proceed to tests")
            
        elif status == "success":
            self.status_icon.setText("✅")
            self.status_label.setText("Camera Detected!")
            self.status_description.setText(message)
            self.progress_bar.setVisible(False)
            self.success_widget.setVisible(True)
            self.proceed_button.setEnabled(True)
            self.proceed_button.setToolTip("")
            # Refresh network info in case mode changed or IP resolved from device
            try:
                self.update_network_info()
            except Exception:
                pass
            
        elif status == "error":
            self.status_icon.setText("❌")
            self.status_label.setText("Detection Failed")
            self.status_description.setText(message)
            self.progress_bar.setVisible(False)
            self.success_widget.setVisible(False)
            self.proceed_button.setEnabled(False)
            self.proceed_button.setToolTip("Connect a camera to proceed to tests")
            
        elif status == "warning":
            self.status_icon.setText("⚠️")
            self.status_label.setText("No Cameras Found")
            self.status_description.setText(message)
            self.progress_bar.setVisible(False)
            self.success_widget.setVisible(False)
            self.proceed_button.setEnabled(False)
            self.proceed_button.setToolTip("Connect a camera to proceed to tests")
            
        elif status == "ready":
            self.status_icon.setText("🔍")
            self.status_label.setText("Ready to detect cameras")
            self.status_description.setText("Click one of the detection buttons above to begin")
            self.progress_bar.setVisible(False)
            self.success_widget.setVisible(False)
            self.proceed_button.setEnabled(False)
            self.proceed_button.setToolTip("Connect a camera to proceed to tests")
            
    def update_camera_summary(self, camera_info):
        """Update the camera summary display in the success state"""
        if camera_info:
            summary_text = f"""
            <b>Model:</b> {camera_info.get('name', 'Unknown')}<br>
            <b>Serial Number:</b> {camera_info.get('id', 'Unknown')}<br>
            <b>Interface:</b> {camera_info.get('interface', 'Unknown')}<br>
            <b>Status:</b> Connected and Ready
            """
            self.camera_summary.setText(summary_text)

    def prompt_gige_configuration(self):
        # Prefill dialog with helper defaults if available
        defaults = {}
        try:
            if hasattr(self.presenter, 'camera_helper') and self.presenter.camera_helper:
                info = self.presenter.camera_helper.get_network_info()
                # Use stored defaults even if camera not connected
                defaults = {
                    'ip_address': getattr(self.presenter.camera_helper, 'ip_address', info.get('ip_address', '')),
                    'subnet_mask': getattr(self.presenter.camera_helper, 'subnet_mask', info.get('subnet_mask', '')),
                    'gateway': getattr(self.presenter.camera_helper, 'gateway', info.get('gateway', '')),
                }
        except Exception:
            pass

        config_dialog = CameraConfigDialog(self, defaults=defaults)
        if config_dialog.exec_() == QDialog.Accepted:
            use_dhcp, ip_settings = config_dialog.get_configuration()
            self.presenter.detect_gige_camera(use_dhcp, ip_settings)

    def on_simulation_toggled(self, state):
        """Enable or disable simulation mode at runtime."""
        enabled = bool(state)
        try:
            if not hasattr(self.presenter, 'camera_helper'):
                return
            self.presenter.camera_helper.simulation_enabled = enabled
            if enabled:
                if not getattr(self.presenter, 'camera', None):
                    # Connect and immediately transition to test selection flow
                    self.update_camera_detection_status("detecting", "Starting simulation camera...", show_progress=True, progress_value=50)
                    sim_cam = self.presenter.camera_helper.connect_camera(None)
                    if sim_cam:
                        fake_info = {"name": "Simulation Camera", "id": "SIM-0000", "interface": "SIM"}
                        self.presenter.camera = sim_cam
                        # Update details (no success screen shown)
                        self.update_camera_summary(fake_info)
                        # Hide success widget if it was left from a previous physical detection
                        if hasattr(self, 'success_widget'):
                            self.success_widget.setVisible(False)
                        # Refresh network info to show Simulation mode
                        try:
                            self.update_network_info()
                        except Exception:
                            pass
                        # Ensure test selection page exists
                        if not hasattr(self, 'test_selection_page'):
                            try:
                                self.init_test_selection_page()
                            except Exception as e:
                                self.log_message(f"Failed to init test selection page: {e}", "ERROR")
                        # Navigate directly to tests page
                        def _go_tests():
                            if hasattr(self, 'test_selection_page'):
                                self.stacked_widget.setCurrentWidget(self.test_selection_page)
                                self.log_message("Simulation camera ready. Running in simulation mode. Select any test to begin.", "SUCCESS")
                        QTimer.singleShot(100, _go_tests)
                    else:
                        self.update_camera_detection_status("error", "Failed to start simulation camera")
                        self.log_message("Simulation camera failed to initialize.", "ERROR")
            else:
                # Reset to ready state when simulation disabled
                if hasattr(self, 'success_widget'):
                    self.success_widget.setVisible(False)
                self.update_camera_detection_status("ready", "Simulation disabled. Select an interface to detect cameras.")
                self.log_message("Simulation mode disabled.", "INFO")
                try:
                    self.update_network_info()
                except Exception:
                    pass
        except Exception as e:
            self.log_message(f"Simulation toggle error: {e}", "ERROR")

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
        page_layout = QVBoxLayout(self.test_selection_page)
        page_layout.setContentsMargins(20, 20, 20, 20)

        # Top navigation bar
        top_nav = QHBoxLayout()
        back_main_btn = QPushButton("← Back to Main Menu")
        back_main_btn.setToolTip("Return to the welcome page")
        back_main_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.welcome_page))
        top_nav.addWidget(back_main_btn, alignment=Qt.AlignLeft)
        top_nav.addStretch()
        page_layout.addLayout(top_nav)

        # Header layout containing left info panel and right test groups
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Left: Camera info / quick actions
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        info_group = QGroupBox("📷 Camera Information")
        info_layout = QVBoxLayout()
        self.camera_details_widget = QTextEdit()
        self.camera_details_widget.setReadOnly(True)
        self.camera_details_widget.setMaximumHeight(180)
        info_layout.addWidget(self.camera_details_widget)
        self.doc_link = QLabel()
        self.doc_link.setOpenExternalLinks(True)
        info_layout.addWidget(self.doc_link)
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)

        quick_group = QGroupBox("⚡ Quick Actions")
        quick_layout = QHBoxLayout()
        live_btn = QPushButton("🎥 Live View")
        live_btn.clicked.connect(lambda: self.stacked_widget.setCurrentWidget(self.live_view_page))
        snap_btn = QPushButton("📸 Snap Image")
        snap_btn.clicked.connect(self.snap_image)
        quick_layout.addWidget(live_btn)
        quick_layout.addWidget(snap_btn)
        quick_group.setLayout(quick_layout)
        left_layout.addWidget(quick_group)

        disc_btn = QPushButton("🔌 Disconnect Camera")
        disc_btn.clicked.connect(self.disconnect_camera)
        left_layout.addWidget(disc_btn)
        left_layout.addStretch()
        header_layout.addWidget(left_panel, 3)

        # Right: Test groups
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        title = QLabel("🧪 Camera Tests")
        title.setProperty('title', True)
        title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(title)

        # Scroll container (simple vertical container here)
        tests_container = QVBoxLayout()

        groups = [
            ("🔧 Basic Camera Tests", "Fundamental camera operations and initialization", [
                ("Feature Access Test", self.run_feature_tests, "Test camera feature access"),
                ("Image Acquisition Test", self.run_image_acquisition_test, "Test image capture"),
                ("Camera Initialization Test", self.run_init_cam_test, "Test camera initialization"),
                ("Image Quality Test", self.run_image_quality_tests, "Test image quality metrics")
            ], self.style_dict['primary']),
            ("⚡ Performance Tests", "Camera performance and speed testing", [
                ("Max FPS Test", self.run_max_fps_test, "Test maximum frame rate"),
                ("ROI Test", self.run_roi_test, "Test region of interest functionality"),
                ("Long Run Test", self.run_long_run_test, "Extended stability testing")
            ], self.style_dict['success']),
            ("🖼️ Image Processing Tests", "Advanced image analysis and processing", [
                ("Camera Calibration", self.run_camera_calibration, "Camera calibration testing"),
                ("Edge Detection", self.run_edge_detection, "Edge detection algorithms"),
                ("Blur Detection", self.run_blur_detection, "Image blur detection")
            ], self.style_dict['secondary']),
            ("🚀 Advanced Tests", "Complex scenarios and power / IO", [
                ("Multi-Camera Test", self.run_multicam_test, "Test multiple cameras"),
                ("Power GigE Test", self.run_power_gige_test, "GigE power management"),
                ("Power USB Test", self.run_power_usb_test, "USB power management"),
                ("IO Test", self.run_io_test, "Input/Output testing"),
                ("Power Cycle Test", self.run_power_cycle_test, "Power cycle testing")
            ], self.style_dict['warning'])
        ]

        for g_title, g_desc, g_tests, g_color in groups:
            group_widget = self._create_test_group(g_title, g_desc, g_tests, g_color)
            tests_container.addWidget(group_widget)
        tests_container.addStretch()

        # Wrap container
        wrap = QWidget()
        wrap.setLayout(tests_container)
        right_layout.addWidget(wrap)
        header_layout.addWidget(right_panel, 7)

        page_layout.addWidget(header_widget)
        self.stacked_widget.addWidget(self.test_selection_page)
        
    def _create_test_group(self, title, description, tests, color):
        """Create a test group with the given title, description, and tests"""
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)
        group_layout.setContentsMargins(0, 0, 0, 0)
        
        # Group header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icon and title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {color};
            margin: 0;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        group_layout.addWidget(header_widget)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            color: {self.style_dict['text']};
            font-size: 12px;
            font-style: italic;
            margin: 0 0 12px 0;
        """)
        group_layout.addWidget(desc_label)
        
        # Test buttons in a grid layout
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        for test_name, callback, tooltip in tests:
            btn = QPushButton(test_name)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.style_dict['white']};
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 6px;
                    padding: 10px 16px;
                    font-size: 12px;
                    font-weight: bold;
                    min-width: 140px;
                    max-width: 160px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    color: {self.style_dict['white']};
                }}
                QPushButton:pressed {{
                    background-color: {color};
                    color: {self.style_dict['white']};
                }}
            """)
            btn.clicked.connect(callback)
            buttons_layout.addWidget(btn)
        
        buttons_layout.addStretch()
        group_layout.addWidget(buttons_widget)
        
        # Add some spacing
        group_layout.addSpacing(16)
        
        # Style the group container
        group_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.style_dict['white']};
                border: 1px solid {self.style_dict['border']};
                border-radius: 8px;
                padding: 16px;
                margin: 8px 0;
            }}
        """)
        
        return group_widget
        
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

    def run_image_acquisition_test(self):
        """Run image acquisition test"""
        self.presenter.run_image_acquisition_test()

    def run_max_fps_test(self):
        """Run max FPS test"""
        self.presenter.run_max_fps_test()

    def run_roi_test(self):
        """Run ROI test"""
        self.presenter.run_roi_test()

    def run_image_quality_tests(self):
        """Run image quality tests"""
        self.presenter.run_image_quality_tests()

    def run_camera_calibration(self):
        """Run camera calibration"""
        self.presenter.run_camera_calibration()

    def run_edge_detection(self):
        """Run edge detection"""
        self.presenter.run_edge_detection()

    def run_blur_detection(self):
        """Run blur detection"""
        self.presenter.run_blur_detection()

    def run_multicam_test(self):
        """Run multi-camera test"""
        self.presenter.run_multicam_test()

    def run_power_gige_test(self):
        """Run power GigE test"""
        self.presenter.run_power_gige_test()

    def run_power_usb_test(self):
        """Run power USB test"""
        self.presenter.run_power_usb_test()

    def run_io_test(self):
        """Run IO test"""
        self.presenter.run_io_test()

    def run_performance_tests(self):
        """Run performance tests"""
        self.presenter.run_performance_tests()

    def run_long_run_test(self):
        """Show long run test dialog"""
        dialog = LongRunTestDialog(self)
        dialog.exec_()

    def run_power_cycle_test(self):
        """Run power cycle test"""
        self.presenter.run_power_cycle_test()

    def run_init_cam_test(self):
        """Run camera initialization test"""
        self.presenter.run_init_cam_test()

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

    def show_captured_image(self, frame):
        """Show captured frame in the live view area and prompt user to save."""
        try:
            # Convert BGR to RGB for display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)
            self.image_label.setPixmap(scaled_pixmap)

            # Prompt user to save file (do not auto-save)
            file_name, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Save Captured Image",
                "",
                "PNG Image (*.png);;JPEG Image (*.jpg);;RAW Image (*.raw);;All Files (*)"
            )

            if file_name:
                # Determine format from selected filter or extension
                fmt = None
                if selected_filter and "PNG" in selected_filter:
                    fmt = 'png'
                elif selected_filter and ("JPEG" in selected_filter or "JPG" in selected_filter):
                    fmt = 'jpg'
                elif selected_filter and "RAW" in selected_filter:
                    fmt = 'raw'
                else:
                    # Use extension
                    _, ext = os.path.splitext(file_name)
                    fmt = ext.lstrip('.').lower() or 'png'

                try:
                    if fmt == 'raw':
                        # Save raw bytes (BGR numpy array) to file
                        frame.tofile(file_name)
                    else:
                        # Use OpenCV imwrite for common formats
                        cv2.imwrite(file_name, frame)
                    self.log_message(f"Captured image saved to {file_name}", "SUCCESS")
                except Exception as e:
                    self.show_error("Save Error", f"Failed to save image: {e}")
        except Exception as e:
            self.log_message(f"Failed to display captured image: {e}", "ERROR")

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
        """Show test results in a dialog with save/back options"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(700, 500)

        main_layout = QVBoxLayout(dialog)

        # Results text area
        text_area = QTextEdit()
        text_area.setReadOnly(True)
        text_area.setStyleSheet("QTextEdit { font-family: monospace; }")
        text_area.setText(results)
        text_area.setTextInteractionFlags(
            Qt.TextSelectableByMouse |
            Qt.TextSelectableByKeyboard |
            Qt.LinksAccessibleByMouse
        )
        main_layout.addWidget(text_area)

        # Buttons row
        buttons = QHBoxLayout()

        back_btn = QPushButton("← Back to Tests")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['warning']};
                color: {self.style_dict['white']};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #e0a800; }}
        """)
        def _back():
            dialog.reject()
            if hasattr(self, 'test_selection_page'):
                self.stacked_widget.setCurrentWidget(self.test_selection_page)
        back_btn.clicked.connect(_back)
        buttons.addWidget(back_btn)

        save_std_btn = QPushButton("💾 Save (Standard Name)")
        save_std_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['success']};
                color: {self.style_dict['white']};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #45a049; }}
        """)
        save_std_btn.clicked.connect(lambda: self._save_with_standard_name(title, results, dialog))
        buttons.addWidget(save_std_btn)

        save_as_btn = QPushButton("📁 Save As...")
        save_as_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['secondary']};
                color: {self.style_dict['white']};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #0056b3; }}
        """)
        save_as_btn.clicked.connect(lambda: self._save_test_results(results))
        buttons.addWidget(save_as_btn)

        buttons.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.style_dict['primary']};
                color: {self.style_dict['white']};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.style_dict['secondary']}; }}
        """)
        ok_btn.clicked.connect(dialog.accept)
        buttons.addWidget(ok_btn)

        main_layout.addLayout(buttons)
        dialog.setLayout(main_layout)
        dialog.exec_()
        
    def _save_with_standard_name(self, test_name, results, dialog):
        """Save test results using the standardized filename format"""
        try:
            # Get camera information for filename
            device_serial = "Unknown"
            model_name = "Unknown"
            
            if hasattr(self, 'presenter') and self.presenter.camera_helper:
                try:
                    # Try to get camera info from the helper
                    if hasattr(self.presenter.camera_helper, 'camera') and self.presenter.camera_helper.camera:
                        # Get serial number
                        if hasattr(self.presenter.camera_helper.camera, 'DeviceSerialNumber'):
                            device_serial = self.presenter.camera_helper.camera.DeviceSerialNumber.GetValue()
                        # Get model name
                        if hasattr(self.presenter.camera_helper.camera, 'DeviceModelName'):
                            model_name = self.presenter.camera_helper.camera.DeviceModelName.GetValue()
                except Exception as e:
                    self.log_message(f"Could not get camera info for filename: {str(e)}", "WARNING")
            
            # Save with standard name
            saved_path = self.save_test_results_with_standard_name(
                test_name, results, device_serial, model_name
            )
            
            if saved_path:
                # Close the dialog after successful save
                dialog.accept()
                
        except Exception as e:
            error_msg = f"Error saving with standard name: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.show_error("Save Error", error_msg)

    def _save_test_results(self, results):
        """Save test results to a file with custom name"""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Test Results",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(results)
                self.log_message(f"Test results saved to {file_name}", "INFO")
            except Exception as e:
                self.show_error("Save Error", f"Could not save test results: {str(e)}")

    def generate_test_filename(self, test_name, device_serial=None, model_name=None):
        """Generate a standardized filename for test results
        
        Format: "TestName"_"DeviceSerialNUMBER"_"ModelName"_"Timestamp"
        Example: CollectDeviceInfoTest_123456_BaslerAce_20250812_153045.txt
        
        Args:
            test_name (str): Name of the test
            device_serial (str): Device serial number
            model_name (str): Device model name
            
        Returns:
            str: Generated filename
        """
        # Get current timestamp in YYYYMMDD_HHMMSS format
        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        
        # Clean up test name (remove spaces, special chars)
        clean_test_name = test_name.replace(" ", "").replace("-", "").replace("_", "")
        
        # Use provided values or defaults
        serial = device_serial or "Unknown"
        model = model_name or "Unknown"
        
        # Clean up model name (remove spaces, special chars)
        clean_model = model.replace(" ", "").replace("-", "").replace("_", "")
        
        # Generate filename
        filename = f"{clean_test_name}_{serial}_{clean_model}_{timestamp}.txt"
        
        return filename
        
    def save_test_results_with_standard_name(self, test_name, results, device_serial=None, model_name=None):
        """Save test results using the standardized filename format"""
        try:
            # Generate standard filename
            filename = self.generate_test_filename(test_name, device_serial, model_name)
            
            # Get save directory from user
            save_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Directory to Save Test Results",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if save_dir:
                file_path = os.path.join(save_dir, filename)
                
                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(results)
                
                self.log_message(f"Test results saved to {file_path}", "SUCCESS")
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Save Successful",
                    f"Test results saved successfully!\n\n"
                    f"File: {filename}\n"
                    f"Location: {save_dir}"
                )
                
                return file_path
            else:
                self.log_message("Save cancelled by user", "INFO")
                return None
                
        except Exception as e:
            error_msg = f"Error saving test results: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.show_error("Save Error", error_msg)
            return None

class CameraConfigDialog(QDialog):
    def __init__(self, parent=None, defaults: dict = None):
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

        # Default to manual unless DHCP is explicitly chosen
        self.use_dhcp = False

        # Prefill fields if defaults are provided
        if defaults:
            self.ip_address.setText(defaults.get('ip_address', ''))
            self.subnet_mask.setText(defaults.get('subnet_mask', ''))
            self.gateway.setText(defaults.get('gateway', ''))

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

class TestProgressDialog(QDialog):
    """Progress dialog for showing test execution progress"""
    def __init__(self, parent=None, test_name="Test", max_steps=100):
        super().__init__(parent)
        self.setWindowTitle(f"Running {test_name}")
        self.setFixedSize(500, 200)
        self.setModal(True)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Test name
        title_label = QLabel(f"🧪 {test_name}")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #00427E;
            margin: 10px 0;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, max_steps)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #E9ECEF;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
                margin: 20px 0;
            }
            QProgressBar::chunk {
                background-color: #005CAB;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Initializing test...")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #333333;
            margin: 10px 0;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        # State
        self.current_step = 0
        self.max_steps = max_steps
        self.is_cancelled = False
        
    def update_progress(self, step, status_text):
        """Update progress bar and status text"""
        self.current_step = step
        self.progress_bar.setValue(step)
        self.status_label.setText(status_text)
        
        # Process events to update UI
        QApplication.processEvents()
        
    def update_status(self, status_text):
        """Update only the status text"""
        self.status_label.setText(status_text)
        QApplication.processEvents()
        
    def set_progress_range(self, min_val, max_val):
        """Set the progress bar range"""
        self.progress_bar.setRange(min_val, max_val)
        
    def complete(self):
        """Mark test as complete"""
        self.progress_bar.setValue(self.max_steps)
        self.status_label.setText("Test completed successfully!")
        self.cancel_button.setText("Close")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
    def was_cancelled(self):
        """Check if test was cancelled"""
        return self.is_cancelled

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = CameraTestGUI()
    gui.show()
    sys.exit(app.exec_())
