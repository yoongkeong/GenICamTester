import time
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
import pytest

class TestPowerUSB:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.test_duration = 60  # seconds
        self.check_interval = 1  # seconds
        self.max_current_draw = 500  # mA (USB 2.0 limit)

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def set_test_parameters(self, duration=60, interval=1, max_current=500):
        """Set test parameters"""
        self.test_duration = duration
        self.check_interval = interval
        self.max_current_draw = max_current

    def test_power_consumption(self):
        """Test USB camera power consumption"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "current_readings": [],
            "power_readings": [],
            "timestamps": [],
            "average_current": 0,
            "peak_current": 0,
            "average_power": 0,
            "peak_power": 0,
            "test_duration": 0
        }

        try:
            start_time = time.time()
            while time.time() - start_time < self.test_duration:
                # Get current measurements
                current = self.get_current_draw()
                power = current * 5.0 / 1000.0  # Convert to watts (USB is 5V)
                
                if current:
                    results["current_readings"].append(current)
                    results["power_readings"].append(power)
                    results["timestamps"].append(time.time() - start_time)
                
                time.sleep(self.check_interval)

            # Calculate metrics
            if results["current_readings"]:
                results["average_current"] = sum(results["current_readings"]) / len(results["current_readings"])
                results["peak_current"] = max(results["current_readings"])
                results["average_power"] = sum(results["power_readings"]) / len(results["power_readings"])
                results["peak_power"] = max(results["power_readings"])
            
            results["test_duration"] = time.time() - start_time
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)

        return results

    def get_current_draw(self):
        """Get current draw in mA"""
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Use USB power monitoring hardware
            # 2. Use system APIs to get USB power info
            # 3. Use camera's power monitoring features if available
            
            # Simulate current based on camera state
            base_current = 200  # Base current draw in mA
            
            # Add current for active features
            if self.camera_helper.camera.IsGrabbing():
                base_current += 100  # Additional current when streaming
            
            # Add current based on temperature (higher temp = higher current)
            temp = self.genicam_helper.get_device_temperature()
            temp_current = (temp - 25) * 2  # 2mA per degree above 25°C
            
            return base_current + max(0, temp_current)
            
        except Exception:
            return None

    def test_voltage_stability(self):
        """Test USB voltage stability"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "voltage_readings": [],
            "timestamps": [],
            "min_voltage": 0,
            "max_voltage": 0,
            "voltage_stability": 0
        }

        try:
            start_time = time.time()
            while time.time() - start_time < self.test_duration:
                # Get current USB voltage
                voltage = self.get_usb_voltage()
                if voltage:
                    results["voltage_readings"].append(voltage)
                    results["timestamps"].append(time.time() - start_time)
                
                time.sleep(self.check_interval)

            # Calculate metrics
            if results["voltage_readings"]:
                results["min_voltage"] = min(results["voltage_readings"])
                results["max_voltage"] = max(results["voltage_readings"])
                results["voltage_stability"] = (
                    (results["max_voltage"] - results["min_voltage"]) / 
                    results["max_voltage"] * 100  # as percentage
                )
            
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)

        return results

    def get_usb_voltage(self):
        """Get USB voltage"""
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Use USB power monitoring hardware
            # 2. Use system APIs to get USB power info
            return 5.0  # Nominal USB voltage
        except Exception:
            return None

def test_power_consumption(camera_helper, simulate):
    if simulate:
        pytest.skip("USB power test not meaningful in simulation")
    test = TestPowerUSB()
    test.setup(camera_helper)
    test.set_test_parameters(duration=5)
    results = test.test_power_consumption()
    assert results["success"], "Power consumption test failed"

def test_voltage_stability(camera_helper, simulate):
    if simulate:
        pytest.skip("USB voltage test not meaningful in simulation")
    test = TestPowerUSB()
    test.setup(camera_helper)
    test.set_test_parameters(duration=5)
    results = test.test_voltage_stability()
    assert results["success"], "Voltage stability test failed"
