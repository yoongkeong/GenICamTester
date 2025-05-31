import cv2
import numpy as np
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestROI:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def test_roi_settings(self):
        """Test Region of Interest (ROI) settings"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "full_resolution": self.test_full_resolution(),
            "half_resolution": self.test_half_resolution(),
            "quarter_resolution": self.test_quarter_resolution(),
            "custom_roi": self.test_custom_roi()
        }
        return results

    def test_full_resolution(self):
        """Test full resolution capture"""
        try:
            # Get maximum resolution
            max_width, max_height = self.genicam_helper.get_max_resolution()
            self.genicam_helper.set_roi(max_width, max_height)
            
            # Capture image
            image = self.capture_image()
            
            return {
                "success": True,
                "width": image.shape[1],
                "height": image.shape[0],
                "matches_expected": (
                    image.shape[1] == max_width and 
                    image.shape[0] == max_height
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_half_resolution(self):
        """Test half resolution ROI"""
        try:
            max_width, max_height = self.genicam_helper.get_max_resolution()
            half_width = max_width // 2
            half_height = max_height // 2
            
            self.genicam_helper.set_roi(half_width, half_height)
            image = self.capture_image()
            
            return {
                "success": True,
                "width": image.shape[1],
                "height": image.shape[0],
                "matches_expected": (
                    image.shape[1] == half_width and 
                    image.shape[0] == half_height
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_quarter_resolution(self):
        """Test quarter resolution ROI"""
        try:
            max_width, max_height = self.genicam_helper.get_max_resolution()
            quarter_width = max_width // 4
            quarter_height = max_height // 4
            
            self.genicam_helper.set_roi(quarter_width, quarter_height)
            image = self.capture_image()
            
            return {
                "success": True,
                "width": image.shape[1],
                "height": image.shape[0],
                "matches_expected": (
                    image.shape[1] == quarter_width and 
                    image.shape[0] == quarter_height
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def test_custom_roi(self):
        """Test custom ROI with offset"""
        try:
            max_width, max_height = self.genicam_helper.get_max_resolution()
            roi_width = max_width // 3
            roi_height = max_height // 3
            offset_x = roi_width
            offset_y = roi_height
            
            self.genicam_helper.set_roi(roi_width, roi_height, offset_x, offset_y)
            image = self.capture_image()
            
            return {
                "success": True,
                "width": image.shape[1],
                "height": image.shape[0],
                "offset_x": offset_x,
                "offset_y": offset_y,
                "matches_expected": (
                    image.shape[1] == roi_width and 
                    image.shape[0] == roi_height
                )
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def capture_image(self):
        """Capture a single image from the camera"""
        grab_result = self.camera_helper.camera.GrabOne(1000)
        if grab_result.GrabSucceeded():
            return grab_result.Array
        raise RuntimeError("Failed to capture image")

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_roi_functions(camera):
    test = TestROI()
    test.setup(camera)
    
    results = test.test_roi_settings()
    
    # Test full resolution
    assert results["full_resolution"]["success"], "Full resolution test failed"
    assert results["full_resolution"]["matches_expected"], "Full resolution size mismatch"
    
    # Test half resolution
    assert results["half_resolution"]["success"], "Half resolution test failed"
    assert results["half_resolution"]["matches_expected"], "Half resolution size mismatch"
    
    # Test quarter resolution
    assert results["quarter_resolution"]["success"], "Quarter resolution test failed"
    assert results["quarter_resolution"]["matches_expected"], "Quarter resolution size mismatch"
    
    # Test custom ROI
    assert results["custom_roi"]["success"], "Custom ROI test failed"
    assert results["custom_roi"]["matches_expected"], "Custom ROI size mismatch"
