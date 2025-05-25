import pytest
import time
import subprocess
import logging
from pypylon import pylon
from src.lib.genicam_helper import GenICamHelper
from src.lib.camera_helper import CameraHelper

class CameraHelper:
    def __init__(self):
        self.camera = None

    def connect_camera(self, camera_index=0):
        """Connect to the first available camera."""
        try:
            factory = pylon.TlFactory.GetInstance()
            devices = factory.EnumerateDevices()

            if not devices:
                raise RuntimeError("No camera found.")

            self.camera = pylon.InstantCamera(factory.CreateDevice(devices[camera_index]))
            self.camera.Open()
            logging.info("Camera connected and opened.")
        except Exception as e:
            logging.error(f"Error connecting to camera: {e}")
            raise

    def disconnect_camera(self):
        """Disconnect from the camera."""
        if self.camera and self.camera.IsOpen():
            self.camera.Close()
            logging.info("Camera disconnected.")
        else:
            logging.warning("Camera is not connected.")

    def is_camera_connected(self):
        """Check if the camera is currently connected."""
        return self.camera is not None and self.camera.IsOpen()

@pytest.fixture(scope='module')
def camera_helper():
    """Fixture to manage camera connection for the tests."""
    helper = CameraHelper()
    yield helper
    helper.disconnect_camera()

def test_power_on(camera_helper):
    """Test powering on the GigE camera."""
    camera_helper.connect_camera()
    assert camera_helper.is_camera_connected(), "Camera should be powered on and connected."

def test_power_off(camera_helper):
    """Test powering off the GigE camera."""
    camera_helper.disconnect_camera()
    assert not camera_helper.is_camera_connected(), "Camera should be powered off and disconnected."

if __name__ == '__main__':
    pytest.main()
