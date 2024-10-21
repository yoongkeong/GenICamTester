import os
from pathlib import Path

# Define the folder structure
folder_structure = {
    "GenICamCameraTester": [
        "config",
        "data/test_images",
        "data/calibration_files",
        "docs",
        "logs",
        "reports/coverage",
        "src/gui",
        "src/lib",
        "src/tests",
    ]
}

# Define the basic files and their content
files_content = {
    "GenICamCameraTester/config/config.ini": """
[general]
log_level = INFO
camera_timeout = 5000  # Timeout for camera responses (ms)

[gigE]
camera_ip = 192.168.1.100
packet_size = 1500

[usb]
usb_bandwidth = 1000

[image_processing]
edge_detection_threshold = 100
blur_detection_threshold = 0.75

[logging]
log_file = logs/test.log
error_log_file = logs/error.log
""",
    "GenICamCameraTester/docs/architecture.md": "# Architecture Overview\n\nDetails about the architecture.",
    "GenICamCameraTester/docs/test_plan.md": "# Test Plan\n\nDetailed test plans for the modules.",
    "GenICamCameraTester/docs/test_report_template.md": "# Test Report Template\n\nUse this template to create test reports.",
    "GenICamCameraTester/logs/test.log": "",
    "GenICamCameraTester/logs/error.log": "",
    "GenICamCameraTester/src/gui/main_gui.py": """
# Basic GUI for GenICam Tester (placeholder)

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('GenICam Tester GUI')

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
""",
    "GenICamCameraTester/src/lib/camera_helper.py": """
import pypylon.pylon as pylon
import logging
from configparser import ConfigParser

config = ConfigParser()
config.read('config/config.ini')
logger = logging.getLogger(__name__)

class CameraHelper:
    def __init__(self, camera_ip=None):
        self.camera_ip = camera_ip or config['gigE']['camera_ip']
        self.camera = self.initialize_camera()

    def initialize_camera(self):
        try:
            logger.info(f"Initializing camera at {self.camera_ip}")
            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            camera.Open()
            return camera
        except Exception as e:
            logger.error(f"Camera initialization failed: {str(e)}")
            raise e

    def start_acquisition(self):
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logger.info("Camera acquisition started")
        except Exception as e:
            logger.error(f"Failed to start acquisition: {str(e)}")
            raise e

    def stop_acquisition(self):
        self.camera.StopGrabbing()
        logger.info("Camera acquisition stopped")

    def power_on(self):
        logger.info("Powering on the camera")

    def power_off(self):
        logger.info("Powering off the camera")
""",
    "GenICamCameraTester/src/lib/genicam_helper.py": """
import pypylon.genicam as genicam
import logging

logger = logging.getLogger(__name__)

class GenICamHelper:
    def validate_xml(self, camera):
        try:
            xml = camera.GetDeviceInfo().GetXML()
            logger.info("Validating GenICam XML descriptor")
            # Validation logic here (e.g., XML schema check)
            return True
        except genicam.RuntimeException as e:
            logger.error(f"XML Validation failed: {str(e)}")
            return False

    def access_feature(self, camera, feature_name):
        try:
            node_map = camera.GetNodeMap()
            feature_node = node_map.GetNode(feature_name)
            if feature_node.IsReadable:
                logger.info(f"Feature {feature_name} is readable")
                return feature_node.GetValue()
            else:
                logger.warning(f"Feature {feature_name} is not accessible")
                return None
        except Exception as e:
            logger.error(f"Feature access failed: {str(e)}")
            raise e
""",
    "GenICamCameraTester/src/tests/test_power.py": """
import pytest
from src.lib.camera_helper import CameraHelper

@pytest.fixture(scope="module")
def camera():
    cam = CameraHelper()
    yield cam
    cam.camera.Close()

def test_power_on(camera):
    camera.power_on()
    assert camera.camera.IsOpen(), "Camera failed to power on"

def test_power_off(camera):
    camera.power_off()
    assert not camera.camera.IsOpen(), "Camera failed to power off"
""",
    "GenICamCameraTester/.gitignore": """
# Ignore unnecessary files
__pycache__/
*.pyc
.env
logs/*
reports/*
""",
    "GenICamCameraTester/pytest.ini": """
[pytest]
addopts = --cov=src --cov-report=html --maxfail=1 -v
testpaths = src/tests
""",
    "GenICamCameraTester/requirements.txt": """
pypylon
pytest
pytest-cov
opencv-python
loguru
""",
    "GenICamCameraTester/README.md": """
# GenICam Camera Tester

This project provides a comprehensive framework for testing GenICam-compliant industrial cameras. It supports testing different transport layers (USB, GigE) and covers multiple camera features such as image quality, feature access, and more.
"""
}

# Function to create directories
def create_directories():
    for root, dirs in folder_structure.items():
        for dir_path in dirs:
            path = Path(root) / dir_path
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {path}")

# Function to create files with default content
def create_files():
    for file_path, content in files_content.items():
        with open(file_path, 'w') as f:
            f.write(content.strip())
            print(f"Created file: {file_path}")

if __name__ == "__main__":
    create_directories()
    create_files()
