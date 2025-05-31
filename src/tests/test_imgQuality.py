import cv2
import numpy as np
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestImageQuality:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.min_sharpness = 50  # Minimum acceptable sharpness score
        self.max_noise = 30      # Maximum acceptable noise level
        self.min_contrast = 0.3  # Minimum acceptable contrast ratio

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def capture_test_image(self):
        """Capture a test image from the camera"""
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        grab_result = self.camera_helper.camera.GrabOne(1000)
        if grab_result.GrabSucceeded():
            return grab_result.Array
        raise RuntimeError("Failed to capture test image")

    def calculate_sharpness(self, image):
        """Calculate image sharpness using Laplacian variance"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var()

    def calculate_noise(self, image):
        """Calculate image noise level"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Calculate noise using standard deviation in uniform region
        h, w = gray.shape
        center_region = gray[h//4:3*h//4, w//4:3*w//4]
        return np.std(center_region)

    def calculate_contrast(self, image):
        """Calculate image contrast ratio"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        min_val = np.percentile(gray, 5)
        max_val = np.percentile(gray, 95)
        if min_val == 0:
            min_val = 1  # Avoid division by zero
        return max_val / min_val

    def test_image_quality(self):
        """Run all image quality tests"""
        try:
            image = self.capture_test_image()
            
            # Calculate metrics
            sharpness = self.calculate_sharpness(image)
            noise = self.calculate_noise(image)
            contrast = self.calculate_contrast(image)
            
            # Evaluate results
            results = {
                "sharpness": {
                    "value": sharpness,
                    "pass": sharpness > self.min_sharpness,
                    "threshold": self.min_sharpness
                },
                "noise": {
                    "value": noise,
                    "pass": noise < self.max_noise,
                    "threshold": self.max_noise
                },
                "contrast": {
                    "value": contrast,
                    "pass": contrast > self.min_contrast,
                    "threshold": self.min_contrast
                }
            }
            
            return {
                "success": True,
                "results": results,
                "overall_pass": all(r["pass"] for r in results.values())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "overall_pass": False
            }

    def set_quality_thresholds(self, min_sharpness=None, max_noise=None, min_contrast=None):
        """Set custom thresholds for quality metrics"""
        if min_sharpness is not None:
            self.min_sharpness = min_sharpness
        if max_noise is not None:
            self.max_noise = max_noise
        if min_contrast is not None:
            self.min_contrast = min_contrast

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_image_quality_metrics(camera):
    test = TestImageQuality()
    test.setup(camera)
    
    results = test.test_image_quality()
    assert results["success"], "Image quality test failed to complete"
    
    # Check individual metrics
    metrics = results["results"]
    assert metrics["sharpness"]["pass"], "Image sharpness below threshold"
    assert metrics["noise"]["pass"], "Image noise above threshold"
    assert metrics["contrast"]["pass"], "Image contrast below threshold"
