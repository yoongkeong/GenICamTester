# presenter.py
import sys
import os
from PyQt5.QtWidgets import QMessageBox
from pypylon import pylon
from tests.test_imageAcq import test_imageAcq 

class CameraPresenter:
    def __init__(self, view):
        self.view = view  # Reference to the CameraTestGUI instance
        self.camera = None

    def detect_gige_camera(self):
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            if self.camera.IsOpen():
                camera_info = (
                    f"Camera detected:\nSerial Number: {self.camera.GetDeviceInfo().GetSerialNumber()}"
                    f"\nManufacturer: {self.camera.GetDeviceInfo().GetVendorName()}"
                )
                self.view.display_camera_info(camera_info)
                self.view.navigate_to_test_selection()
        except Exception:
            self.prompt_ip_configuration()

    def detect_usb_camera(self):
        try:
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            if self.camera.IsOpen():
                camera_info = (
                    f"Camera detected:\nSerial Number: {self.camera.GetDeviceInfo().GetSerialNumber()}"
                    f"\nManufacturer: {self.camera.GetDeviceInfo().GetVendorName()}"
                )
                self.view.display_camera_info(camera_info)
                self.view.navigate_to_test_selection()
        except Exception:
            QMessageBox.warning(self.view, "USB Camera Detection", "No USB camera detected.")

    def start_image_acquisition(self):
        """Starts image acquisition and displays result in the GUI."""
        try:
            result = test_image_acquisition(self.camera)
            if result:
                self.view.display_image(result)
            else:
                QMessageBox.warning(self.view, "Image Acquisition", "Failed to acquire image.")
        except Exception as e:
            QMessageBox.critical(self.view, "Error", f"Image acquisition failed: {e}")

    def show_test_result(self, test_name, result):
        QMessageBox.information(self.view, f"{test_name} Result", str(result))

    def prompt_ip_configuration(self):
        QMessageBox.warning(self.view, "GigE Camera Detection", "No GigE camera detected. Please configure IP settings.")
