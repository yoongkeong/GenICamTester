import cv2
import numpy as np
import pytest
import time
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.camera_helper import CameraHelper

class LongRunTest:
    def __init__(self):
        self.camera_helper = None
        self.test_duration = 3600  # Default 1 hour
        self.frame_count = 0
        self.errors = 0
        self.start_time = None

    def set_camera(self, camera_helper):
        self.camera_helper = camera_helper

    def set_duration(self, seconds):
        """Set the duration for the long run test"""
        self.test_duration = seconds

    def start_test(self):
        """Start the long run test"""
        if not self.camera_helper or not self.camera_helper.camera:
            raise RuntimeError("Camera not initialized")
        
        self.frame_count = 0
        self.errors = 0
        self.start_time = time.time()
        
        try:
            while time.time() - self.start_time < self.test_duration:
                try:
                    grab_result = self.camera_helper.camera.GrabOne(1000)
                    if grab_result and grab_result.GrabSucceeded():
                        self.frame_count += 1
                    else:
                        self.errors += 1
                except Exception as e:
                    self.errors += 1
                    print(f"Error during frame grab: {str(e)}")
        except KeyboardInterrupt:
            print("Test interrupted by user")
        
        return self.get_results()

    def get_results(self):
        """Get the test results"""
        elapsed_time = time.time() - (self.start_time or time.time())
        fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        return {
            "duration": elapsed_time,
            "frames_captured": self.frame_count,
            "errors": self.errors,
            "average_fps": fps
        }

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_long_run(camera):
    test = LongRunTest()
    test.set_camera(camera)
    test.set_duration(60)  # 1 minute test for pytest
    
    results = test.start_test()
    assert results["frames_captured"] > 0, "No frames were captured"
    assert results["errors"] == 0, f"Test encountered {results['errors']} errors"
    assert results["average_fps"] > 0, "FPS is zero or negative"
