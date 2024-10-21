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