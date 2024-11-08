import pytest
import pytest
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_io_trigger(camera):
    genicam_helper = GenICamHelper(camera.camera)
    trigger_source = genicam_helper.access_feature("TriggerSource")
    trigger_mode = genicam_helper.access_feature("TriggerMode")

    trigger_source.SetValue("Line1")  # Set to hardware trigger source
    trigger_mode.SetValue("On")
    
    assert trigger_source.GetValue() == "Line1", "Trigger source not set correctly."
    assert trigger_mode.GetValue() == "On", "Trigger mode should be 'On'."

def test_io_output(camera):
    genicam_helper = GenICamHelper(camera.camera)
    output_line = genicam_helper.access_feature("LineSelector")
    output_mode = genicam_helper.access_feature("LineMode")

    output_line.SetValue("Line1")
    output_mode.SetValue("Output")
    
    assert output_line.GetValue() == "Line1", "Output line not selected correctly."
    assert output_mode.GetValue() == "Output", "Output mode not set correctly."
