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
        # Log active network configuration at the moment helper is set
        try:
            info = self.camera_helper.get_network_info()
            self.logger.info(
                f"Active network configuration → IP {info.get('ip_address')} / {info.get('subnet_mask')} / {info.get('gateway')} (mode={info.get('mode')})"
            )
        except Exception:
            pass

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

    def snap_image(self):
        """Capture a single image from the camera"""
        try:
            self.logger.info("Capturing single image")
            
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Capture image
            frame = self.get_current_frame()
            if frame is not None:
                self.logger.info("Image captured successfully")
                self.view.log_message("Image captured successfully", "SUCCESS")
                
                # Save image to file
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"snap_image_{timestamp}.png"
                cv2.imwrite(filename, frame)
                self.logger.info(f"Image saved to {filename}")
                self.view.log_message(f"Image saved to {filename}", "SUCCESS")
                
                return True
            else:
                self.logger.warning("Failed to capture image")
                self.view.log_message("Failed to capture image", "WARNING")
                return False
                
        except Exception as e:
            error_msg = f"Image capture failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")
            return False

    def detect_usb_camera(self):
        """Detect and connect to a USB camera"""
        try:
            # If camera is already connected/open, avoid re-detection that can cause exclusive-open errors
            try:
                if self.camera_helper and self.camera_helper.camera and self.camera_helper.camera.IsOpen():
                    self.logger.info("Camera already connected; skipping USB detection")
                    self.view.update_camera_detection_status("success", "Camera already connected. You can proceed to tests.")
                    self.view.log_message("Camera already connected; skipping USB detection", "INFO")
                    return
            except Exception:
                # If any attribute missing or IsOpen raises, continue with detection
                pass

            self.logger.info("Starting USB camera discovery...")
            self.view.update_camera_detection_status("detecting", "Searching for USB cameras...", show_progress=True, progress_value=25)
            
            if self.camera_helper is None:
                raise RuntimeError("Camera helper not initialized")
                
            # Get list of available cameras
            self.view.update_camera_detection_status("detecting", "Enumerating available cameras...", show_progress=True, progress_value=50)
            cameras = self.camera_helper.get_usb_cameras()
            
            if not cameras:
                self.view.update_camera_detection_status("warning", "No USB cameras found. Please check your connection and try again.")
                self.view.log_message("No USB cameras found", "WARNING")
                return
                
            self.view.update_camera_detection_status("detecting", "Selecting camera...", show_progress=True, progress_value=75)
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
                self.view.update_camera_detection_status("detecting", "Connecting to camera...", show_progress=True, progress_value=90)
                self.camera = self.camera_helper.connect_camera(selected_camera)
                if self.camera:
                    self.view.update_camera_detection_status("success", f"Successfully connected to {selected_camera.get('name', 'Unknown')}")
                    self.view.update_camera_summary(selected_camera)
                    self.view.log_message(
                        f"Successfully connected to camera: {selected_camera.get('name', 'Unknown')} "
                        f"(SN: {selected_camera.get('id', 'Unknown')})",
                        "SUCCESS"
                    )
                    # Update camera details
                    self.update_camera_details(selected_camera)
                else:
                    self.view.update_camera_detection_status("error", "Failed to connect to camera. Please check your connection and try again.")
                    self.view.log_message("Failed to connect to camera", "ERROR")
            else:
                self.view.update_camera_detection_status("warning", "No camera selected. Please try again.")
            
        except Exception as e:
            self.logger.error(f"USB camera detection error: {str(e)}")
            self.view.update_camera_detection_status("error", f"Error detecting USB camera: {str(e)}")
            self.view.log_message(f"Error detecting USB camera: {str(e)}", "ERROR")

    def detect_gige_camera(self, use_dhcp, ip_settings):
        """Detect and connect to GigE camera"""
        try:
            self.logger.info("Starting GigE camera detection")
            self.view.update_camera_detection_status("detecting", "Searching for GigE cameras...", show_progress=True, progress_value=25)
            
            if use_dhcp:
                self.logger.info("Using DHCP for camera detection")
                self.view.update_camera_detection_status("detecting", "Using DHCP to detect cameras...", show_progress=True, progress_value=50)
                # Use DHCP to find camera
                cameras = self.camera_helper.enumerate_cameras()
                if cameras:
                    # Connect to the first available camera
                    camera = cameras[0]
                    self.logger.info(f"Found camera: {camera}")
                    self.view.update_camera_detection_status("detecting", "Connecting to camera...", show_progress=True, progress_value=75)
                    # Pass the discovered camera info to the connector
                    self.camera = self.camera_helper.connect_camera(camera)
                    self.view.update_camera_detection_status("success", f"GigE camera connected via DHCP: {camera.get('name', 'Unknown')}")
                    self.view.update_camera_summary(camera)
                    self.view.log_message("GigE camera connected via DHCP", "SUCCESS")
                    # Update camera details
                    self.update_camera_details(camera)
                    return True
                else:
                    self.logger.warning("No GigE cameras found via DHCP")
                    self.view.update_camera_detection_status("warning", "No GigE cameras found via DHCP. Please check your network connection.")
                    self.view.log_message("No GigE cameras found via DHCP", "WARNING")
                    return False
            else:
                self.logger.info(f"Using manual IP settings: {ip_settings}")
                self.view.update_camera_detection_status("detecting", "Connecting with manual IP settings...", show_progress=True, progress_value=50)
                # Use manual IP settings
                if ip_settings and 'ip_address' in ip_settings:
                    try:
                        # Allow helper to accept IP-based connection (simulation will always succeed)
                        self.camera = self.camera_helper.connect_camera(ip_settings['ip_address'])
                        self.view.update_camera_detection_status("success", f"GigE camera connected to {ip_settings['ip_address']}")
                        # Create a dummy camera info for display
                        camera_info = {
                            'name': 'GigE Camera',
                            'id': 'Manual IP',
                            'interface': 'GigE',
                            'ip_address': ip_settings['ip_address']
                        }
                        self.view.update_camera_summary(camera_info)
                        self.view.log_message(f"GigE camera connected to {ip_settings['ip_address']}", "SUCCESS")
                        return True
                    except Exception as e:
                        error_msg = f"Failed to connect to camera at {ip_settings['ip_address']}: {str(e)}"
                        self.logger.error(error_msg)
                        self.view.update_camera_detection_status("error", error_msg)
                        self.view.log_message(error_msg, "ERROR")
                        return False
                else:
                    error_msg = "Invalid IP settings provided"
                    self.logger.error(error_msg)
                    self.view.update_camera_detection_status("error", error_msg)
                    self.view.log_message(error_msg, "ERROR")
                    return False
                    
        except Exception as e:
            error_msg = f"GigE camera detection failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.update_camera_detection_status("error", error_msg)
            self.view.log_message(error_msg, "ERROR")
            return False

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

    def run_image_acquisition_test(self):
        """Run image acquisition test"""
        try:
            from tests.test_imageAcq import TestImageAcquisition
            
            self.logger.info("Starting image acquisition test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestImageAcquisition()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_continuous_acquisition()
                
                # Log results
                self.logger.info(f"Image acquisition test completed: {results}")
                
                # Update view with results
                summary = self._format_image_acquisition_results(results)
                self.view.update_test_results("Image Acquisition Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Image acquisition test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize image acquisition test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_image_quality_tests(self):
        """Run image quality tests"""
        try:
            from tests.test_imgQuality import TestImageQuality

            self.logger.info("Starting image quality tests")

            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            test = TestImageQuality()
            test.setup(self.camera_helper)

            results = test.test_image_quality()
            if not results.get("success"):
                raise RuntimeError(results.get("error", "Image quality test failed"))

            # Format results for display
            lines = ["Image Quality Metrics:"]
            metrics = results.get("results", {})
            for k, v in metrics.items():
                val = v.get("value")
                passed = v.get("pass")
                thresh = v.get("threshold")
                if thresh is not None:
                    lines.append(f"- {k}: {val:.4g} (pass={passed}, threshold={thresh})")
                else:
                    try:
                        lines.append(f"- {k}: {val:.4g} (pass={passed})")
                    except Exception:
                        lines.append(f"- {k}: {val} (pass={passed})")

            summary = "\n".join(lines)
            self.view.update_test_results("Image Quality", summary)
            return True

        except Exception as e:
            error_msg = f"Failed to run image quality tests: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_max_fps_test(self):
        """Run max FPS test"""
        try:
            from tests.test_maxFPS import TestMaxFPS
            
            self.logger.info("Starting max FPS test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestMaxFPS()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_maximum_fps()
                
                # Log results
                self.logger.info(f"Max FPS test completed: {results}")
                
                # Update view with results
                summary = self._format_max_fps_results(results)
                self.view.update_test_results("Max FPS Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Max FPS test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize max FPS test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_roi_test(self):
        """Run ROI test (functional version, no TestROI class).

        Procedure:
          1. Determine maximum resolution (via GenICamHelper if possible, else current Width/Height).
          2. Exercise a sequence of ROI sizes: full, half, quarter, third.
          3. For each ROI, set it, grab one frame, validate frame shape matches expectation.
          4. Restore full resolution at end.
        """
        try:
            self.logger.info("Starting ROI test (functional)")

            # Preconditions
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            if not self.genicam_helper:
                raise RuntimeError("GenICam helper not available")

            cam = self.camera_helper.camera

            # Ensure helper has the camera attached
            try:
                if getattr(self.genicam_helper, 'camera', None) is None:
                    self.genicam_helper.set_camera(cam)
            except Exception:
                pass

            # Helper to grab a single frame
            def _grab_one():
                grab = cam.GrabOne(500)
                if not grab or not grab.GrabSucceeded():
                    raise RuntimeError("Failed to grab frame")
                arr = grab.Array
                grab.Release()
                return arr

            # Determine full resolution
            try:
                max_w, max_h = self.genicam_helper.get_max_resolution()
            except Exception:
                # Fallback: read current ROI (Width/Height) if API available
                try:
                    max_w = int(cam.Width.GetValue())
                    max_h = int(cam.Height.GetValue())
                except Exception:
                    frame = _grab_one()
                    max_h, max_w = frame.shape[0], frame.shape[1]

            variants = []
            variants.append(("Full", max_w, max_h))
            variants.append(("Half", max_w // 2, max_h // 2))
            variants.append(("Quarter", max_w // 4, max_h // 4))
            variants.append(("Third", max_w // 3, max_h // 3))

            results_lines = [f"Detected max resolution: {max_w}x{max_h}"]

            # Run through variants
            for label, w, h in variants:
                try:
                    self.genicam_helper.set_roi(w, h)
                    frame = _grab_one()
                    fh, fw = frame.shape[0], frame.shape[1]
                    ok = (fw == w and fh == h)
                    results_lines.append(f"{label} ROI -> set {w}x{h}, got {fw}x{fh} : {'OK' if ok else 'MISMATCH'}")
                    if not ok:
                        raise AssertionError(f"ROI mismatch for {label}: expected {w}x{h}, got {fw}x{fh}")
                except Exception as e_variant:
                    msg = f"{label} ROI failed: {e_variant}"
                    results_lines.append(msg)
                    self.logger.warning(msg)
                    # Continue to next variant

            # Restore full
            try:
                self.genicam_helper.set_roi(max_w, max_h)
            except Exception:
                pass

            summary = "ROI Test Results:\n" + "\n".join(results_lines)
            self.view.update_test_results("ROI Test", summary)
            self.logger.info("ROI test completed")
            return True

        except Exception as e:
            error_msg = f"ROI test failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_camera_calibration(self):
        """Run camera calibration"""
        try:
            from funct.funct_calibCam import CameraCalibration
            
            self.logger.info("Starting camera calibration")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize calibration class
            calibration = CameraCalibration()
            calibration.set_camera(self.camera_helper)
            
            # Run calibration and get results
            try:
                # Capture calibration images
                images = []
                for i in range(5):
                    image = calibration.capture_calibration_image()
                    images.append(image)
                    self.logger.info(f"Captured calibration image {i+1}")
                
                # Perform calibration
                success = calibration.calibrate_camera(images)
                
                if success:
                    self.logger.info("Camera calibration completed successfully")
                    self.view.update_test_results("Camera Calibration", "Calibration completed successfully!")
                else:
                    self.logger.warning("Camera calibration failed")
                    self.view.update_test_results("Camera Calibration", "Calibration failed!")
                
                return success
                
            except Exception as e:
                error_msg = f"Camera calibration execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize camera calibration: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_edge_detection(self):
        """Run edge detection"""
        try:
            from funct.funct_edgeDetection import EdgeDetection
            
            self.logger.info("Starting edge detection")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize edge detection class
            edge_detector = EdgeDetection()
            edge_detector.set_camera(self.camera_helper)
            
            # Run edge detection and get results
            try:
                edges = edge_detector.capture_and_detect()
                percentage = edge_detector.get_edge_percentage(edges)
                
                self.logger.info(f"Edge detection completed. Edge percentage: {percentage:.2f}%")
                
                # Update view with results
                summary = f"Edge Detection Results:\nEdge percentage: {percentage:.2f}%"
                self.view.update_test_results("Edge Detection", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Edge detection execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize edge detection: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_blur_detection(self):
        """Run blur detection"""
        try:
            from funct.funct_blurDetection import BlurDetection
            
            self.logger.info("Starting blur detection")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize blur detection class
            blur_detector = BlurDetection()
            blur_detector.set_camera(self.camera_helper)
            
            # Run blur detection and get results
            try:
                is_blurry = blur_detector.test_image_blur()
                
                result = "Image is NOT blurry" if not is_blurry else "Image IS blurry"
                self.logger.info(f"Blur detection completed: {result}")
                
                # Update view with results
                summary = f"Blur Detection Results:\n{result}"
                self.view.update_test_results("Blur Detection", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Blur detection execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize blur detection: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_multicam_test(self):
        """Run multi-camera test"""
        try:
            from tests.test_multicam import TestMultiCam
            
            self.logger.info("Starting multi-camera test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestMultiCam()
            test.setup([self.camera_helper])  # Single camera for now
            
            # Run tests and get results
            try:
                results = test.test_synchronization()
                
                # Log results
                self.logger.info(f"Multi-camera test completed: {results}")
                
                # Update view with results
                summary = self._format_multicam_results(results)
                self.view.update_test_results("Multi-Camera Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Multi-camera test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize multi-camera test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_power_gige_test(self):
        """Run power GigE test"""
        try:
            from tests.test_powerGigE import TestPowerGigE
            
            self.logger.info("Starting power GigE test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestPowerGigE()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_power_consumption()
                
                # Log results
                self.logger.info(f"Power GigE test completed: {results}")
                
                # Update view with results
                summary = self._format_power_gige_results(results)
                self.view.update_test_results("Power GigE Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Power GigE test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize power GigE test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_power_usb_test(self):
        """Run power USB test"""
        try:
            from tests.test_powerUSB import TestPowerUSB
            
            self.logger.info("Starting power USB test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = TestPowerUSB()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_power_consumption()
                
                # Log results
                self.logger.info(f"Power USB test completed: {results}")
                
                # Update view with results
                summary = self._format_power_usb_results(results)
                self.view.update_test_results("Power USB Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Power USB test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize power USB test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_io_test(self):
        """Run IO test (adapted to new functional test implementation)"""
        from lib.genicam_helper import GenICamHelper
        try:
            self.logger.info("Starting IO test (functional mode)")

            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            gh = GenICamHelper()
            gh.set_camera(self.camera_helper.camera)

            def _io_line_test(line_number):
                try:
                    gh.set_line_mode(line_number, "input")
                    input_state = gh.get_line_state(line_number)

                    gh.set_line_mode(line_number, "output")
                    gh.set_line_state(line_number, True)
                    high_state = gh.get_line_state(line_number)

                    gh.set_line_state(line_number, False)
                    low_state = gh.get_line_state(line_number)

                    return {
                        "input_test": input_state is not None,
                        "output_high": high_state is True,
                        "output_low": low_state is False,
                        "overall": True
                    }
                except Exception as e:
                    return {
                        "input_test": False,
                        "output_high": False,
                        "output_low": False,
                        "overall": False,
                        "error": str(e)
                    }

            def _user_output_test():
                try:
                    gh.set_user_output(1, True)
                    high_state = gh.get_user_output(1)
                    gh.set_user_output(1, False)
                    low_state = gh.get_user_output(1)
                    return {"set_high": high_state is True, "set_low": low_state is False, "overall": True}
                except Exception as e:
                    return {"set_high": False, "set_low": False, "overall": False, "error": str(e)}

            results = {
                "Line1": _io_line_test(1),
                "Line2": _io_line_test(2),
                "UserOutput1": _user_output_test()
            }

            self.logger.info(f"IO test completed: {results}")
            summary = self._format_io_results(results)
            self.view.update_test_results("IO Test", summary)
            return True
        except Exception as e:
            error_msg = f"IO test failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_power_cycle_test(self):
        """Run power cycle test"""
        try:
            from funct.funct_powercycle import PowerCycleTest
            
            self.logger.info("Starting power cycle test")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Initialize test class
            test = PowerCycleTest()
            test.setup(self.camera_helper)
            
            # Run tests and get results
            try:
                results = test.test_power_cycle()
                
                # Log results
                self.logger.info(f"Power cycle test completed: {results}")
                
                # Update view with results
                summary = self._format_power_cycle_results(results)
                self.view.update_test_results("Power Cycle Test", summary)
                
                return True
                
            except Exception as e:
                error_msg = f"Power cycle test execution failed: {str(e)}"
                self.logger.error(error_msg)
                self.view.show_error("Test Error", error_msg)
                return False
        except Exception as e:
            error_msg = f"Failed to initialize power cycle test: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_init_cam_test(self):
        """Run camera initialization test (adapted to functional pytest test)"""
        import time
        try:
            self.logger.info("Starting camera initialization test (functional mode)")
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            start = time.time()
            cam = self.camera_helper.camera
            if not cam.IsOpen():
                raise RuntimeError("Camera not open")

            grab = cam.GrabOne(500)
            ok = grab and grab.GrabSucceeded()
            if grab:
                grab.Release()
            elapsed = time.time() - start
            if not ok:
                raise RuntimeError("Failed to grab test frame during initialization")
            if elapsed < 0:
                raise RuntimeError("Invalid timing captured")

            results = {"success": True, "elapsed": elapsed}
            self.logger.info(f"Camera initialization test completed: {results}")
            summary = self._format_init_cam_results(results)
            self.view.update_test_results("Camera Initialization Test", summary)
            return True
        except Exception as e:
            error_msg = f"Camera initialization test failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error("Test Error", error_msg)
            return False

    def run_performance_tests(self):
        """Run performance tests"""
        try:
            self.logger.info("Starting performance tests")
            
            # Verify camera is connected
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # Run multiple performance tests
            results = {}
            
            # Test 1: Max FPS
            try:
                from tests.test_maxFPS import TestMaxFPS
                test = TestMaxFPS()
                test.setup(self.camera_helper)
                results['max_fps'] = test.test_maximum_fps()
                self.logger.info("Max FPS test completed")
            except Exception as e:
                self.logger.warning(f"Max FPS test failed: {str(e)}")
                results['max_fps'] = {'error': str(e)}
            
            # Test 2: Image Quality
            try:
                from tests.test_imgQuality import TestImageQuality
                test = TestImageQuality()
                test.setup(self.camera_helper)
                results['image_quality'] = test.test_image_quality()
                self.logger.info("Image quality test completed")
            except Exception as e:
                self.logger.warning(f"Image quality test failed: {str(e)}")
                results['image_quality'] = {'error': str(e)}
            
            # Test 3: Long Run
            try:
                from funct.funct_longRun import LongRunTest
                test = LongRunTest()
                test.set_camera(self.camera_helper)
                test.set_duration(10)  # Short test for performance
                results['long_run'] = test.start_test()
                self.logger.info("Long run test completed")
            except Exception as e:
                self.logger.warning(f"Long run test failed: {str(e)}")
                results['long_run'] = {'error': str(e)}
            
            # Log overall results
            self.logger.info(f"Performance tests completed: {results}")
            
            # Update view with results
            summary = self._format_performance_results(results)
            self.view.update_test_results("Performance Tests", summary)
            
            return True
            
        except Exception as e:
            error_msg = f"Performance tests failed: {str(e)}"
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
        # Count successful write tests robustly across different value types
        write_success = 0
        for _, r in results["write_test"].items():
            try:
                if isinstance(r, dict):
                    if r.get('success', False):
                        write_success += 1
                elif isinstance(r, bool):
                    if r:
                        write_success += 1
                else:
                    # Treat "Not Supported" or other non-bool as not successful but do not crash
                    pass
            except Exception:
                pass
        write_total = len(results["write_test"])
        
        summary.append(f"Read Tests:  {read_success}/{read_total} successful")
        summary.append(f"Write Tests: {write_success}/{write_total} successful")
        summary.append(f"Overall:     {read_success + write_success}/{read_total + write_total} successful")
        
        return "\n".join(summary)

    def _format_image_acquisition_results(self, results):
        """Format image acquisition test results"""
        summary = []
        summary.append("=== Image Acquisition Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Total Frames: {results.get('total_frames', 'N/A')}")
            summary.append(f"Successful Frames: {results.get('successful_frames', 'N/A')}")
            summary.append(f"Failed Frames: {results.get('failed_frames', 'N/A')}")
            summary.append(f"Success Rate: {results.get('success_rate', 'N/A'):.2f}%")
            summary.append(f"Average FPS: {results.get('average_fps', 'N/A'):.2f}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_max_fps_results(self, results):
        """Format max FPS test results"""
        summary = []
        summary.append("=== Max FPS Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            for test_name, test_results in results.items():
                if isinstance(test_results, dict):
                    summary.append(f"\n{test_name}:")
                    summary.append(f"  FPS Achieved: {test_results.get('fps_achieved', 'N/A'):.2f}")
                    summary.append(f"  Frames Captured: {test_results.get('frames_captured', 'N/A')}")
                    summary.append(f"  Duration: {test_results.get('duration', 'N/A'):.2f}s")
                    summary.append(f"  Exposure Time: {test_results.get('exposure_time', 'N/A')}μs")
                else:
                    summary.append(f"{test_name}: {test_results}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_roi_results(self, results):
        """Format ROI test results"""
        summary = []
        summary.append("=== ROI Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            for test_name, test_results in results.items():
                if isinstance(test_results, dict):
                    summary.append(f"\n{test_name}:")
                    summary.append(f"  Success: {test_results.get('success', 'N/A')}")
                    summary.append(f"  Width: {test_results.get('width', 'N/A')}")
                    summary.append(f"  Height: {test_results.get('height', 'N/A')}")
                    summary.append(f"  Matches Expected: {test_results.get('matches_expected', 'N/A')}")
                else:
                    summary.append(f"{test_name}: {test_results}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_multicam_results(self, results):
        """Format multi-camera test results"""
        summary = []
        summary.append("=== Multi-Camera Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Overall Success: {results.get('overall_success', 'N/A')}")
            summary.append(f"Frame Counts: {results.get('frame_counts', 'N/A')}")
            summary.append(f"FPS Values: {results.get('fps_values', 'N/A')}")
            
            sync_accuracy = results.get('sync_accuracy', {})
            if sync_accuracy:
                summary.append(f"Max Sync Error: {sync_accuracy.get('max_error', 'N/A'):.2f}μs")
                summary.append(f"Avg Sync Error: {sync_accuracy.get('avg_error', 'N/A'):.2f}μs")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_power_gige_results(self, results):
        """Format power GigE test results"""
        summary = []
        summary.append("=== Power GigE Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Success: {results.get('success', 'N/A')}")
            summary.append(f"Test Duration: {results.get('test_duration', 'N/A'):.2f}s")
            summary.append(f"Average Power: {results.get('average_power', 'N/A'):.2f}W")
            summary.append(f"Peak Power: {results.get('peak_power', 'N/A'):.2f}W")
            
            if 'error' in results:
                summary.append(f"Error: {results['error']}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_power_usb_results(self, results):
        """Format power USB test results"""
        summary = []
        summary.append("=== Power USB Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Success: {results.get('success', 'N/A')}")
            summary.append(f"Test Duration: {results.get('test_duration', 'N/A'):.2f}s")
            summary.append(f"Average Current: {results.get('average_current', 'N/A'):.2f}mA")
            summary.append(f"Peak Current: {results.get('peak_current', 'N/A'):.2f}mA")
            summary.append(f"Average Power: {results.get('average_power', 'N/A'):.2f}W")
            summary.append(f"Peak Power: {results.get('peak_power', 'N/A'):.2f}W")
            
            if 'error' in results:
                summary.append(f"Error: {results['error']}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_io_results(self, results):
        """Format IO test results"""
        summary = []
        summary.append("=== IO Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            for test_name, test_results in results.items():
                if isinstance(test_results, dict):
                    summary.append(f"\n{test_name}:")
                    summary.append(f"  Input Test: {test_results.get('input_test', 'N/A')}")
                    summary.append(f"  Output High: {test_results.get('output_high', 'N/A')}")
                    summary.append(f"  Output Low: {test_results.get('output_low', 'N/A')}")
                    summary.append(f"  Overall: {test_results.get('overall', 'N/A')}")
                    
                    if 'error' in test_results:
                        summary.append(f"  Error: {test_results['error']}")
                else:
                    summary.append(f"{test_name}: {test_results}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_power_cycle_results(self, results):
        """Format power cycle test results"""
        summary = []
        summary.append("=== Power Cycle Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Total Cycles: {results.get('total_cycles', 'N/A')}")
            summary.append(f"Successful Cycles: {results.get('successful_cycles', 'N/A')}")
            summary.append(f"Failed Cycles: {results.get('failed_cycles', 'N/A')}")
            summary.append(f"Success Rate: {results.get('success_rate', 'N/A'):.2f}%")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_init_cam_results(self, results):
        """Format camera initialization test results"""
        summary = []
        summary.append("=== Camera Initialization Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            summary.append(f"Success: {results.get('success', 'N/A')}")
            summary.append(f"Error: {results.get('error', 'N/A')}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)

    def _format_performance_results(self, results):
        """Format performance test results"""
        summary = []
        summary.append("=== Performance Test Results ===")
        summary.append(f"Test Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if isinstance(results, dict):
            for test_name, test_results in results.items():
                summary.append(f"\n{test_name.upper().replace('_', ' ')}:")
                if isinstance(test_results, dict):
                    if 'error' in test_results:
                        summary.append(f"  Status: FAILED")
                        summary.append(f"  Error: {test_results['error']}")
                    else:
                        summary.append(f"  Status: COMPLETED")
                        for key, value in test_results.items():
                            if key != 'error':
                                summary.append(f"  {key.replace('_', ' ').title()}: {value}")
                else:
                    summary.append(f"  Results: {test_results}")
        else:
            summary.append(f"Results: {results}")
        
        return "\n".join(summary)
