# presenter.py
from pypylon import pylon
from PyQt5.QtWidgets import QMessageBox, QInputDialog

class CameraPresenter:
    def __init__(self, view):
        self.view = view  # This is the CameraTestGUI instance

    def detect_usb_camera(self):
        # Initialize Pypylon USB transport layer
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()

        usb_camera = None
        for device in devices:
            if device.GetDeviceClass() == "BaslerUsb":
                usb_camera = device
                break

        if usb_camera:
            # Camera detected
            self.show_camera_info(usb_camera, "USB")
        else:
            # No USB camera detected
            self.view.display_camera_info("No USB camera detected.")

    def detect_gige_camera(self):
        # Initialize Pypylon GigE transport layer explicitly
        tl_factory = pylon.TlFactory.GetInstance()
        gige_tl = tl_factory.CreateTl("BaslerGigE")  # Force transport layer to GigE

        if not gige_tl:
            self.view.display_camera_info("GigE transport layer not available.")
            return

        devices = gige_tl.EnumerateDevices()
        
        if not devices:
            # No GigE camera detected
            print("Debug: No devices found in the GigE transport layer.")
            self.prompt_ip_configuration()
            return

        # Log all found devices for debugging
        for device in devices:
            print(f"Debug: Found device - {device.GetDeviceClass()}, IP: {device.GetIpAddress()}, Serial: {device.GetSerialNumber()}")
        
        # Try to find a Basler GigE camera specifically
        gige_camera = None
        for device in devices:
            if device.GetDeviceClass() == "BaslerGigE":
                gige_camera = device
                break

        if gige_camera:
            # Camera detected
            self.show_camera_info(gige_camera, "GigE")
        else:
            # No GigE camera detected in the subnet
            print("Debug: No BaslerGigE device found after filtering.")
            self.prompt_ip_configuration()

    def show_camera_info(self, device, camera_type):
        # Open camera to retrieve info
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateDevice(device))
        camera.Open()

        # Retrieve Serial Number and Manufacturer Information
        serial_number = camera.GetDeviceInfo().GetSerialNumber()
        manufacturer = camera.GetDeviceInfo().GetVendorName()
        model_name = camera.GetDeviceInfo().GetModelName()

        # Display information in the GUI
        self.view.display_camera_info(
            f"{camera_type} Camera Detected!\n"
            f"Serial Number: {serial_number}\n"
            f"Manufacturer: {manufacturer}\n"
            f"Model Name: {model_name}"
        )
        
        camera.Close()

    def prompt_ip_configuration(self):
        # Ask user whether to configure Static IP or DHCP
        reply = QMessageBox.question(
            self.view, "No GigE Camera Detected",
            "No GigE camera detected in the subnet.\n"
            "Do you want to configure a Static IP?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.configure_static_ip()
        else:
            self.configure_dhcp()

    def configure_static_ip(self):
        # Prompt the user to enter IP, Subnet Mask, and Gateway
        ip_address, ok1 = QInputDialog.getText(self.view, "Static IP Configuration", "Enter IP Address:")
        if not ok1:
            return

        subnet_mask, ok2 = QInputDialog.getText(self.view, "Static IP Configuration", "Enter Subnet Mask:")
        if not ok2:
            return

        gateway, ok3 = QInputDialog.getText(self.view, "Static IP Configuration", "Enter Gateway:")
        if not ok3:
            return

        # Apply static IP settings
        self.view.display_camera_info(
            f"Configuring Static IP:\nIP: {ip_address}\nSubnet Mask: {subnet_mask}\nGateway: {gateway}"
        )

    def configure_dhcp(self):
        # Display DHCP configuration message
        self.view.display_camera_info("Configuring camera to use DHCP...")
        # DHCP setting logic could be added here if needed
