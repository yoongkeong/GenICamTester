import pytest
from camera_helper import CameraHelper

@pytest.fixture(scope='module')
def usb_camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(com_port="COM3")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_usb_camera_power_on(usb_camera):
    assert usb_camera.camera.IsOpen(), "Camera should be powered on and connected."

def test_usb_camera_power_off(usb_camera):
    usb_camera.disconnect_camera()
    assert not usb_camera.camera.IsOpen(), "Camera should be powered off and disconnected."
