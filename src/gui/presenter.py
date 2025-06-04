# presenter.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import QTimer
from pypylon import pylon
import cv2
import numpy as np
import time
import logging

class CameraPresenter:
    def __init__(self, view):
        self.view = view  # Reference to the CameraTestGUI instance
        self.camera = None
        self.camera_helper = None
        self.driver_helper = None
        self.genicam_helper = None
        self.live_timer = None
        self.is_live_grabbing = False
        self.is_long_run_test = False
        self.long_run_start_time = None
        self.long_run_frame_count = 0
        self.long_run_last_fps_update = None
        self.long_run_last_frame_count = 0
        self.current_fps = 0
        self.frame_count = 0
        self.test_start_time = None
        self._last_frame_log_time = 0
        self._frames_since_last_log = 0
        self._init_logging()

    def _init_logging(self):
        """Initialize logging for the presenter"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def set_camera_helper(self, helper):
        self.camera_helper = helper
        self.logger.info("Camera helper set")

    def set_driver_helper(self, helper):
        self.driver_helper = helper
        self.logger.info("Driver helper set")

    def set_genicam_helper(self, helper):
        self.genicam_helper = helper
        self.logger.info("GenICam helper set")

    def add_functionality(self, name, func):
        setattr(self, name, func)
        self.logger.debug(f"Added functionality: {name}")

    def add_test(self, name, test):
        setattr(self, name, test)
        self.logger.debug(f"Added test: {name}")

    def start_live_view(self):
        """Start live view of the camera with enhanced error checking"""
        try:
            if not self.camera:
                error_msg = "Cannot start live view: No camera connected"
                self.logger.error(error_msg)
                self.view.log_message(error_msg, "ERROR")
                return False
                
            if not self.camera.IsOpen():
                error_msg = "Cannot start live view: Camera is not open"
                self.logger.error(error_msg)
                self.view.log_message(error_msg, "ERROR")
                return False

            # Configure camera for continuous acquisition
            try:
                if hasattr(self.camera, 'AcquisitionMode'):
                    self.camera.AcquisitionMode.SetValue('Continuous')
                    self.logger.debug("Set acquisition mode to Continuous")
            except Exception as e:
                self.logger.warning(f"Could not set acquisition mode: {str(e)}")
                
            # Configure frame rate if available
            try:
                if hasattr(self.camera, 'AcquisitionFrameRateEnable'):
                    self.camera.AcquisitionFrameRateEnable.SetValue(True)
                    if hasattr(self.camera, 'AcquisitionFrameRate'):
                        current_rate = self.camera.AcquisitionFrameRate.GetValue()
                        self.logger.debug(f"Current frame rate: {current_rate} fps")
            except Exception as e:
                self.logger.warning(f"Could not configure frame rate: {str(e)}")
                
            # Start grabbing
            if self.camera.IsGrabbing():
                self.logger.debug("Camera was already grabbing, stopping first")
                self.camera.StopGrabbing()
                
            self.logger.debug("Starting camera grabbing")
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            # Verify grabbing started successfully
            if not self.camera.IsGrabbing():
                error_msg = "Failed to start camera grabbing"
                self.logger.error(error_msg)
                self.view.log_message(error_msg, "ERROR")
                return False
                
            # Reset frame counting
            self._frames_since_last_log = 0
            self._last_frame_log_time = time.time()
                
            # Test first frame grab
            test_frame = self.camera_helper.get_frame(self.camera)
            if test_frame is None:
                error_msg = "Camera started but could not grab test frame"
                self.logger.error(error_msg)
                self.view.log_message(error_msg, "ERROR")
                if self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
                return False
                
            self.is_live_grabbing = True
            self.logger.info("Live view started successfully")
            self.view.log_message("Live view started", "SUCCESS")
            return True
            
        except Exception as e:
            error_msg = f"Error starting live view: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")
            self.is_live_grabbing = False
            if self.camera and self.camera.IsGrabbing():
                try:
                    self.camera.StopGrabbing()
                except:
                    pass
            return False

    def stop_live_view(self):
        """Stop live view"""
        try:
            if self.camera and self.camera.IsGrabbing():
                self.logger.debug(f"Stopping camera grabbing. Frames since last log: {self._frames_since_last_log}")
                self.camera.StopGrabbing()
                
            self.is_live_grabbing = False
            self.logger.info("Live view stopped")
            self.view.log_message("Live view stopped", "INFO")
            
        except Exception as e:
            error_msg = f"Error stopping live view: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")

    def get_current_frame(self):
        """Get the current frame with enhanced error checking"""
        if not self.camera:
            self.logger.error("Cannot get frame: No camera connected")
            return None
            
        if not self.is_live_grabbing and not self.is_long_run_test:
            self.logger.error("Cannot get frame: Camera is not grabbing")
            return None
            
        try:
            frame = self.camera_helper.get_frame(self.camera)
            if frame is not None:
                self._frames_since_last_log += 1
                
                if self.is_long_run_test:
                    self.long_run_frame_count += 1
                    
                # Log frame statistics periodically
                current_time = time.time()
                if current_time - self._last_frame_log_time >= 5.0:  # Log every 5 seconds
                    fps = self._frames_since_last_log / (current_time - self._last_frame_log_time)
                    self.logger.debug(
                        f"Frames grabbed: {self._frames_since_last_log}, "
                        f"FPS: {fps:.1f}, Shape: {frame.shape}"
                    )
                    self._frames_since_last_log = 0
                    self._last_frame_log_time = current_time
                    
                return frame
            else:
                error_msg = "Failed to get frame from camera"
                self.logger.error(error_msg)
                if self.is_long_run_test:
                    self.view.log_message(error_msg, "ERROR")
                return None
                
        except Exception as e:
            error_msg = f"Error getting frame: {str(e)}"
            self.logger.error(error_msg)
            if self.is_long_run_test:
                self.view.log_message(error_msg, "ERROR")
            return None

    def detect_usb_camera(self):
        """Detect and connect to a USB camera"""
        try:
            self.logger.info("Starting USB camera discovery...")
            if self.camera_helper is None:
                raise RuntimeError("Camera helper not initialized")
                
            # Get list of available cameras
            cameras = self.camera_helper.get_usb_cameras()
            if not cameras:
                self.view.log_message("No USB cameras found", "WARNING")
                return
                
            selected_camera = None
            if len(cameras) == 1:
                selected_camera = cameras[0]
            else:
                from gui.main_gui import CameraSelectionDialog
                dialog = CameraSelectionDialog(self.view, cameras)
                if dialog.exec_() == QDialog.Accepted:
                    selected_camera = dialog.get_selected_camera()
            
            if selected_camera:
                # Connect to the selected camera
                self.camera = self.camera_helper.connect_camera(selected_camera)
                if self.camera:
                    self.view.log_message(
                        f"Successfully connected to camera: {selected_camera.get('name', 'Unknown')} "
                        f"(SN: {selected_camera.get('id', 'Unknown')})",
                        "SUCCESS"
                    )
                    # Update camera details
                    self.update_camera_details(selected_camera)
                    # Switch to test selection page
                    self.view.stacked_widget.setCurrentWidget(self.view.test_selection_page)
                else:
                    self.view.log_message("Failed to connect to camera", "ERROR")
            
        except Exception as e:
            self.logger.error(f"USB camera detection error: {str(e)}")
            self.view.log_message(f"Error detecting USB camera: {str(e)}", "ERROR")

    def update_camera_details(self, camera_info):
        """Update camera details in the GUI with enhanced error handling"""
        try:
            details = {
                'name': camera_info.get('name', 'Unknown'),
                'manufacturer': 'Basler',
                'serial_number': camera_info.get('id', 'Unknown'),
                'interface': camera_info.get('interface', 'Unknown'),
                'firmware_version': 'N/A',
                'sensor_type': 'N/A',
                'sensor_size': 'N/A',
                'pixel_size': 'N/A',
            }

            if self.camera:
                try:
                    if hasattr(self.camera, 'DeviceFirmwareVersion'):
                        details['firmware_version'] = self.camera.DeviceFirmwareVersion.GetValue()
                except Exception as e:
                    self.logger.warning(f"Could not get firmware version: {str(e)}")

                try:
                    if hasattr(self.camera, 'SensorType'):
                        details['sensor_type'] = self.camera.SensorType.GetValue()
                except Exception as e:
                    self.logger.warning(f"Could not get sensor type: {str(e)}")

                try:
                    if hasattr(self.camera, 'SensorWidth') and hasattr(self.camera, 'SensorHeight'):
                        width = self.camera.SensorWidth.GetValue()
                        height = self.camera.SensorHeight.GetValue()
                        details['sensor_size'] = f"{width}x{height}"
                except Exception as e:
                    self.logger.warning(f"Could not get sensor size: {str(e)}")

                try:
                    if hasattr(self.camera, 'PixelSize'):
                        pixel_size = self.camera.PixelSize.GetValue()
                        details['pixel_size'] = f"{pixel_size} µm"
                except Exception as e:
                    self.logger.warning(f"Could not get pixel size: {str(e)}")

            # Add documentation link
            model = camera_info.get('name', '').lower()
            details['documentation_link'] = f"https://docs.baslerweb.com/{model}"

            self.view.update_camera_details(details)
            self.logger.info("Camera details updated successfully")

        except Exception as e:
            self.logger.error(f"Error updating camera details: {str(e)}")
            # Still try to show basic info
            self.view.update_camera_details(camera_info)

    def cleanup(self):
        """Clean up resources before closing"""
        try:
            if self.camera:
                if self.is_live_grabbing:
                    self.stop_live_view()
                if hasattr(self.camera, 'IsGrabbing') and self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
                if hasattr(self.camera, 'Close') and self.camera.IsOpen():
                    self.camera.Close()
                self.camera = None
            self.logger.info("Cleaning up resources")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def disconnect_camera(self):
        """Disconnect the current camera"""
        try:
            if self.camera:
                if self.is_live_grabbing:
                    self.stop_live_view()
                if self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
                if self.camera.IsOpen():
                    self.camera.Close()
                self.camera = None
                self.logger.info("Camera disconnected successfully")
                return True
        except Exception as e:
            self.logger.error(f"Error disconnecting camera: {str(e)}")
        return False

    def start_long_run_test(self):
        """Start long run test with enhanced error handling"""
        if not self.camera:
            self.view.log_message("No camera connected", "ERROR")
            return False

        try:
            if self.is_live_grabbing:
                self.stop_live_view()

            # Configure camera for continuous acquisition
            if hasattr(self.camera, 'AcquisitionMode'):
                self.camera.AcquisitionMode.SetValue('Continuous')
                self.logger.debug("Set acquisition mode to Continuous")
                
            # Configure frame rate if available
            if hasattr(self.camera, 'AcquisitionFrameRateEnable'):
                self.camera.AcquisitionFrameRateEnable.SetValue(True)
                if hasattr(self.camera, 'AcquisitionFrameRate'):
                    max_frame_rate = self.camera.AcquisitionFrameRate.GetMax()
                    self.camera.AcquisitionFrameRate.SetValue(max_frame_rate)
                    actual_frame_rate = self.camera.AcquisitionFrameRate.GetValue()
                    self.logger.info(f"Set frame rate to {actual_frame_rate:.1f} fps")

            # Start grabbing
            if self.camera.IsGrabbing():
                self.logger.debug("Camera was already grabbing, stopping first")
                self.camera.StopGrabbing()
                
            self.logger.debug("Starting camera grabbing for long run test")
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            # Verify grabbing started successfully
            if not self.camera.IsGrabbing():
                raise RuntimeError("Failed to start camera grabbing")
                
            # Try to get first frame to verify everything is working
            test_frame = self.camera_helper.get_frame(self.camera)
            if test_frame is None:
                raise RuntimeError("Failed to retrieve test frame")

            self.is_long_run_test = True
            self.long_run_start_time = time.time()
            self.long_run_frame_count = 0
            self.long_run_last_fps_update = time.time()
            self.long_run_last_frame_count = 0
            self._frames_since_last_log = 0
            self._last_frame_log_time = time.time()

            self.logger.info("Long run test started successfully")
            self.view.log_message("Long run test started successfully", "SUCCESS")
            return True
        except Exception as e:
            error_msg = f"Error starting long run test: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")
            self.is_long_run_test = False
            if self.camera and self.camera.IsGrabbing():
                try:
                    self.camera.StopGrabbing()
                except:
                    pass
            return False

    def stop_long_run_test(self):
        """Stop long run test with statistics logging"""
        self.logger.info("Stopping long run test")
        try:
            if not self.is_long_run_test:
                return

            if self.camera and self.camera.IsGrabbing():
                self.camera.StopGrabbing()
                
            # Calculate final statistics
            total_time = time.time() - self.long_run_start_time
            avg_fps = self.long_run_frame_count / total_time if total_time > 0 else 0
            
            stats_msg = (
                f"Long run test completed:\n"
                f"Total frames: {self.long_run_frame_count:,}\n"
                f"Test duration: {total_time:.1f} seconds\n"
                f"Average FPS: {avg_fps:.1f}"
            )
            
            self.logger.info(stats_msg)
            self.view.log_message(stats_msg, "SUCCESS")
            
        except Exception as e:
            error_msg = f"Error stopping long run test: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")
        finally:
            self.is_long_run_test = False
            self._frames_since_last_log = 0
            
    def get_current_frame(self):
        """Get the current frame with enhanced error checking and reduced logging"""
        if not self.camera:
            return None
            
        if not self.is_live_grabbing and not self.is_long_run_test:
            return None
            
        try:
            frame = self.camera_helper.get_frame(self.camera)
            if frame is not None:
                self._frames_since_last_log += 1
                
                if self.is_long_run_test:
                    self.long_run_frame_count += 1
                    
                # Log frame statistics periodically (every 5 seconds)
                current_time = time.time()
                if current_time - self._last_frame_log_time >= 5.0:
                    fps = self._frames_since_last_log / (current_time - self._last_frame_log_time)
                    self.logger.debug(
                        f"Frame stats: Count={self._frames_since_last_log}, "
                        f"FPS={fps:.1f}, Shape={frame.shape}"
                    )
                    self._frames_since_last_log = 0
                    self._last_frame_log_time = current_time
                    
                return frame
            else:
                # Only log error once per second to avoid spam
                current_time = time.time()
                if not hasattr(self, '_last_error_log_time') or current_time - self._last_error_log_time >= 1.0:
                    self.logger.error("Failed to get frame from camera")
                    self._last_error_log_time = current_time
                return None
                
        except Exception as e:
            # Only log error once per second
            current_time = time.time()
            if not hasattr(self, '_last_error_log_time') or current_time - self._last_error_log_time >= 1.0:
                self.logger.error(f"Error getting frame: {str(e)}")
                self._last_error_log_time = current_time
            return None

    def get_long_run_stats(self):
        """Get current statistics for long run test"""
        if not self.is_long_run_test:
            return {
                'frames_captured': 0,
                'current_fps': 0,
                'elapsed_time': 0,
                'errors': 0
            }
        
        current_time = time.time()
        elapsed_time = current_time - self.long_run_start_time if self.long_run_start_time else 0
        
        # Calculate current FPS based on frames since last update
        frames_since_last = self.long_run_frame_count - self.long_run_last_frame_count
        time_since_last = current_time - self.long_run_last_fps_update
        current_fps = frames_since_last / time_since_last if time_since_last > 0 else 0
        
        # Update last values for next calculation
        self.long_run_last_frame_count = self.long_run_frame_count
        self.long_run_last_fps_update = current_time
        
        return {
            'frames_captured': self.long_run_frame_count,
            'current_fps': current_fps,
            'elapsed_time': elapsed_time,
            'errors': 0  # TODO: Implement error tracking if needed
        }
    
    def run_feature_tests(self):
        """Run camera feature access tests"""
        try:
            from tests.test_featureAccess import TestFeatureAccess
            
            self.logger.info("Starting feature access tests")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestFeatureAccess()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_basic_features()
                
                # Log detailed results
                self.logger.info("Feature test results:")
                for feature, details in results["readability_test"].items():
                    if details['readable']:
                        self.logger.info(f"{feature}: Read successful, value: {details['value']}")
                    else:
                        self.logger.warning(f"{feature}: Read failed - {details['error']}")
                
                for feature, result in results["write_test"].items():
                    if isinstance(result, dict):
                        if 'success' in result:
                            success = result['success']
                            error = result.get('error', 'Unknown error')
                            self.logger.info(f"{feature}: Write {'successful' if success else f'failed - {error}'}")
                        else:
                            # Handle test result dictionaries that contain sub-results
                            self.logger.info(f"{feature} test results:")
                            for subtest, value in result.items():
                                if value is None:
                                    self.logger.info(f"  - {subtest}: Not Supported")
                                elif isinstance(value, bool):
                                    self.logger.info(f"  - {subtest}: {'successful' if value else 'failed'}")
                                else:
                                    self.logger.info(f"  - {subtest}: {value}")
                    elif isinstance(result, bool):
                        self.logger.info(f"{feature}: Write {'successful' if result else 'failed'}")
                    elif result is None:
                        self.logger.info(f"{feature}: Not Supported")
                    else:
                        self.logger.warning(f"{feature}: Invalid result type - {type(result)}")
                
                # Update view with results
                summary = self._format_test_results(results)
                self.view.update_test_results("Feature Tests", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Feature test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
                
            finally:
                # Always try to restore original settings
                try:
                    test.restore_original_settings()
                except Exception as e:
                    self.logger.error(f"Failed to restore camera settings: {str(e)}")
        except Exception as e:
            error_msg = f"Failed to initialize feature tests: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def _format_test_results(self, results):
        """Format test results into a readable summary with improved formatting"""
        summary = []
        
        # Add header with timestamp
        summary.append("=== Feature Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Add readability test results
        summary.append("=== Readability Tests ===")
        summary.append("-" * 80)
        summary.append(f"{'Status':<8}{'Feature':<32}{'Value/Error'}")
        summary.append("-" * 80)
        for feature, details in results["readability_test"].items():
            status = "✓" if details['readable'] else "✗"
            value = details['value'] if details['readable'] else details['error']
            summary.append(f"{status:<8}{feature:<32}{value}")
        
        # Add write test results
        summary.append("\n=== Write Tests ===")
        summary.append("-" * 80)
        summary.append(f"{'Status':<8}{'Feature':<32}{'Error (if any)'}")
        summary.append("-" * 80)
        for feature, result in results["write_test"].items():
            if isinstance(result, dict):
                status = "✓" if result.get('success', False) else "✗"
                error = f" - {result['error']}" if not result.get('success', False) else ""
            else:
                status = "✓" if result else "✗"
                error = ""
            summary.append(f"{status:<8}{feature:<32}{error}")
        
        # Add summary footer
        summary.append("\n=== Test Summary ===")
        read_success = sum(1 for _, d in results["readability_test"].items() if d['readable'])
        read_total = len(results["readability_test"])
        write_success = sum(1 for _, r in results["write_test"].items() if r.get('success', r) if r)
        write_total = len(results["write_test"])
        
        summary.append(f"Read Tests:  {read_success}/{read_total} successful")
        summary.append(f"Write Tests: {write_success}/{write_total} successful")
        summary.append(f"Overall:     {read_success + write_success}/{read_total + write_total} successful")
        
        return "\n".join(summary)
