import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestFeatureAccess:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def test_basic_features(self):
        """Test basic camera feature access"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "exposure": self.test_exposure(),
            "gain": self.test_gain(),
            "pixel_format": self.test_pixel_format(),
            "roi": self.test_roi()
        }
        return results

    def test_exposure(self):
        """Test exposure time feature"""
        try:
            current = self.genicam_helper.get_exposure_time()
            self.genicam_helper.set_exposure_time(current * 2)
            new_value = self.genicam_helper.get_exposure_time()
            return abs(new_value - (current * 2)) < 0.1
        except Exception as e:
            return False

    def test_gain(self):
        """Test gain feature"""
        try:
            current = self.genicam_helper.get_gain()
            self.genicam_helper.set_gain(current + 1)
            new_value = self.genicam_helper.get_gain()
            return abs(new_value - (current + 1)) < 0.1
        except Exception as e:
            return False

    def test_pixel_format(self):
        """Test pixel format feature"""
        try:
            formats = self.genicam_helper.get_available_pixel_formats()
            if len(formats) > 0:
                current = self.genicam_helper.get_pixel_format()
                new_format = formats[0] if formats[0] != current else formats[-1]
                self.genicam_helper.set_pixel_format(new_format)
                return self.genicam_helper.get_pixel_format() == new_format
            return False
        except Exception as e:
            return False

    def test_roi(self):
        """Test ROI feature"""
        try:
            width, height = self.genicam_helper.get_roi()
            new_width = width // 2
            new_height = height // 2
            self.genicam_helper.set_roi(new_width, new_height)
            current_width, current_height = self.genicam_helper.get_roi()
            return current_width == new_width and current_height == new_height
        except Exception as e:
            return False

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_feature_access(camera):
    test = TestFeatureAccess()
    test.setup(camera)
    
    results = test.test_basic_features()
    for feature, success in results.items():
        assert success, f"Feature test failed: {feature}"
