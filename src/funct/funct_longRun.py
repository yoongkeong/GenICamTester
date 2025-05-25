import pytest
from src.lib.camera_helper import CameraHelper

def test_long_run_acquisition():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")

    for _ in range(1000):  # Long-run test for 1000 acquisitions
        grab_result = camera_helper.camera.GrabOne(1000)
        assert grab_result.GrabSucceeded(), "Image acquisition failed during long run."

    camera_helper.disconnect_camera()
