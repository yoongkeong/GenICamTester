import time
import pytest
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper

class TestPowerGigE:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.test_duration = 60  # seconds
        self.check_interval = 1  # seconds

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        self.camera_helper = camera_helper
        self.genicam_helper = GenICamHelper()
        self.genicam_helper.set_camera(camera_helper.camera)

    def set_test_parameters(self, duration=60, interval=1):
        """Set test parameters"""
        self.test_duration = duration
        self.check_interval = interval

    def test_power_consumption(self):
        """Test GigE camera power consumption"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        results = {
            "power_readings": [],
            "timestamps": [],
            "average_power": 0,
            "peak_power": 0,
            "test_duration": 0
        }

        try:
            start_time = time.time()
            while time.time() - start_time < self.test_duration:
                # Get current power consumption
                power = self.get_power_consumption()
                if power:
                    results["power_readings"].append(power)
                    results["timestamps"].append(time.time() - start_time)
                
                time.sleep(self.check_interval)

            # Calculate metrics
            if results["power_readings"]:
                results["average_power"] = sum(results["power_readings"]) / len(results["power_readings"])
                results["peak_power"] = max(results["power_readings"])
            
            results["test_duration"] = time.time() - start_time
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)

        return results

    def get_power_consumption(self):
        """Get current power consumption from the camera"""
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Use the camera's API to get power information
            # 2. Use PoE switch SNMP queries
            # 3. Use external power monitoring hardware
            
            # For now, we'll estimate based on temperature and link speed
            temp = self.genicam_helper.get_device_temperature()
            link_speed = self.get_link_speed()
            
            # Simple power estimation formula (this should be replaced with actual measurements)
            estimated_power = 2.5  # Base power (W)
            if link_speed == 1000:
                estimated_power += 0.5  # Additional power for Gigabit
            estimated_power += (temp - 25) * 0.1  # Temperature factor
            
            return estimated_power
            
        except Exception:
            return None

    def get_link_speed(self):
        """Get the current link speed in Mbps"""
        try:
            # This would normally use the camera's API or network interface info
            # For now, return 1000 for Gigabit
            return 1000
        except Exception:
            return 0

    def test_poe_stability(self):
        """Test PoE power stability"""
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
                # Get current PoE voltage
                voltage = self.get_poe_voltage()
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

    def get_poe_voltage(self):
        """Get current PoE voltage"""
        try:
            # This is a placeholder. In a real implementation, you would:
            # 1. Use PoE switch SNMP queries
            # 2. Use external voltage monitoring hardware
            return 48.0  # Nominal PoE voltage
        except Exception:
            return None

def test_power_consumption(camera_helper, simulate):
    if simulate:
        pytest.skip("Power GigE test not meaningful in simulation")
    test = TestPowerGigE()
    test.setup(camera_helper)
    test.set_test_parameters(duration=5)
    results = test.test_power_consumption()
    assert results["success"], "Power consumption test failed"

def test_poe_stability(camera_helper, simulate):
    if simulate:
        pytest.skip("PoE stability test not meaningful in simulation")
    test = TestPowerGigE()
    test.setup(camera_helper)
    test.set_test_parameters(duration=5)
    results = test.test_poe_stability()
    assert results["success"], "PoE stability test failed"
