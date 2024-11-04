import pytest
from camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_image_acquisition(camera):
    grab_result = camera.camera.GrabOne(1000)
    assert grab_result.GrabSucceeded(), "Image acquisition failed."
