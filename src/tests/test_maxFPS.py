import pytest
from src.lib.genicam_helper import GenICamHelper
from src.lib.camera_helper import CameraHelper

def test_max_fps():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")

    camera_helper.camera.MaxFrameRate.SetValue(60)  # Set to max FPS
    assert camera_helper.camera.MaxFrameRate.GetValue() == 60, "Failed to set max FPS."
    
    camera_helper.disconnect_camera()
