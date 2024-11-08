# main_gui.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, 
    QStackedWidget, QDialog, QLineEdit, QDialogButtonBox, QFormLayout, QMessageBox
)
from presenter import CameraPresenter

class CameraTestGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.presenter = CameraPresenter(self)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("GenICam Camera Tester")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.stacked_widget = QStackedWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.addWidget(self.stacked_widget)

        self.init_camera_detection_page()
        self.init_test_selection_page()

        self.stacked_widget.setCurrentWidget(self.camera_detection_page)

    def init_camera_detection_page(self):
        self.camera_detection_page = QWidget()
        layout = QVBoxLayout(self.camera_detection_page)
        
        self.status_label = QLabel("Detecting Camera...")
        layout.addWidget(self.status_label)

        self.usb_button = QPushButton("Detect USB Camera")
        self.usb_button.clicked.connect(self.presenter.detect_usb_camera)
        layout.addWidget(self.usb_button)

        self.gige_button = QPushButton("Detect GigE Camera")
        self.gige_button.clicked.connect(self.prompt_gige_configuration)
        layout.addWidget(self.gige_button)

        self.stacked_widget.addWidget(self.camera_detection_page)

    def prompt_gige_configuration(self):
        config_dialog = CameraConfigDialog(self)
        if config_dialog.exec_() == QDialog.Accepted:
            use_dhcp, ip_settings = config_dialog.get_configuration()
            self.presenter.detect_gige_camera(use_dhcp, ip_settings)

    def init_test_selection_page(self):
        self.test_selection_page = QWidget()
        layout = QVBoxLayout(self.test_selection_page)

        layout.addWidget(QLabel("Basic Tests"))
        basic_tests_button = QPushButton("Run Basic Tests")
        basic_tests_button.clicked.connect(self.presenter.start_image_acquisition)
        layout.addWidget(basic_tests_button)

        layout.addWidget(QLabel("Functional Tests"))
        functional_tests_button = QPushButton("Run Functional Tests")
        functional_tests_button.clicked.connect(lambda: self.presenter.run_test(test_initialize_camera, "Init Camera"))
        layout.addWidget(functional_tests_button)

        layout.addWidget(QLabel("Advanced Tests"))
        advanced_tests_button = QPushButton("Run Advanced Tests")
        layout.addWidget(advanced_tests_button)

        self.stacked_widget.addWidget(self.test_selection_page)

    def display_camera_info(self, info):
        self.status_label.setText(info)

    def navigate_to_test_selection(self):
        self.stacked_widget.setCurrentWidget(self.test_selection_page)

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
