import pytest
from genicam_helper import GenICamHelper
from camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_access_exposure(camera):
    genicam_helper = GenICamHelper(camera.camera)
    exposure_node = genicam_helper.access_feature('ExposureTime')
    assert exposure_node is not None, "Failed to access exposure feature."
