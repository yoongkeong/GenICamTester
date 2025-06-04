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
from .presenter import CameraPresenter

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
        # Colors and styling will go here
        pass

    def setup_ui_components(self):
        """Initialize UI components"""
        pass

    def log_message(self, message, level="INFO"):
        """Add a message to the log viewer"""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        color = {
            "INFO": "black",
            "WARNING": "#FFA500",
            "ERROR": "red",
            "SUCCESS": "green"
        }.get(level.upper(), "black")
        
        html_message = f'<p style="margin: 0;"><span style="color: #666;">{timestamp}</span> <span style="color: {color};">[{level}]</span> {message}</p>'
        self.log_text.append(html_message)
        # Auto scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
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
