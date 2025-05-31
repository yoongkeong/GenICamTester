import time
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper
import pytest
import numpy as np

class TestMaxFPS:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.test_duration = 5  # seconds
        self.min_frames = 50    # minimum frames to collect

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def set_test_parameters(self, duration=5, min_frames=50):
        """Set test parameters"""
        self.test_duration = duration
        self.min_frames = min_frames

    def test_maximum_fps(self):
        """Test maximum achievable FPS"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        try:
            # Get current exposure time
            current_exposure = self.genicam_helper.get_exposure_time()
            
            # Test with different exposure times
            results = {
                "min_exposure": self.measure_fps(exposure_time=20),  # Minimum exposure
                "default_exposure": self.measure_fps(exposure_time=current_exposure),
                "max_exposure": self.measure_fps(exposure_time=1000)  # 1ms exposure
            }
            
            # Restore original exposure time
            self.genicam_helper.set_exposure_time(current_exposure)
            
            return results
            
        except Exception as e:
            return {
                "error": str(e),
                "fps_achieved": 0,
                "frames_captured": 0,
                "duration": 0
            }

    def measure_fps(self, exposure_time):
        """Measure FPS at specific exposure time"""
        try:
            # Set exposure time
            self.genicam_helper.set_exposure_time(exposure_time)
            
            frames = []
            start_time = time.time()
            
            # Start grabbing
            self.camera_helper.camera.StartGrabbing()
            
            try:
                while time.time() - start_time < self.test_duration:
                    grab_result = self.camera_helper.camera.RetrieveResult(1000)
                    if grab_result.GrabSucceeded():
                        frames.append(grab_result.TimeStamp)
                    grab_result.Release()
            finally:
                self.camera_helper.camera.StopGrabbing()
            
            # Calculate metrics
            duration = time.time() - start_time
            frame_count = len(frames)
            
            if frame_count > 1:
                # Calculate FPS from frame timestamps
                frame_intervals = np.diff(frames)
                avg_interval = np.mean(frame_intervals)
                fps = 1e9 / avg_interval if avg_interval > 0 else 0  # Convert from ns to seconds
            else:
                fps = 0

            return {
                "fps_achieved": fps,
                "frames_captured": frame_count,
                "duration": duration,
                "exposure_time": exposure_time
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "fps_achieved": 0,
                "frames_captured": 0,
                "duration": 0,
                "exposure_time": exposure_time
            }

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_fps_measurement(camera):
    test = TestMaxFPS()
    test.setup(camera)
    
    results = test.test_maximum_fps()
    
    # Check min exposure results
    assert "error" not in results["min_exposure"], "Error in minimum exposure test"
    assert results["min_exposure"]["fps_achieved"] > 0, "No frames captured at minimum exposure"
    
    # Check default exposure results
    assert "error" not in results["default_exposure"], "Error in default exposure test"
    assert results["default_exposure"]["fps_achieved"] > 0, "No frames captured at default exposure"
    
    # Check max exposure results
    assert "error" not in results["max_exposure"], "Error in maximum exposure test"
    assert results["max_exposure"]["fps_achieved"] > 0, "No frames captured at maximum exposure"
    
    # Verify FPS relationship
    assert (results["min_exposure"]["fps_achieved"] >= 
            results["default_exposure"]["fps_achieved"]), "FPS not increasing with lower exposure"
