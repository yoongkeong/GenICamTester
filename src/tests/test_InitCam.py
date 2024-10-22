import pytest
from camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_initialize_camera(camera):
    assert camera.camera.IsOpen(), "Camera failed to initialize."
