import pytest
from camera_helper import CameraHelper

def test_power_cycle():
    camera_helper = CameraHelper()

    # Perform power cycle multiple times
    for _ in range(10):
        camera_helper.connect_camera(ip_address="192.168.1.10")
        assert camera_helper.camera.IsOpen(), "Camera should power on."
        camera_helper.disconnect_camera()
        assert not camera_helper.camera.IsOpen(), "Camera should power off."
