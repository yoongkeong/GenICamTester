# test_InitCam.py
import pytest
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.camera_helper import CameraHelper

class TestInitializeCamera:
    def __init__(self):
        self.camera_helper = None
        self.init_attempts = 3  # Number of initialization attempts
        self.init_delay = 1     # Delay between attempts in seconds

    def set_test_parameters(self, attempts=3, delay=1):
        """Set test parameters"""
        self.init_attempts = attempts
        self.init_delay = delay

    def test_initialization(self, ip_address=None):
        """Test camera initialization"""
        results = {
            "success": False,
            "attempts": 0,
            "error": None,
            "connection_time": 0
        }

        for attempt in range(self.init_attempts):
            try:
                results["attempts"] += 1
                
                # Create new CameraHelper instance
                self.camera_helper = CameraHelper()
                
                # Record start time
                start_time = time.time()
                
                # Try to connect
                if ip_address:
                    self.camera_helper.connect_camera(ip_address=ip_address)
                else:
                    self.camera_helper.connect_camera()
                
                # Calculate connection time
                results["connection_time"] = time.time() - start_time
                
                # Verify camera is operational
                if self.verify_camera():
                    results["success"] = True
                    break
                
            except Exception as e:
                results["error"] = str(e)
                
                # Clean up before next attempt
                if self.camera_helper:
                    try:
                        self.camera_helper.disconnect_camera()
                    except:
                        pass
                self.camera_helper = None
                
                # Wait before next attempt
                if attempt < self.init_attempts - 1:
                    time.sleep(self.init_delay)

        return results

    def verify_camera(self):
        """Verify camera is operational by capturing a test image"""
        try:
            if not self.camera_helper or not self.camera_helper.camera:
                return False
            
            # Try to capture an image
            grab_result = self.camera_helper.camera.GrabOne(1000)
            success = grab_result and grab_result.GrabSucceeded()
            
            # Clean up
            if grab_result:
                grab_result.Release()
                
            return success
            
        except Exception:
            return False

    def cleanup(self):
        """Clean up camera resources"""
        if self.camera_helper:
            try:
                self.camera_helper.disconnect_camera()
            except:
                pass
            self.camera_helper = None

# Test fixtures and functions for pytest
@pytest.fixture(scope='function')
def init_test():
    test = TestInitializeCamera()
    yield test
    test.cleanup()

def test_camera_initialization(init_test):
    results = init_test.test_initialization()
    assert results["success"], f"Camera initialization failed after {results['attempts']} attempts"
    assert results["connection_time"] > 0, "Connection time not recorded"

def test_camera_verification(init_test):
    init_test.test_initialization()
    assert init_test.verify_camera(), "Camera verification failed"
