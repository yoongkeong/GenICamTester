import time
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.camera_helper import CameraHelper

class PowerCycleTest:
    def __init__(self):
        self.camera_helper = None
        self.cycles = 10  # Default number of power cycles
        self.cycle_delay = 5  # Default delay between cycles in seconds
        self.success_count = 0
        self.failure_count = 0

    def set_camera(self, camera_helper):
        self.camera_helper = camera_helper

    def set_test_parameters(self, cycles=10, cycle_delay=5):
        """Set the test parameters"""
        self.cycles = cycles
        self.cycle_delay = cycle_delay

    def run_power_cycle_test(self):
        """Run the power cycle test"""
        if not self.camera_helper:
            raise RuntimeError("Camera helper not initialized")

        self.success_count = 0
        self.failure_count = 0
        
        for cycle in range(self.cycles):
            try:
                print(f"Starting cycle {cycle + 1}/{self.cycles}")
                
                # Disconnect camera
                self.camera_helper.disconnect_camera()
                time.sleep(self.cycle_delay)
                
                # Reconnect camera
                self.camera_helper.connect_camera()
                
                # Verify camera is working by capturing an image
                if self.verify_camera():
                    self.success_count += 1
                else:
                    self.failure_count += 1
                
                time.sleep(self.cycle_delay)
                
            except Exception as e:
                print(f"Error in cycle {cycle + 1}: {str(e)}")
                self.failure_count += 1
        
        return self.get_results()

    def verify_camera(self):
        """Verify camera is working by capturing an image"""
        try:
            if not self.camera_helper.camera:
                return False
            
            grab_result = self.camera_helper.camera.GrabOne(1000)
            return grab_result and grab_result.GrabSucceeded()
            
        except Exception:
            return False

    def get_results(self):
        """Get the test results"""
        return {
            "total_cycles": self.cycles,
            "successful_cycles": self.success_count,
            "failed_cycles": self.failure_count,
            "success_rate": (self.success_count / self.cycles * 100) if self.cycles > 0 else 0
        }

# Test fixtures and functions for pytest
@pytest.fixture(scope='module')
def camera():
    camera_helper = CameraHelper()
    camera_helper.connect_camera(ip_address="192.168.1.10")
    yield camera_helper
    camera_helper.disconnect_camera()

def test_power_cycle(camera):
    test = PowerCycleTest()
    test.set_camera(camera)
    test.set_test_parameters(cycles=3, cycle_delay=2)  # Shorter test for pytest
    
    results = test.run_power_cycle_test()
    assert results["successful_cycles"] > 0, "No successful power cycles"
    assert results["failed_cycles"] == 0, f"Test encountered {results['failed_cycles']} failures"
    assert results["success_rate"] > 0, "Success rate is zero"
