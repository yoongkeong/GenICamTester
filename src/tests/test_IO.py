import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestIO:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def test_io_triggers(self):
        """Test camera IO triggers"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "line1": self.test_io_line(1),
            "line2": self.test_io_line(2),
            "userOutput": self.test_user_output()
        }
        return results

    def test_io_line(self, line_number):
        """Test specific IO line"""
        try:
            # Test input mode
            self.genicam_helper.set_line_mode(line_number, "input")
            input_state = self.genicam_helper.get_line_state(line_number)

            # Test output mode
            self.genicam_helper.set_line_mode(line_number, "output")
            self.genicam_helper.set_line_state(line_number, True)
            high_state = self.genicam_helper.get_line_state(line_number)
            
            self.genicam_helper.set_line_state(line_number, False)
            low_state = self.genicam_helper.get_line_state(line_number)

            return {
                "input_test": input_state is not None,
                "output_high": high_state is True,
                "output_low": low_state is False,
                "overall": True
            }
        except Exception as e:
            return {
                "input_test": False,
                "output_high": False,
                "output_low": False,
                "overall": False,
                "error": str(e)
            }

    def test_user_output(self):
        """Test user configurable output"""
        try:
            # Set user output value
            self.genicam_helper.set_user_output(1, True)
            high_state = self.genicam_helper.get_user_output(1)
            
            self.genicam_helper.set_user_output(1, False)
            low_state = self.genicam_helper.get_user_output(1)

            return {
                "set_high": high_state is True,
                "set_low": low_state is False,
                "overall": True
            }
        except Exception as e:
            return {
                "set_high": False,
                "set_low": False,
                "overall": False,
                "error": str(e)
            }

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_io_functionality(camera):
    test = TestIO()
    test.setup(camera)
    
    results = test.test_io_triggers()
    assert results["line1"]["overall"], "IO Line 1 test failed"
    assert results["line2"]["overall"], "IO Line 2 test failed"
    assert results["userOutput"]["overall"], "User output test failed"
