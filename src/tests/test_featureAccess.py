import pytest
import sys, os
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib.genicam_helper import GenICamHelper
from lib.camera_helper import CameraHelper
from lib.extended_features import ExtendedFeatureTests

class TestFeatureAccess:
    def __init__(self):
        self.camera_helper = None
        self.genicam_helper = None
        self.extended_tests = None
        self.original_settings = {}
        self.logger = logging.getLogger(__name__)

    def setup(self, camera_helper):
        """Set up the test with camera and GenICam helpers"""
        try:
            self.logger.info("Setting up TestFeatureAccess")
            self.camera_helper = camera_helper
            
            # Verify camera is connected and open
            if not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            if not self.camera_helper.camera.IsOpen():
                raise RuntimeError("Camera not open")
                
            # Initialize GenICam helper
            self.genicam_helper = GenICamHelper()
            self.genicam_helper.set_camera(self.camera_helper.camera)
            
            # Initialize extended tests
            self.extended_tests = ExtendedFeatureTests(self.genicam_helper)
            
            # Store original settings
            self.store_original_settings()
            self.logger.info("TestFeatureAccess setup completed successfully")
        except Exception as e:
            self.logger.error(f"Setup failed: {str(e)}")
            raise RuntimeError(f"Setup failed: {str(e)}")

    def store_original_settings(self):
        """Store original camera settings for restoration after tests"""
        try:
            # Store each setting individually to handle failures gracefully
            settings = {}
            
            try:
                settings['exposure'] = self.genicam_helper.get_exposure_time()
                self.logger.debug(f"Stored exposure time: {settings['exposure']}")
            except Exception as e:
                self.logger.warning(f"Could not store exposure time: {e}")
                
            try:
                settings['gain'] = self.genicam_helper.get_gain()
                self.logger.debug(f"Stored gain: {settings['gain']}")
            except Exception as e:
                self.logger.warning(f"Could not store gain: {e}")
                
            try:
                settings['pixel_format'] = self.genicam_helper.get_pixel_format()
                self.logger.debug(f"Stored pixel format: {settings['pixel_format']}")
            except Exception as e:
                self.logger.warning(f"Could not store pixel format: {e}")
                
            try:
                settings['roi'] = self.genicam_helper.get_roi()
                self.logger.debug(f"Stored ROI: {settings['roi']}")
            except Exception as e:
                self.logger.warning(f"Could not store ROI: {e}")
            
            self.original_settings = settings
            self.logger.info(f"Stored original settings: {settings}")
            
        except Exception as e:
            self.logger.error(f"Failed to store settings: {str(e)}")
            raise

    def test_feature_readability(self):
        """Test if all common features are readable"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        readability_results = {}
        features_to_test = [
            ('ExposureTime', self.genicam_helper.get_exposure_time),
            ('Gain', self.genicam_helper.get_gain),
            ('PixelFormat', self.genicam_helper.get_pixel_format),
            ('ROI', self.genicam_helper.get_roi),
            ('TriggerMode', lambda: self.genicam_helper.get_node_value("TriggerMode")),
            ('TriggerSource', lambda: self.genicam_helper.get_node_value("TriggerSource")),
            ('ExposureAuto', lambda: self.genicam_helper.get_node_value("ExposureAuto")),
            ('GainAuto', lambda: self.genicam_helper.get_node_value("GainAuto")),
            ('BalanceWhiteAuto', lambda: self.genicam_helper.get_node_value("BalanceWhiteAuto")),
            ('AcquisitionFrameRate', lambda: self.genicam_helper.get_node_value("AcquisitionFrameRate")),
            ('DeviceLinkThroughputLimit', lambda: self.genicam_helper.get_node_value("DeviceLinkThroughputLimit")),
            ('DeviceTemperature', lambda: self.genicam_helper.get_node_value("DeviceTemperature")),
            ('BlackLevel', lambda: self.genicam_helper.get_node_value("BlackLevel")),
            ('Gamma', lambda: self.genicam_helper.get_node_value("Gamma"))
        ]

        for feature_name, getter_func in features_to_test:
            try:
                value = getter_func()
                self.logger.info(f"Successfully read {feature_name}: {value}")
                readability_results[feature_name] = {
                    'readable': True,
                    'value': value,
                    'error': None
                }
            except Exception as e:
                self.logger.error(f"Failed to read {feature_name}: {e}")
                readability_results[feature_name] = {
                    'readable': False,
                    'value': None,
                    'error': str(e)
                }

        return readability_results

    def test_basic_features(self):
        """Test basic camera feature access"""
        if not self.camera_helper or not self.genicam_helper:
            raise RuntimeError("Test not properly initialized")

        try:
            # First test readability
            read_results = self.test_feature_readability()
            
            # Then test write operations for basic features
            basic_write_results = {
                "exposure": self.test_exposure(),
                "gain": self.test_gain(),
                "pixel_format": self.test_pixel_format(),
                "roi": self.test_roi()
            }
            
            # Test advanced features
            advanced_results = {
                "auto_features": self.test_auto_features(),
                "trigger": self.test_trigger(),
                "image_format": self.test_image_format()
            }

            # Log results
            self.logger.info("Feature test results:")
            self.logger.info(f"Read tests: {read_results}")
            self.logger.info(f"Basic write tests: {basic_write_results}")
            self.logger.info(f"Advanced feature tests: {advanced_results}")

            # Combine all test results
            write_results = basic_write_results.copy()
            for feature_set, results in advanced_results.items():
                if isinstance(results, dict):
                    write_results.update(results)
                else:
                    write_results[feature_set] = results

            return {
                "readability_test": read_results,
                "write_test": write_results
            }

        except Exception as e:
            self.logger.error(f"Feature test failed: {str(e)}")
            raise
        finally:
            self.restore_original_settings()

    def restore_original_settings(self):
        """Restore original camera settings"""
        try:
            if 'exposure' in self.original_settings:
                try:
                    self.genicam_helper.set_exposure_time(self.original_settings['exposure'])
                except Exception as e:
                    self.logger.error(f"Failed to restore exposure: {e}")
                    
            if 'gain' in self.original_settings:
                try:
                    self.genicam_helper.set_gain(self.original_settings['gain'])
                except Exception as e:
                    self.logger.error(f"Failed to restore gain: {e}")
                    
            if 'pixel_format' in self.original_settings:
                try:
                    self.genicam_helper.set_pixel_format(self.original_settings['pixel_format'])
                except Exception as e:
                    self.logger.error(f"Failed to restore pixel format: {e}")
                    
            if 'roi' in self.original_settings:
                try:
                    width, height = self.original_settings['roi']
                    self.genicam_helper.set_roi(width, height)
                except Exception as e:
                    self.logger.error(f"Failed to restore ROI: {e}")
                    
            self.logger.info("Original settings restored")
        except Exception as e:
            self.logger.error(f"Failed to restore settings: {str(e)}")
            raise

    def test_exposure(self):
        """Test exposure time feature"""
        try:
            current = self.genicam_helper.get_exposure_time()
            self.logger.info(f"Current exposure time: {current}")
            
            # Test half and double exposure
            test_values = [current * 0.5, current * 2]
            results = []
            
            for test_value in test_values:
                self.genicam_helper.set_exposure_time(test_value)
                new_value = self.genicam_helper.get_exposure_time()
                self.logger.info(f"Set exposure to {test_value}, got {new_value}")
                results.append(abs(new_value - test_value) < 0.1 * test_value)  # 10% tolerance
                
            return all(results)
        except Exception as e:
            self.logger.error(f"Exposure test failed: {str(e)}")
            return False

    def test_gain(self):
        """Test gain feature"""
        try:
            current = self.genicam_helper.get_gain()
            self.logger.info(f"Current gain: {current}")
            
            # Test gain increase and decrease
            test_values = [current + 1, max(0, current - 1)]  # Ensure gain doesn't go negative
            results = []
            
            for test_value in test_values:
                self.genicam_helper.set_gain(test_value)
                new_value = self.genicam_helper.get_gain()
                self.logger.info(f"Set gain to {test_value}, got {new_value}")
                results.append(abs(new_value - test_value) < 0.1)  # Tolerance of 0.1
                
            return all(results)
        except Exception as e:
            self.logger.error(f"Gain test failed: {str(e)}")
            return False

    def test_pixel_format(self):
        """Test pixel format feature"""
        try:
            formats = self.genicam_helper.get_available_pixel_formats()
            self.logger.info(f"Available pixel formats: {formats}")
            
            if not formats:
                self.logger.warning("No pixel formats available")
                return False
                
            current = self.genicam_helper.get_pixel_format()
            self.logger.info(f"Current pixel format: {current}")
            
            # Try to switch to a different format
            test_format = next((fmt for fmt in formats if fmt != current), None)
            if not test_format:
                self.logger.warning("No alternative pixel format to test")
                return True  # Consider it a pass if we can't find an alternative
                
            self.genicam_helper.set_pixel_format(test_format)
            new_format = self.genicam_helper.get_pixel_format()
            self.logger.info(f"Set pixel format to {test_format}, got {new_format}")
            
            return new_format == test_format
        except Exception as e:
            self.logger.error(f"Pixel format test failed: {str(e)}")
            return False

    def test_roi(self):
        """Test ROI feature"""
        try:
            width, height = self.genicam_helper.get_roi()
            self.logger.info(f"Current ROI: {width}x{height}")
            
            # Test half size ROI
            new_width = width // 2
            new_height = height // 2
            
            self.genicam_helper.set_roi(new_width, new_height)
            current_width, current_height = self.genicam_helper.get_roi()
            self.logger.info(f"Set ROI to {new_width}x{new_height}, got {current_width}x{current_height}")
            
            return current_width == new_width and current_height == new_height
        except Exception as e:
            self.logger.error(f"ROI test failed: {str(e)}")
            return False

    def test_auto_features(self):
        """Test automatic control features (exposure, gain, white balance)"""
        try:
            results = {}
            
            # Test auto exposure
            if self.genicam_helper.has_node("ExposureAuto"):
                try:
                    current = self.genicam_helper.get_node_value("ExposureAuto")
                    self.logger.info(f"Current ExposureAuto: {current}")
                    
                    # Test different auto exposure modes
                    for mode in ["Off", "Once", "Continuous"]:
                        try:
                            self.genicam_helper.set_node_value("ExposureAuto", mode)
                            new_value = self.genicam_helper.get_node_value("ExposureAuto")
                            self.logger.info(f"Set ExposureAuto to {mode}, got {new_value}")
                            if new_value == mode:
                                results["auto_exposure"] = True
                                break
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.error(f"Auto exposure test failed: {e}")
                    results["auto_exposure"] = False
            else:
                results["auto_exposure"] = None  # Not supported
                
            # Test auto gain
            if self.genicam_helper.has_node("GainAuto"):
                try:
                    current = self.genicam_helper.get_node_value("GainAuto")
                    self.logger.info(f"Current GainAuto: {current}")
                    
                    # Test different auto gain modes
                    for mode in ["Off", "Once", "Continuous"]:
                        try:
                            self.genicam_helper.set_node_value("GainAuto", mode)
                            new_value = self.genicam_helper.get_node_value("GainAuto")
                            self.logger.info(f"Set GainAuto to {mode}, got {new_value}")
                            if new_value == mode:
                                results["auto_gain"] = True
                                break
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.error(f"Auto gain test failed: {e}")
                    results["auto_gain"] = False
            else:
                results["auto_gain"] = None  # Not supported
                
            # Test auto white balance
            if self.genicam_helper.has_node("BalanceWhiteAuto"):
                try:
                    current = self.genicam_helper.get_node_value("BalanceWhiteAuto")
                    self.logger.info(f"Current BalanceWhiteAuto: {current}")
                    
                    # Test different white balance modes
                    for mode in ["Off", "Once", "Continuous"]:
                        try:
                            self.genicam_helper.set_node_value("BalanceWhiteAuto", mode)
                            new_value = self.genicam_helper.get_node_value("BalanceWhiteAuto")
                            self.logger.info(f"Set BalanceWhiteAuto to {mode}, got {new_value}")
                            if new_value == mode:
                                results["auto_white_balance"] = True
                                break
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.error(f"Auto white balance test failed: {e}")
                    results["auto_white_balance"] = False
            else:
                results["auto_white_balance"] = None  # Not supported
                
            return results
        except Exception as e:
            self.logger.error(f"Auto features test failed: {str(e)}")
            return False
            
    def test_trigger(self):
        """Test trigger configuration"""
        try:
            results = {}
            
            # Test trigger mode
            if self.genicam_helper.has_node("TriggerMode"):
                try:
                    current = self.genicam_helper.get_node_value("TriggerMode")
                    self.logger.info(f"Current TriggerMode: {current}")
                    
                    # Test Off/On modes
                    for mode in ["Off", "On"]:
                        try:
                            self.genicam_helper.set_node_value("TriggerMode", mode)
                            new_value = self.genicam_helper.get_node_value("TriggerMode")
                            self.logger.info(f"Set TriggerMode to {mode}, got {new_value}")
                            if new_value == mode:
                                results["trigger_mode"] = True
                                break
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.error(f"Trigger mode test failed: {e}")
                    results["trigger_mode"] = False
            else:
                results["trigger_mode"] = None  # Not supported
                
            # Test trigger source if trigger mode is supported
            if self.genicam_helper.has_node("TriggerSource") and results.get("trigger_mode"):
                try:
                    current = self.genicam_helper.get_node_value("TriggerSource")
                    self.logger.info(f"Current TriggerSource: {current}")
                    
                    # Get available trigger sources
                    sources = self.genicam_helper.get_enum_entries("TriggerSource")
                    self.logger.info(f"Available trigger sources: {sources}")
                    
                    # Test each available source
                    for source in sources:
                        try:
                            self.genicam_helper.set_node_value("TriggerSource", source)
                            new_value = self.genicam_helper.get_node_value("TriggerSource")
                            self.logger.info(f"Set TriggerSource to {source}, got {new_value}")
                            if new_value == source:
                                results["trigger_source"] = True
                                break
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.error(f"Trigger source test failed: {e}")
                    results["trigger_source"] = False
            else:
                results["trigger_source"] = None  # Not supported

            return results
        except Exception as e:
            self.logger.error(f"Trigger test failed: {str(e)}")
            return False

    def test_image_format(self):
        """Test image format related features"""
        try:
            results = {}
            
            # Test width/height adjustment
            if self.genicam_helper.has_node("Width") and self.genicam_helper.has_node("Height"):
                try:
                    current_width = self.genicam_helper.get_node_value("Width")
                    current_height = self.genicam_helper.get_node_value("Height")
                    self.logger.info(f"Current dimensions: {current_width}x{current_height}")
                    
                    # Get increment values
                    width_inc = self.genicam_helper.get_node_value("WidthInc") if self.genicam_helper.has_node("WidthInc") else 1
                    height_inc = self.genicam_helper.get_node_value("HeightInc") if self.genicam_helper.has_node("HeightInc") else 1
                    
                    # Test smaller dimensions
                    new_width = current_width - width_inc
                    new_height = current_height - height_inc
                    
                    self.genicam_helper.set_node_value("Width", new_width)
                    self.genicam_helper.set_node_value("Height", new_height)
                    
                    test_width = self.genicam_helper.get_node_value("Width")
                    test_height = self.genicam_helper.get_node_value("Height")
                    
                    results["dimensions"] = (test_width == new_width and test_height == new_height)
                except Exception as e:
                    self.logger.error(f"Dimension test failed: {e}")
                    results["dimensions"] = False
            else:
                results["dimensions"] = None  # Not supported
                
            # Test offset adjustment
            if self.genicam_helper.has_node("OffsetX") and self.genicam_helper.has_node("OffsetY"):
                try:
                    current_x = self.genicam_helper.get_node_value("OffsetX")
                    current_y = self.genicam_helper.get_node_value("OffsetY")
                    self.logger.info(f"Current offset: ({current_x},{current_y})")
                    
                    # Get increment values
                    x_inc = self.genicam_helper.get_node_value("OffsetXInc") if self.genicam_helper.has_node("OffsetXInc") else 1
                    y_inc = self.genicam_helper.get_node_value("OffsetYInc") if self.genicam_helper.has_node("OffsetYInc") else 1
                    
                    # Test offset adjustment
                    new_x = current_x + x_inc if current_x + x_inc <= self.genicam_helper.get_node_value("OffsetXMax") else current_x
                    new_y = current_y + y_inc if current_y + y_inc <= self.genicam_helper.get_node_value("OffsetYMax") else current_y
                    
                    self.genicam_helper.set_node_value("OffsetX", new_x)
                    self.genicam_helper.set_node_value("OffsetY", new_y)
                    
                    test_x = self.genicam_helper.get_node_value("OffsetX")
                    test_y = self.genicam_helper.get_node_value("OffsetY")
                    
                    results["offset"] = (test_x == new_x and test_y == new_y)
                except Exception as e:
                    self.logger.error(f"Offset test failed: {e}")
                    results["offset"] = False
            else:
                results["offset"] = None  # Not supported
                
            return results
        except Exception as e:
            self.logger.error(f"Image format test failed: {str(e)}")
            return False

@pytest.fixture(scope='module')
def camera():
    """Create camera fixture that works with both USB and GigE cameras"""
    camera_helper = CameraHelper()
    # Enumerate available cameras
    cameras = CameraHelper.enumerate_cameras()
    if not cameras:
        pytest.skip("No cameras found")
    
    try:
        # Try to connect to the first available camera
        camera_helper.connect_camera(cameras[0])
        yield camera_helper
    except Exception as e:
        pytest.fail(f"Failed to connect to camera: {str(e)}")
    finally:
        try:
            camera_helper.disconnect_camera()
        except Exception as e:
            print(f"Warning: Failed to disconnect camera: {str(e)}")

def test_feature_access(camera):
    """Test camera feature access and configuration"""
    test = TestFeatureAccess()
    try:
        test.setup(camera)
        results = test.test_basic_features()
        
        # Verify test results
        for feature, details in results["readability_test"].items():
            assert details['readable'], f"Feature {feature} not readable: {details['error']}"
            assert details['value'] is not None, f"Feature {feature} returned None value"
        
        for feature, success in results["write_test"].items():
            assert success, f"Feature write test failed: {feature}"
            
    except Exception as e:
        pytest.fail(f"Feature access test failed: {str(e)}")
    finally:
        try:
            test.restore_original_settings()
        except Exception as e:
            print(f"Warning: Failed to restore settings: {str(e)}")
