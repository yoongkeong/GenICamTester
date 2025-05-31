# test_imageAcq.py
import cv2
import numpy as np
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper

class TestImageAcquisition:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.num_frames = 100  # Default number of frames to test
        self.timeout_ms = 1000

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def set_test_parameters(self, num_frames=100, timeout_ms=1000):
        """Set test parameters"""
        self.num_frames = num_frames
        self.timeout_ms = timeout_ms

    def test_continuous_acquisition(self):
        """Test continuous image acquisition"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        successful_frames = 0
        failed_frames = 0
        frame_times = []

        try:
            self.camera_helper.camera.StartGrabbing()
            
            for i in range(self.num_frames):
                try:
                    grab_result = self.camera_helper.camera.RetrieveResult(self.timeout_ms)
                    if grab_result.GrabSucceeded():
                        successful_frames += 1
                        frame_times.append(grab_result.TimeStamp)
                    else:
                        failed_frames += 1
                except Exception:
                    failed_frames += 1
                finally:
                    if grab_result:
                        grab_result.Release()

        finally:
            if self.camera_helper.camera.IsGrabbing():
                self.camera_helper.camera.StopGrabbing()

        # Calculate metrics
        frame_intervals = np.diff(frame_times) if len(frame_times) > 1 else []
        avg_interval = np.mean(frame_intervals) if len(frame_intervals) > 0 else 0
        fps = 1e9 / avg_interval if avg_interval > 0 else 0  # Convert nanoseconds to FPS

        return {
            "total_frames": self.num_frames,
            "successful_frames": successful_frames,
            "failed_frames": failed_frames,
            "success_rate": (successful_frames / self.num_frames * 100),
            "average_fps": fps
        }

    def test_single_image(self):
        """Test single image acquisition"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        try:
            grab_result = self.camera_helper.camera.GrabOne(self.timeout_ms)
            success = grab_result.GrabSucceeded()
            image_data = None
            
            if success:
                image_data = grab_result.Array
            
            grab_result.Release()
            
            return {
                "success": success,
                "has_image_data": image_data is not None,
                "image_shape": image_data.shape if image_data is not None else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "has_image_data": False,
                "image_shape": None,
                "error": str(e)
            }

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_image_acquisition(camera):
    test = TestImageAcquisition()
    test.setup(camera)
    test.set_test_parameters(num_frames=10)  # Shorter test for pytest
    
    # Test continuous acquisition
    results = test.test_continuous_acquisition()
    assert results["success_rate"] > 95, "Continuous acquisition success rate too low"
    assert results["average_fps"] > 0, "No frames captured"
    
    # Test single image acquisition
    single_result = test.test_single_image()
    assert single_result["success"], "Single image acquisition failed"
    assert single_result["has_image_data"], "No image data received"
