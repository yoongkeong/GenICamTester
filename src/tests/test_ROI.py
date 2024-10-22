import pytest
from genicam_helper import GenICamHelper
from camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_roi_selection(camera):
    genicam_helper = GenICamHelper(camera.camera)
    roi_width = genicam_helper.access_feature("Width")
    roi_height = genicam_helper.access_feature("Height")

    # Set ROI to the center of the sensor
    original_width = roi_width.GetMax()
    original_height = roi_height.GetMax()

    new_width = int(original_width / 2)
    new_height = int(original_height / 2)

    roi_width.SetValue(new_width)
    roi_height.SetValue(new_height)

    assert roi_width.GetValue() == new_width, "Failed to set ROI width."
    assert roi_height.GetValue() == new_height, "Failed to set ROI height."
