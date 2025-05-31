import cv2
import numpy as np
import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.camera_helper import CameraHelper

class EdgeDetection:
    def __init__(self):
        self.camera_helper = None
        self.threshold1 = 100  # Default lower threshold for Canny
        self.threshold2 = 200  # Default upper threshold for Canny

    def set_camera(self, camera_helper):
        self.camera_helper = camera_helper

    def set_thresholds(self, threshold1, threshold2):
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def detect_edges(self, image):
        """Detect edges in the given image using Canny edge detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, self.threshold1, self.threshold2)
        return edges

    def capture_and_detect(self):
        """Capture an image from the camera and detect edges"""
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        grab_result = self.camera_helper.camera.GrabOne(1000)
        img = grab_result.Array
        return self.detect_edges(img)

    def get_edge_percentage(self, image):
        """Calculate the percentage of edge pixels in the image"""
        edges = self.detect_edges(image)
        total_pixels = edges.shape[0] * edges.shape[1]
        edge_pixels = np.count_nonzero(edges)
        return (edge_pixels / total_pixels) * 100

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_edge_detection(camera):
    detector = EdgeDetection()
    detector.set_camera(camera)
    
    # Test edge detection on a captured image
    edges = detector.capture_and_detect()
    assert edges is not None, "Edge detection failed"
    
    # Test edge percentage calculation
    percentage = detector.get_edge_percentage(detector.camera_helper.camera.GrabOne(1000).Array)
    assert 0 <= percentage <= 100, "Edge percentage calculation failed"
