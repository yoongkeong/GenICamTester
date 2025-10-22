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
        # Store last explicitly captured frame for GUI preview/save
        self.last_captured_frame = None
        self._init_logging()
        # Cooperative cancellation flag for long-running presenter-driven tests
        self._cancel_requested = False

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
        """Capture a single image from the camera and store it for preview/save."""
        try:
            self.logger.info("Capturing single image")

            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            cam = self.camera_helper.camera
            frame = None

            # Try direct single-frame grab using GrabOne (works without live view)
            try:
                if hasattr(cam, 'GrabOne'):
                    self.logger.debug("Attempting GrabOne() for single image capture")
                    grab = cam.GrabOne(1000)
                    if grab and hasattr(grab, 'GrabSucceeded') and grab.GrabSucceeded():
                        frame = grab.Array
                    try:
                        if grab is not None:
                            grab.Release()
                    except Exception:
                        pass
            except Exception as e:
                self.logger.debug(f"GrabOne failed: {e}")

            # Fallback: try helper's get_frame
            if frame is None:
                try:
                    self.logger.debug("Falling back to camera_helper.get_frame()")
                    frame = self.camera_helper.get_frame(self.camera)
                except Exception as e:
                    self.logger.debug(f"camera_helper.get_frame failed: {e}")

            # If still no frame, attempt a software trigger (GenICam) if supported
            if frame is None and getattr(self, 'genicam_helper', None) is not None:
                try:
                    gh = self.genicam_helper
                    # Ensure helper has camera attached
                    try:
                        if getattr(gh, 'camera', None) is None:
                            gh.set_camera(self.camera_helper.camera)
                    except Exception:
                        pass

                    # Configure trigger to software and execute
                    if gh.has_node('TriggerMode') and gh.has_node('TriggerSource'):
                        try:
                            gh.set_node_value('TriggerMode', 'On')
                            gh.set_node_value('TriggerSource', 'Software')
                        except Exception:
                            # ignore failures to set
                            pass

                    # Execute software trigger command if available
                    trig_node = gh._get_node('TriggerSoftware') if hasattr(gh, '_get_node') else None
                    executed = False
                    if trig_node is not None:
                        for cmd in ('Execute', 'ExecuteCommand', 'Run'):
                            try:
                                if hasattr(trig_node, cmd):
                                    getattr(trig_node, cmd)()
                                    executed = True
                                    break
                            except Exception:
                                continue

                    # After triggering, try to GrabOne/RetrieveResult
                    if executed:
                        try:
                            if hasattr(cam, 'RetrieveResult'):
                                grab = cam.RetrieveResult(1000)
                                if grab and hasattr(grab, 'GrabSucceeded') and grab.GrabSucceeded():
                                    frame = grab.Array
                                try:
                                    if grab is not None:
                                        grab.Release()
                                except Exception:
                                    pass
                        except Exception:
                            try:
                                grab = cam.GrabOne(1000)
                                if grab and hasattr(grab, 'GrabSucceeded') and grab.GrabSucceeded():
                                    frame = grab.Array
                                try:
                                    if grab is not None:
                                        grab.Release()
                                except Exception:
                                    pass
                            except Exception:
                                pass

                except Exception as e:
                    self.logger.debug(f"Software trigger attempt failed: {e}")

            if frame is not None:
                self.logger.info("Image captured successfully")
                self.view.log_message("Image captured successfully", "SUCCESS")
                # Store for preview/save
                self.last_captured_frame = frame
                # Instruct view to display preview in the live view area
                try:
                    if hasattr(self.view, 'show_captured_image'):
                        self.view.show_captured_image(frame)
                except Exception:
                    pass

                return frame
            else:
                self.logger.warning("Failed to capture image")
                self.view.log_message("Failed to capture image", "WARNING")
                return None

        except Exception as e:
            error_msg = f"Image capture failed: {str(e)}"
            self.logger.error(error_msg)
            self.view.log_message(error_msg, "ERROR")
            return None

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
        """Run Image Quality test with operator-guided stages and consolidated report.

        - Keeps right-panel Live View (handled by dialog); uses logs for guidance.
        - Computes EMVA-aligned basic metrics (best-effort) and extended analyses.
        - Writes a single test_result.txt in result/image_quality/<RunID>/.
        - After compute, prompts user (GUI thread) to optionally save images/plots to a folder.
        - No JSON or multiple artifact files are created automatically.
        """
        import os, time, math, platform, threading
        import numpy as np
        import cv2
        from configparser import ConfigParser

        TEST_NAME = "ImageQuality"

        def log(level: str, msg: str):
            try:
                self.view.log_message(msg, level)
            except Exception:
                pass
            lvl = (level or "INFO").upper()
            if lvl == "ERROR":
                self.logger.error(msg)
            elif lvl in ("WARN", "WARNING"):
                self.logger.warning(msg)
            elif lvl == "SUCCESS":
                self.logger.info(msg)
            else:
                self.logger.info(msg)

        def stage(pct: int, text: str):
            log('INFO', f"[{pct}%] {text}")

        def check_cancel() -> bool:
            return bool(getattr(self, '_cancel_requested', False))

        def show_blocking_prompt(title: str, body: str) -> bool:
            """Scene prompt helper supporting both UI-thread sync and worker-thread async flows.
            - UI thread: build dialog and exec_ synchronously (modal loop).
            - Worker thread: schedule non-blocking open() with finished callback and wait via Event.
            Acquisition is paused before showing; resumes only if it was running and decision=Continue.
            Single-instance guard, watchdog, global-cancel, parenting, centering, focus, and diagnostics preserved.
            """
            from PyQt5.QtWidgets import QMessageBox, QWidget, QApplication
            from PyQt5.QtCore import Qt, QThread

            # Determine current thread context and log mode
            app = QApplication.instance()
            on_ui_thread = bool(app) and (QThread.currentThread() == app.thread())
            log('INFO', f"prompt_mode={'UI-sync' if on_ui_thread else 'worker-async'} title={title}")

            # Lazy-init guard fields on presenter
            if not hasattr(self, '_prompt_in_progress'):
                self._prompt_in_progress = False
            if not hasattr(self, '_current_prompt_event'):
                self._current_prompt_event = None
            if not hasattr(self, '_current_prompt_result'):
                self._current_prompt_result = False
            if not hasattr(self, '_scene_gate_active'):
                self._scene_gate_active = False

            # If a prompt is already open, ignore re-entry but wait for it to finish
            if self._prompt_in_progress and self._current_prompt_event is not None:
                log('INFO', 'ImageQuality: Prompt already open; ignoring duplicate request')
                self._current_prompt_event.wait()
                return bool(self._current_prompt_result)

            # Pause acquisition safely and flush pending buffers
            was_grabbing = False
            try:
                if self.camera_helper and self.camera_helper.camera and self.camera_helper.camera.IsGrabbing():
                    log('INFO', 'ImageQuality: Pausing acquisition for scene prompt')
                    self.camera_helper.camera.StopGrabbing()
                    was_grabbing = True
                    # Best-effort flush pending results
                    try:
                        while True:
                            try:
                                gr = self.camera_helper.camera.RetrieveResult(0)
                                if gr and hasattr(gr, 'GrabSucceeded') and gr.GrabSucceeded():
                                    try:
                                        gr.Release()
                                    except Exception:
                                        pass
                                else:
                                    break
                            except Exception:
                                break
                    except Exception:
                        pass
            except Exception:
                pass
            # Gate further acquisition restarts until prompt closes
            self._scene_gate_active = True

            # Helper: resolve best parent dialog
            def _resolve_parent():
                try:
                    parent = None
                    try:
                        active_modal = QApplication.activeModalWidget()
                        if active_modal and hasattr(active_modal, 'windowTitle'):
                            wt = str(active_modal.windowTitle())
                            if wt == TEST_NAME or (TEST_NAME in wt):
                                parent = active_modal
                    except Exception:
                        parent = None
                    if parent is None:
                        try:
                            for w in QApplication.topLevelWidgets():
                                try:
                                    if hasattr(w, 'windowTitle') and hasattr(w, 'isVisible') and w.isVisible():
                                        wt = str(w.windowTitle())
                                        if wt == TEST_NAME or (TEST_NAME in wt):
                                            parent = w
                                            break
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    if parent is None:
                        try:
                            return self.view if isinstance(self.view, QWidget) else QApplication.activeWindow()
                        except Exception:
                            return None
                    return parent
                except Exception:
                    return None

            # Helper: build and configure the dialog
            def _build_box(parent):
                box = QMessageBox(parent)
                box.setWindowTitle(title)
                box.setText(body)
                box.setIcon(QMessageBox.Information)
                try:
                    box.setModal(True)
                    box.setWindowModality(Qt.ApplicationModal)
                    box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
                except Exception:
                    pass
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
                try:
                    box.button(QMessageBox.Yes).setText('Continue')
                    box.button(QMessageBox.Cancel).setText('Cancel')
                    yes_btn = box.button(QMessageBox.Yes)
                    try:
                        yes_btn.setDefault(True); yes_btn.setAutoDefault(True); yes_btn.setFocus(Qt.OtherFocusReason)
                    except Exception:
                        pass
                except Exception:
                    pass
                return box

            # Helper: diagnostics
            def _diag_before(parent):
                try:
                    p_title = parent.windowTitle() if (parent is not None and hasattr(parent, 'windowTitle')) else 'N/A'
                    p_cls = parent.__class__.__name__ if parent is not None else 'None'
                    try:
                        g = parent.geometry() if parent is not None else None
                        gtxt = f"x={g.x()} y={g.y()} w={g.width()} h={g.height()}" if g is not None else 'N/A'
                    except Exception:
                        gtxt = 'N/A'
                    log('INFO', f"diag: prompt={'Dark' if 'Dark' in title else 'Light'} parent=<{p_cls},{p_title}> geom=({gtxt}) visible=0 active=0 on_ui_thread={1 if on_ui_thread else 0}")
                except Exception:
                    pass

            def _position_and_raise(box, parent):
                try:
                    box.adjustSize()
                    if parent is not None:
                        try:
                            pg = parent.frameGeometry(); sz = box.sizeHint()
                            x = int(pg.center().x() - sz.width() / 2); y = int(pg.center().y() - sz.height() / 2)
                            box.move(x, y)
                        except Exception:
                            pass
                    try:
                        box.raise_(); box.activateWindow()
                    except Exception:
                        pass
                except Exception:
                    pass

            # UI-thread synchronous path
            if on_ui_thread:
                parent = _resolve_parent()
                box = _build_box(parent)
                _diag_before(parent)
                # watchdog and cancel polling
                watchdog = QTimer(box); watchdog.setSingleShot(True); watchdog.setInterval(120000)
                def _on_watchdog():
                    try: log('WARNING', 'ImageQuality: Scene prompt timed out (no response in 120s)')
                    except Exception: pass
                    try: box.reject()
                    except Exception: pass
                try:
                    watchdog.timeout.connect(_on_watchdog); watchdog.start()
                except Exception:
                    pass
                cancel_timer = QTimer(box); cancel_timer.setSingleShot(False); cancel_timer.setInterval(400)
                def _poll_cancel():
                    try:
                        if bool(getattr(self, '_cancel_requested', False)):
                            try: log('INFO', 'ImageQuality: Global cancel while prompt — stopping test')
                            except Exception: pass
                            try: box.reject()
                            except Exception: pass
                    except Exception:
                        pass
                try:
                    cancel_timer.timeout.connect(_poll_cancel); cancel_timer.start()
                except Exception:
                    pass
                # Disable parent and keep strong ref
                try:
                    if parent is not None: parent.setEnabled(False)
                except Exception:
                    pass
                try:
                    self._current_prompt_widget = box
                except Exception:
                    pass
                _position_and_raise(box, parent)
                ret = box.exec_()
                # Post diagnostics
                try:
                    vis = 1 if box.isVisible() else 0
                    act = 1 if (box.isActiveWindow() if hasattr(box, 'isActiveWindow') else False) else 0
                    log('INFO', f"diag: prompt={'Dark' if 'Dark' in title else 'Light'} parent=<inline> geom=(x={box.x()} y={box.y()} w={box.width()} h={box.height()}) visible={vis} active={act} on_ui_thread=1")
                except Exception:
                    pass
                # Cleanup and decision
                try: watchdog.stop()
                except Exception: pass
                try: cancel_timer.stop()
                except Exception: pass
                self._current_prompt_result = (ret == QMessageBox.Yes)
                try:
                    if parent is not None: parent.setEnabled(True)
                except Exception:
                    pass
                if self._current_prompt_result:
                    if was_grabbing:
                        try:
                            log('INFO', 'ImageQuality: Resuming acquisition after scene prompt (decision=Continue)')
                            self.camera_helper.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                        except Exception:
                            pass
                else:
                    try: log('INFO', 'ImageQuality: Acquisition remains stopped (decision=Cancel)')
                    except Exception: pass
                self._scene_gate_active = False
                self._prompt_in_progress = False
                try: self._current_prompt_widget = None
                except Exception: pass
                return bool(self._current_prompt_result)

            # Worker-thread asynchronous path
            done = threading.Event()
            self._current_prompt_event = done
            self._prompt_in_progress = True
            self._current_prompt_result = False

            def _ask():
                parent = _resolve_parent()
                box = _build_box(parent)
                _diag_before(parent)
                # Watchdog and cancel timers
                watchdog = QTimer(box); watchdog.setSingleShot(True); watchdog.setInterval(120000)
                def _on_watchdog():
                    try: log('WARNING', 'ImageQuality: Scene prompt timed out (no response in 120s)')
                    except Exception: pass
                    try: box.reject()
                    except Exception: pass
                watchdog.timeout.connect(_on_watchdog); watchdog.start()

                cancel_timer = QTimer(box); cancel_timer.setSingleShot(False); cancel_timer.setInterval(400)
                def _poll_cancel():
                    try:
                        if bool(getattr(self, '_cancel_requested', False)):
                            try: log('INFO', 'ImageQuality: Global cancel while prompt — stopping test')
                            except Exception: pass
                            try: box.reject()
                            except Exception: pass
                    except Exception:
                        pass
                cancel_timer.timeout.connect(_poll_cancel); cancel_timer.start()

                def _on_finished(code: int):
                    try:
                        try: watchdog.stop()
                        except Exception: pass
                        try: cancel_timer.stop()
                        except Exception: pass
                        self._current_prompt_result = (code == QMessageBox.Yes)
                        try:
                            if parent is not None: parent.setEnabled(True)
                        except Exception:
                            pass
                        if self._current_prompt_result:
                            if was_grabbing:
                                try:
                                    log('INFO', 'ImageQuality: Resuming acquisition after scene prompt (decision=Continue)')
                                    self.camera_helper.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                                except Exception:
                                    pass
                        else:
                            try: log('INFO', 'ImageQuality: Acquisition remains stopped (decision=Cancel)')
                            except Exception: pass
                    finally:
                        self._scene_gate_active = False
                        self._prompt_in_progress = False
                        try: self._current_prompt_widget = None
                        except Exception: pass
                        done.set()

                try:
                    box.finished.connect(_on_finished)
                except Exception:
                    pass

                # Disable parent input while prompt is open
                try:
                    if parent is not None: parent.setEnabled(False)
                except Exception:
                    pass
                # Keep strong ref
                try:
                    self._current_prompt_widget = box
                except Exception:
                    pass

                # Show non-blocking and ensure visibility
                def _post_show_diag_and_recover():
                    try:
                        vis = 1 if box.isVisible() else 0
                        act = 1 if (box.isActiveWindow() if hasattr(box, 'isActiveWindow') else False) else 0
                        try:
                            pt = parent.windowTitle() if (parent is not None and hasattr(parent, 'windowTitle')) else 'N/A'
                            pc = parent.__class__.__name__ if parent is not None else 'None'
                        except Exception:
                            pt, pc = 'N/A', 'None'
                        log('INFO', f"diag: prompt={'Dark' if 'Dark' in title else 'Light'} parent=<{pc},{pt}> geom=(x={box.x()} y={box.y()} w={box.width()} h={box.height()}) visible={vis} active={act} on_ui_thread=0")
                        if not vis:
                            try: box.raise_(); box.activateWindow()
                            except Exception: pass
                            QTimer.singleShot(150, _fallback_reparent_if_hidden)
                    except Exception:
                        pass

                def _fallback_reparent_if_hidden():
                    try:
                        if not box.isVisible():
                            log('WARNING', 'Prompt visibility issue: reparent fallback without parent')
                            try: box.hide()
                            except Exception: pass
                            try:
                                box.setParent(None)
                                box.setWindowModality(Qt.ApplicationModal)
                                box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
                            except Exception:
                                pass
                            try:
                                box.open(); QTimer.singleShot(0, lambda: _position_and_raise(box, parent))
                            except Exception:
                                try:
                                    ret = box.exec_(); _on_finished(ret)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                try:
                    box.open()
                    QTimer.singleShot(0, lambda: _position_and_raise(box, parent))
                    QTimer.singleShot(200, _post_show_diag_and_recover)
                except Exception:
                    # Fallback to exec_ on UI thread only
                    ret = box.exec_()
                    _on_finished(ret)

            # Execute creation on UI thread
            try:
                QTimer.singleShot(0, _ask)
            except Exception:
                _ask()

            # Worker waits for decision
            done.wait()
            return bool(self._current_prompt_result)

        try:
            # reset cancel flag at start
            self._cancel_requested = False
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            cam = self.camera_helper.camera
            gh = self.genicam_helper
            try:
                if getattr(gh, 'camera', None) is None:
                    gh.set_camera(cam)
            except Exception:
                pass

            # Load configuration
            cfg = ConfigParser()
            try:
                cfg.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'config.ini'))
            except Exception:
                pass

            def cfg_get(sec: str, key: str, default, cast=str):
                try:
                    if not cfg.has_section('image_quality'):
                        # try upper-case section name variant
                        if cfg.has_section('IMAGE_QUALITY'):
                            sec = 'IMAGE_QUALITY'
                        else:
                            return default
                    else:
                        sec = 'image_quality'
                    if not cfg.has_option(sec, key):
                        return default
                    val = cfg.get(sec, key)
                    return cast(val)
                except Exception:
                    return default

            warmup_minutes = cfg_get('image_quality', 'warmup_minutes', 0, int)
            N_dark = cfg_get('image_quality', 'dark.N_frames', 32, int)
            N_flat = cfg_get('image_quality', 'flat.N_frames', 32, int)
            sweep_steps = cfg_get('image_quality', 'sweep.steps', 12, int)
            sweep_k = cfg_get('image_quality', 'sweep.frames_per_step', 8, int)
            target_mean_pct = cfg_get('image_quality', 'target_mean_pct', 60.0, float)
            max_sat_pct = cfg_get('image_quality', 'max_saturation_pct', 98.5, float)
            flicker_secs = cfg_get('image_quality', 'flicker.capture_seconds', 3, int)
            flicker_pass_pct = cfg_get('image_quality', 'flicker.pass_peak_pct', 5.0, float)
            flicker_fail_pct = cfg_get('image_quality', 'flicker.fail_peak_pct', 15.0, float)
            hot_sigma_k = cfg_get('image_quality', 'hotpixel.sigma_k', 6.0, float)
            hot_warn = cfg_get('image_quality', 'hotpixel.max_count_warn', 50, int)
            hot_fail = cfg_get('image_quality', 'hotpixel.max_count_fail', 200, int)
            N_straylight = cfg_get('image_quality', 'straylight.N_frames', 16, int)
            stray_req_note = cfg_get('image_quality', 'straylight.operator_note_required', False, lambda v: str(v).lower() in ('1','true','yes'))
            color_enabled = cfg_get('image_quality', 'color.enabled', False, lambda v: str(v).lower() in ('1','true','yes'))
            gamma_required = cfg_get('image_quality', 'gamma_required', True, lambda v: str(v).lower() in ('1','true','yes'))
            save_images_prompt = cfg_get('image_quality', 'save_images_prompt', True, lambda v: str(v).lower() in ('1','true','yes'))

            # Instrumentation helpers for logging
            last_first_latency_ms = {}
            def read_exposure_us():
                try:
                    if gh and gh.has_node('ExposureTime'):
                        return float(gh.get_node_value('ExposureTime'))
                    if gh and gh.has_node('ExposureTimeAbs'):
                        return float(gh.get_node_value('ExposureTimeAbs'))
                except Exception:
                    pass
                return None

            def emit_scene_stats(scene_name: str, frames_arr: np.ndarray, first_latency_ms: float = None):
                try:
                    if frames_arr is None:
                        return
                    n = int(frames_arr.shape[0]) if hasattr(frames_arr, 'shape') else (len(frames_arr) if isinstance(frames_arr, list) else 1)
                    # Use first frame to compute quick stats
                    fr0 = frames_arr[0] if n >= 1 else None
                    if fr0 is None:
                        return
                    gray0 = fr0 if (fr0.ndim == 2 or (fr0.ndim == 3 and fr0.shape[2] == 1)) else cv2.cvtColor(fr0, cv2.COLOR_BGR2GRAY)
                    mean_dn = float(np.mean(gray0))
                    max_dn = 65535.0 if gray0.dtype == np.uint16 else 255.0
                    sat_pct = float(100.0 * (float(np.max(gray0)) / max_dn)) if max_dn > 0 else 0.0
                    gv0 = int((gray0 == 0).sum())
                    gv255 = int((gray0 == int(max_dn)).sum())
                    ff_ms = first_latency_ms if first_latency_ms is not None else (last_first_latency_ms.get(scene_name) if scene_name in last_first_latency_ms else None)
                    ff_txt = f"{ff_ms:.1f}" if isinstance(ff_ms, (int, float)) else "N/A"
                    log('INFO', f"Scene stats: scene={scene_name} frames={n} first_frame_latency_ms={ff_txt} mean_dn={mean_dn:.4g} sat_pct={sat_pct:.2f}% gv0_count={gv0} gv255_count={gv255}")
                except Exception:
                    pass

            # Run ID and default output file
            run_id = time.strftime('%Y%m%d_%H%M%S')
            out_dir = os.path.abspath(os.path.join(os.getcwd(), 'result', 'image_quality', run_id))
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                pass
            report_path = os.path.join(out_dir, 'test_result.txt')

            # Environment snapshot
            try:
                from pypylon import pylon as _pylon
                sdk_ver = getattr(_pylon, 'PylonVersion', None) or getattr(_pylon, 'GetPylonVersionString', lambda: 'unknown')()
            except Exception:
                sdk_ver = 'unknown'
            try:
                model = cam.DeviceModelName.GetValue() if hasattr(cam, 'DeviceModelName') else 'Unknown'
            except Exception:
                model = 'Unknown'
            try:
                serial = cam.DeviceSerialNumber.GetValue() if hasattr(cam, 'DeviceSerialNumber') else 'Unknown'
            except Exception:
                serial = 'Unknown'

            # Helper conversions
            def to_gray(img):
                if img is None:
                    return None
                if img.ndim == 2 or (img.ndim == 3 and img.shape[2] == 1):
                    return img
                return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            def get_saturation_dn(img=None):
                if img is not None:
                    g = to_gray(img)
                    if g is None:
                        return 255.0
                    if g.dtype == np.uint8:
                        return 255.0
                    if g.dtype == np.uint16:
                        return 65535.0
                    return float(np.max(g))
                return 255.0

            def capture_frame(timeout_ms=1200):
                """Best-effort single frame capture with multiple fallbacks.
                Order: GrabOne -> (temporary StartGrabbing + RetrieveResult) -> software trigger -> helper.get_frame
                """
                # 1) Direct GrabOne
                try:
                    grab = cam.GrabOne(int(timeout_ms))
                    if grab and grab.GrabSucceeded():
                        arr = grab.Array
                        try:
                            grab.Release()
                        except Exception:
                            pass
                        return arr
                except Exception:
                    pass

                # 2) Temporary StartGrabbing + RetrieveResult
                started_here = False
                try:
                    if not cam.IsGrabbing():
                        try:
                            cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                            started_here = True
                        except Exception:
                            started_here = False
                    if cam.IsGrabbing():
                        try:
                            grab2 = cam.RetrieveResult(int(timeout_ms))
                            if grab2 and grab2.GrabSucceeded():
                                arr2 = grab2.Array
                                try:
                                    grab2.Release()
                                except Exception:
                                    pass
                                return arr2
                        except Exception:
                            pass
                finally:
                    try:
                        if started_here and cam.IsGrabbing():
                            cam.StopGrabbing()
                    except Exception:
                        pass

                # 3) Software trigger attempt via GenICam if trigger is enabled
                try:
                    if gh is not None:
                        try:
                            if getattr(gh, 'camera', None) is None:
                                gh.set_camera(cam)
                        except Exception:
                            pass
                        if gh.has_node('TriggerMode'):
                            try:
                                mode = gh.get_node_value('TriggerMode')
                            except Exception:
                                mode = None
                            if str(mode).lower() in ('on', 'true', '1'):
                                try:
                                    if gh.has_node('TriggerSource'):
                                        gh.set_node_value('TriggerSource', 'Software')
                                except Exception:
                                    pass
                                # Execute software trigger node if present
                                try:
                                    trig_node = gh._get_node('TriggerSoftware') if hasattr(gh, '_get_node') else None
                                    if trig_node is not None:
                                        for cmd in ('Execute', 'ExecuteCommand', 'Run'):
                                            try:
                                                if hasattr(trig_node, cmd):
                                                    getattr(trig_node, cmd)()
                                                    break
                                            except Exception:
                                                continue
                                except Exception:
                                    pass
                                # Try to pull the frame
                                try:
                                    grab3 = cam.RetrieveResult(int(timeout_ms))
                                    if grab3 and grab3.GrabSucceeded():
                                        arr3 = grab3.Array
                                        try:
                                            grab3.Release()
                                        except Exception:
                                            pass
                                        return arr3
                                except Exception:
                                    pass
                except Exception:
                    pass

                # 4) Helper fallback
                try:
                    return self.camera_helper.get_frame(cam)
                except Exception:
                    return None

            def capture_stack(n, settle=2, delay=0.0, scene_name=None):
                """Capture a stack of frames with higher robustness.
                If not already grabbing, start a temporary grabbing session and use RetrieveResult.
                """
                frames = []
                started_here = False
                first_frame_time = None
                try:
                    # Ensure continuous acquisition
                    try:
                        if gh and gh.has_node('TriggerMode'):
                            gh.set_node_value('TriggerMode', 'Off')
                        if gh and gh.has_node('AcquisitionMode'):
                            gh.set_node_value('AcquisitionMode', 'Continuous')
                    except Exception:
                        pass

                    # Start grab if needed
                    if not cam.IsGrabbing():
                        try:
                            cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                            started_here = True
                        except Exception:
                            started_here = False

                    # Settle frames (discard)
                    for _ in range(max(0, settle)):
                        if check_cancel():
                            break
                        if hasattr(cam, 'RetrieveResult') and cam.IsGrabbing():
                            try:
                                g0 = cam.RetrieveResult(2000)
                                if g0 and g0.GrabSucceeded():
                                    try:
                                        g0.Release()
                                    except Exception:
                                        pass
                            except Exception:
                                # On error, attempt single-frame fallback
                                _ = capture_frame()
                        else:
                            _ = capture_frame()

                    # Acquire frames
                    for _ in range(n):
                        if check_cancel():
                            break
                        f = None
                        if hasattr(cam, 'RetrieveResult') and cam.IsGrabbing():
                            # Try a few times per frame
                            restart_done = False
                            for _attempt in range(6):
                                try:
                                    t0 = time.time()
                                    gr = cam.RetrieveResult(3500)
                                    if gr and gr.GrabSucceeded():
                                        f = gr.Array
                                        try:
                                            gr.Release()
                                        except Exception:
                                            pass
                                        if first_frame_time is None:
                                            first_frame_time = (time.time() - t0) * 1000.0
                                        break
                                except Exception:
                                    # Log timeout with scene and exposure context
                                    try:
                                        expus = read_exposure_us()
                                        if scene_name:
                                            log('WARNING', f"Grab timed out (scene={scene_name} exposure_us={expus if expus is not None else 'N/A'})")
                                    except Exception:
                                        pass
                                    time.sleep(0.08)
                                    # On persistent failures, attempt one restart of grabbing
                                    if _attempt == 3 and not restart_done:
                                        try:
                                            if cam.IsGrabbing():
                                                cam.StopGrabbing()
                                        except Exception:
                                            pass
                                        try:
                                            cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                                            restart_done = True
                                        except Exception:
                                            pass
                        else:
                            # Fallback to generic capture
                            for _attempt in range(5):
                                f = capture_frame()
                                if f is not None:
                                    if first_frame_time is None:
                                        first_frame_time = 0.0  # unknown via helper; treat as 0 for logging
                                    break
                                time.sleep(0.08)
                        if f is not None:
                            frames.append(f)
                        if delay > 0:
                            time.sleep(delay)
                finally:
                    # Stop grab if we started it
                    if started_here:
                        try:
                            if cam.IsGrabbing():
                                cam.StopGrabbing()
                        except Exception:
                            pass

                if len(frames) == 0:
                    raise RuntimeError('Failed to capture frames')
                # record first-frame latency for scene
                try:
                    if scene_name is not None and first_frame_time is not None:
                        last_first_latency_ms[scene_name] = float(first_frame_time)
                except Exception:
                    pass
                return np.stack(frames, axis=0)

            # Warm-up / Pre-conditioning
            stage(10, "Warm-up / Pre-conditioning")
            # Lock processing (best effort)
            try:
                if gh.has_node('GammaEnable'):
                    gh.set_node_value('GammaEnable', False)
                if gh.has_node('Gamma') and gamma_required:
                    gh.set_node_value('Gamma', 1.0)
            except Exception:
                log('INFO', 'Feature skipped: Gamma/GammaEnable not available/writable')
            for node, val in [('NoiseReduction', 0), ('SharpeningEnable', False), ('BalanceWhiteAuto', 'Off'),
                              ('BlackLevel', None), ('TriggerMode', 'Off'), ('AcquisitionMode', 'Continuous')]:
                try:
                    if val is None:
                        continue
                    if gh.has_node(node):
                        gh.set_node_value(node, val)
                except Exception:
                    log('INFO', f"Feature skipped: {node} not available/writable")

            if warmup_minutes and warmup_minutes > 0:
                total = warmup_minutes * 60
                t0 = time.time()
                log('INFO', f"Warming up for {warmup_minutes} min…")
                while time.time() - t0 < total:
                    if check_cancel():
                        break
                    remaining = int(total - (time.time() - t0))
                    if remaining % 30 == 0:
                        log('INFO', f"Warm-up remaining: {remaining}s")
                    time.sleep(1)

            # Settings snapshot after warm-up/locking
            try:
                def _get(n):
                    try:
                        return gh.get_node_value(n) if gh and gh.has_node(n) else 'N/A'
                    except Exception:
                        return 'N/A'
                pixfmt = _get('PixelFormat')
                # bit depth inference from PixelFormat
                bd = 16 if (isinstance(pixfmt, str) and ('16' in pixfmt or '12' in pixfmt)) else (8 if isinstance(pixfmt, str) and '8' in str(pixfmt) else 'N/A')
                exposure = read_exposure_us()
                gain = _get('Gain')
                gamma_v = _get('Gamma') if gamma_required else 'OFF'
                black = _get('BlackLevel')
                trig = _get('TriggerMode')
                acq = _get('AcquisitionMode')
                try:
                    w = _get('Width'); h = _get('Height')
                    roi_txt = f"(0,0,{w},{h})" if w!='N/A' and h!='N/A' else 'N/A'
                except Exception:
                    roi_txt = 'N/A'
                fps = _get('AcquisitionFrameRate')
                sensor_temp = _get('DeviceTemperature')
                log('INFO', f"settings: pixelformat={pixfmt} bit_depth={bd} exposure_us={exposure if exposure is not None else 'N/A'} gain_db={gain} gamma={gamma_v} blacklevel_dn={black} trigger_mode={trig} acq_mode={acq} roi={roi_txt} fps={fps} sensor_temp_c={sensor_temp}")
            except Exception:
                pass

            status = 'Canceled by user' if check_cancel() else 'Completed'

            # If cancelled during warm-up, write partial report and exit
            if check_cancel():
                log('INFO', 'Cancel acknowledged — stopping acquisition and finalizing partial results')
                report_lines = [
                    "=== IMAGE QUALITY TEST RESULT =========================================",
                    f"Run ID: {run_id}     Camera: {model} / {serial}    SDK: {sdk_ver}",
                    f"Status: {status}",
                    "",
                    "[CONFIG]",
                    f"dark.N_frames={N_dark}",
                    f"flat.N_frames={N_flat}",
                    f"sweep.steps={sweep_steps}  sweep.frames_per_step={sweep_k}",
                    f"target_mean_pct={target_mean_pct}",
                    f"max_saturation_pct={max_sat_pct}",
                    f"gamma_required={'true' if gamma_required else 'false'}",
                    f"save_raw_images_prompted={'true' if save_images_prompt else 'false'}",
                    f"images_saved_to=not saved",
                    "",
                    "[PASS/FAIL SUMMARY]",
                    "Overall: FAIL",
                    "Reasons (for FAIL): Canceled by user",
                ]
                try:
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write("\n".join(report_lines))
                    log('SUCCESS', f"Wrote test_result.txt → {report_path}")
                except Exception as e:
                    log('ERROR', f"Failed to write report: {e}")
                try:
                    self.view.update_test_results('Image Quality', "\n".join(report_lines))
                except Exception:
                    pass
                return False

            # Acquire Dark Scene
            stage(25, "Dark Scene: capture frames")
            # Operator prompt (Dark)
            log('INFO', 'ImageQuality: Dark scene prompt shown.')
            dark_prompt_state = 'confirmed'
            if not show_blocking_prompt(
                title='Dark Scene Required',
                body='Please close the lens cap/cover, ensure no stray light enters the sensor, then press Continue.'
            ):
                dark_prompt_state = 'canceled'
                log('WARNING', 'ImageQuality: Dark scene canceled by user.')
                # Write partial report and stop this test safely
                status = 'Canceled by user'
                report_lines = [
                    "=== IMAGE QUALITY TEST RESULT =========================================",
                    f"Run ID: {run_id}     Camera: {model} / {serial}    SDK: {sdk_ver}",
                    f"Status: {status}",
                    "",
                    "[CONFIG]",
                    f"dark.N_frames={N_dark}",
                    f"flat.N_frames={N_flat}",
                    f"sweep.steps={sweep_steps}  sweep.frames_per_step={sweep_k}",
                    f"target_mean_pct={target_mean_pct}",
                    f"max_saturation_pct={max_sat_pct}",
                    f"gamma_required={'true' if gamma_required else 'false'}",
                    f"save_raw_images_prompted={'true' if save_images_prompt else 'false'}",
                    f"images_saved_to=not saved",
                    f"dark_scene_prompt=canceled",
                    f"scene_skipped_reason=user_canceled_prompt",
                ]
                try:
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write("\n".join(report_lines))
                    log('SUCCESS', f"Wrote test_result.txt → {report_path}")
                except Exception as e:
                    log('ERROR', f"Failed to write report: {e}")
                try:
                    self.view.update_test_results('Image Quality', "\n".join(report_lines))
                except Exception:
                    pass
                return False
            else:
                log('INFO', 'ImageQuality: Dark scene confirmed.')
            dark_stack = capture_stack(N_dark, settle=2, delay=0.0, scene_name='Dark')
            dark_gray = np.stack([to_gray(f) for f in dark_stack], axis=0).astype(np.float32)
            dark_mean = np.mean(dark_gray, axis=0)
            dark_sigma = np.std(dark_gray, axis=0)
            temporal_noise_dn = float(np.median(dark_sigma))
            dsnu_dn = float(np.std(dark_mean))
            # Zero saturation check
            sat_dn = get_saturation_dn(dark_stack[0])
            dark_sat_pct = float(100.0 * (dark_stack.max() / max(1.0, sat_dn)))
            # Scene stats for Dark
            emit_scene_stats('Dark', dark_stack, last_first_latency_ms.get('Dark'))
            # Metric logs for Dark
            log('INFO', f"TemporalNoise (EMVA): temporal_noise_dn={temporal_noise_dn:.4g} pass={np.isfinite(temporal_noise_dn)} threshold=N/A scene=Dark")
            log('INFO', f"DSNU (EMVA): dsnu_dn={dsnu_dn:.4g} pass={np.isfinite(dsnu_dn)} threshold=N/A scene=Dark")

            # Flat-Field Scene
            stage(45, "Flat-Field: reach target mean and capture frames")
            # Operator prompt (Light/Flat)
            log('INFO', 'ImageQuality: Light scene prompt shown.')
            light_prompt_state = 'confirmed'
            proceed_light = show_blocking_prompt(
                title='Light Scene Required',
                body='Please expose the sensor to a uniform, focused light source (avoid saturation), then press Continue.'
            )
            if not proceed_light:
                light_prompt_state = 'canceled'
                log('WARNING', 'ImageQuality: Light scene canceled by user.')
            else:
                log('INFO', 'ImageQuality: Light scene confirmed.')
            # Best-effort exposure tuning to reach ~target_mean_pct
            target_dn = float(target_mean_pct / 100.0 * sat_dn)
            # Initialize defaults in case light scene is canceled
            signal = None
            mean_signal = float('nan')
            prnu = float('nan')
            flat_sat_pct = float('nan')
            if proceed_light:
                try:
                    # Read current exposure and adjust coarsely
                    cur_exp = None
                    if gh.has_node('ExposureTime'):
                        cur_exp = float(gh.get_node_value('ExposureTime'))
                    elif gh.has_node('ExposureTimeAbs'):
                        cur_exp = float(gh.get_node_value('ExposureTimeAbs'))
                    if cur_exp is None:
                        cur_exp = 2000.0
                    # simple hill-climb for up to 6 iterations
                    exp = cur_exp
                    for _ in range(6):
                        if check_cancel():
                            break
                        try:
                            if gh.has_node('ExposureTime'):
                                gh.set_node_value('ExposureTime', exp)
                            elif gh.has_node('ExposureTimeAbs'):
                                gh.set_node_value('ExposureTimeAbs', exp)
                        except Exception:
                            pass
                        time.sleep(0.05)
                        f = capture_frame()
                        if f is None:
                            break
                        m = float(np.mean(to_gray(f)))
                        if m <= 1:
                            exp *= 1.8
                        elif m < target_dn * 0.95:
                            exp *= 1.2
                        elif m > target_dn * 1.05:
                            exp *= 0.85
                        else:
                            break
                except Exception:
                    pass

                flat_stack = capture_stack(N_flat, settle=2, delay=0.0, scene_name='Flat')
                flat_gray = np.stack([to_gray(f) for f in flat_stack], axis=0).astype(np.float32)
                flat_mean = np.mean(flat_gray, axis=0)
                signal = np.clip(flat_mean - dark_mean, 0, None)
                mean_signal = float(np.mean(signal))
                prnu = float(np.std(signal) / (mean_signal + 1e-9)) if mean_signal > 0 else float('nan')
                flat_sat_pct = float(100.0 * (flat_stack.max() / max(1.0, sat_dn)))
                emit_scene_stats('Flat', flat_stack, last_first_latency_ms.get('Flat'))
                # Metric logs for Flat
                log('INFO', f"PRNU (EMVA): prnu_pct={(prnu*100.0 if np.isfinite(prnu) else float('nan')):.4g}% pass={np.isfinite(prnu)} threshold=N/A scene=Flat")
                log('INFO', f"MeanSignal: mean_signal_dn={mean_signal:.4g} pass={np.isfinite(mean_signal)} threshold=N/A scene=Flat")

            # Exposure Sweep (linearity / DR / PTC)
            stage(65, "Exposure Sweep")
            # Build log-spaced exposures around current value if available
            try:
                cur_exp = None
                if gh.has_node('ExposureTime'):
                    cur_exp = float(gh.get_node_value('ExposureTime'))
                elif gh.has_node('ExposureTimeAbs'):
                    cur_exp = float(gh.get_node_value('ExposureTimeAbs'))
                if cur_exp is None or cur_exp <= 0:
                    cur_exp = 2000.0
            except Exception:
                cur_exp = 2000.0
            exp_min = max(50.0, cur_exp / 8.0)
            exp_max = cur_exp * 8.0
            exp_list = np.geomspace(exp_min, exp_max, max(3, sweep_steps)).astype(float).tolist()

            sweep_means = []
            sweep_vars = []
            used_exps = []
            early_stop = False
            for e in exp_list:
                if check_cancel():
                    break
                try:
                    if gh.has_node('ExposureTime'):
                        gh.set_node_value('ExposureTime', float(e))
                    elif gh.has_node('ExposureTimeAbs'):
                        gh.set_node_value('ExposureTimeAbs', float(e))
                except Exception:
                    pass
                _ = capture_frame()
                st = capture_stack(sweep_k, settle=0, delay=0.0, scene_name='Sweep')
                g = np.stack([to_gray(f) for f in st], axis=0).astype(np.float32)
                m = float(np.mean(g))
                v = float(np.var(g))
                sweep_means.append(m); sweep_vars.append(v); used_exps.append(float(e))
                if (m / max(1.0, sat_dn)) * 100.0 > max_sat_pct:
                    early_stop = True
                    break

            # Linearity fit
            if len(used_exps) >= 3:
                x = np.array(used_exps, dtype=np.float64)
                y = np.array(sweep_means, dtype=np.float64)
                A = np.vstack([x, np.ones_like(x)]).T
                slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
                y_pred = slope * x + intercept
                ss_res = float(np.sum((y - y_pred) ** 2))
                ss_tot = float(np.sum((y - y.mean()) ** 2))
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
            else:
                slope = float('nan'); intercept = float('nan'); r2 = float('nan')
            # Log scene stats for Sweep (aggregate)
            try:
                if len(sweep_means) > 0:
                    # Use last captured stack mean as representative
                    gv0 = gv255 = 0
                    mean_dn_agg = float(np.mean(sweep_means))
                    sat_pct_agg = float(100.0 * (max(sweep_means) / max(1.0, sat_dn)))
                    log('INFO', f"Scene stats: scene=Sweep frames={int(len(sweep_means)*sweep_k)} first_frame_latency_ms=N/A mean_dn={mean_dn_agg:.4g} sat_pct={sat_pct_agg:.2f}% gv0_count={gv0} gv255_count={gv255}")
            except Exception:
                pass
            # Metric logs for Sweep
            log('INFO', f"Linearity: linearity_gain={slope:.4g} linearity_offset_dn={intercept:.4g} linearity_r2={r2:.4g} pass={(np.isfinite(r2) and r2>=0.95)} threshold_r2=0.95 scene=Sweep")

            # Noise floor from dark
            noise_floor = temporal_noise_dn
            dr_ratio = max((sat_dn - intercept) / max(1e-6, noise_floor), 1e-6) if np.isfinite(intercept) else max(sat_dn / max(1e-6, noise_floor), 1e-6)
            dr_db = float(20.0 * math.log10(dr_ratio)) if np.isfinite(dr_ratio) else float('nan')
            dr_stops = float(math.log(dr_ratio, 2)) if np.isfinite(dr_ratio) else float('nan')
            log('INFO', f"DynamicRange: dr_db={dr_db:.4g}dB dr_stops={dr_stops:.4g} pass={np.isfinite(dr_db)} threshold_db=N/A scene=Sweep")
            log('INFO', f"NoiseFloor (EMVA): noise_floor_dn={noise_floor:.4g} pass={np.isfinite(noise_floor)} threshold=N/A scene=Dark")

            # Slanted-Edge optional (fallback to MTF proxy)
            stage(75, "Edge scene (optional) / MTF proxy")
            t_edge0 = time.time(); edge_frame = capture_frame(); ff_edge_ms = (time.time()-t_edge0)*1000.0
            try:
                gray = to_gray(edge_frame).astype(np.float32)
                gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                mag = cv2.magnitude(gx, gy)
                y0, x0 = np.unravel_index(np.argmax(mag), mag.shape)
                y0 = int(np.clip(y0, 5, gray.shape[0] - 6))
                band = gray[y0 - 5:y0 + 5, :]
                edge_spread = float(band.std()) + 1e-9
                mtf_proxy = float(1.0 / edge_spread)
                # FFT rolloff
                f = np.fft.fft2(gray)
                fshift = np.fft.fftshift(f)
                ps = np.abs(fshift) ** 2
                h, w = ps.shape; cy, cx = h // 2, w // 2; r = min(cy, cx)
                low = ps[cy - r // 4:cy + r // 4, cx - r // 4:cx + r // 4].mean()
                high_ring = ps.mean() - low
                fft_rolloff = float(low / (high_ring + 1e-9))
            except Exception:
                mtf_proxy = float('nan'); fft_rolloff = float('nan')
            try:
                emit_scene_stats('Edge', np.stack([edge_frame], axis=0) if edge_frame is not None else None, ff_edge_ms)
            except Exception:
                pass
            log('INFO', f"MTF / Proxy: mtf_proxy={mtf_proxy:.4g} pass={np.isfinite(mtf_proxy)} scene=Edge")
            log('INFO', f"FFT Rolloff: fft_rolloff_slope={fft_rolloff:.4g} pass={np.isfinite(fft_rolloff)} scene=Edge")

            # Stray-Light Sensitivity
            stage(85, "Stray-light sensitivity")
            stray_stack = capture_stack(N_straylight, settle=1, delay=0.0, scene_name='StrayLight')
            stray_gray = np.stack([to_gray(f) for f in stray_stack], axis=0).astype(np.float32)
            stray_mean = float(np.mean(stray_gray))
            dark_mean_scalar = float(np.mean(dark_gray))
            stray_delta = float(stray_mean - dark_mean_scalar)
            stray_increase_pct = float(100.0 * (stray_delta / max(1e-6, dark_mean_scalar))) if dark_mean_scalar > 0 else float('nan')
            emit_scene_stats('StrayLight', stray_stack, last_first_latency_ms.get('StrayLight'))
            log('INFO', f"StrayLight: straylight_delta_dn={stray_delta:.4g} increase_pct={stray_increase_pct:.2f}% pass={np.isfinite(stray_increase_pct)} scene=StrayLight")

            # Flicker Detection
            stage(88, "Flicker detection")
            # Collect time series of mean DN
            means_ts = []
            t_end = time.time() + max(1, int(flicker_secs))
            # Keep grabbing with a best-effort rate
            while time.time() < t_end:
                if check_cancel():
                    break
                fr = capture_frame()
                if fr is None:
                    try:
                        expus = read_exposure_us()
                        log('WARNING', f"Grab timed out (scene=Flicker exposure_us={expus if expus is not None else 'N/A'})")
                    except Exception:
                        pass
                    continue
                means_ts.append(float(np.mean(to_gray(fr))))
            flicker_peaks = []
            flicker_decision = 'N/A'
            try:
                import numpy.fft as _fft
                y = np.array(means_ts, dtype=np.float64)
                y = y - np.mean(y)
                n = len(y)
                if n >= 8:
                    Y = np.abs(_fft.rfft(y))
                    freqs = _fft.rfftfreq(n, d=1.0/30.0)  # assume ~30 FPS sampling nominally
                    rel = (Y / (np.max(Y) + 1e-12)) * 100.0
                    # find top peaks near 50/60 Hz and harmonics
                    targets = [50, 60, 100, 120]
                    for t in targets:
                        idx = int(np.argmin(np.abs(freqs - t)))
                        if idx < len(rel):
                            flicker_peaks.append((float(freqs[idx]), float(rel[idx])))
                    # decision
                    max_pk = max((p[1] for p in flicker_peaks), default=0.0)
                    if max_pk >= flicker_fail_pct:
                        flicker_decision = 'FAIL'
                    elif max_pk >= flicker_pass_pct:
                        flicker_decision = 'WARN'
                    else:
                        flicker_decision = 'PASS'
            except Exception:
                pass
            try:
                # Scene stats for Flicker (approximate)
                n = len(means_ts)
                mean_dn_ts = float(np.mean(means_ts)) if n>0 else float('nan')
                log('INFO', f"Scene stats: scene=Flicker frames={n} first_frame_latency_ms=N/A mean_dn={mean_dn_ts:.4g} sat_pct=N/A gv0_count=0 gv255_count=0")
            except Exception:
                pass
            # Flicker metric log
            try:
                peaks_fmt = '[' + ', '.join([f"(freq={a:.2f},mag_pct={b:.2f})" for a,b in flicker_peaks]) + ']'
                log('INFO', f"Flicker: flicker_peaks_hz={peaks_fmt} decision={flicker_decision} capture_s={float(flicker_secs):.1f} scene=Flicker")
            except Exception:
                pass

            # Hot/Defect Pixel Map
            hot_mask = (dark_mean + hot_sigma_k * dark_sigma)  # threshold image
            hot_pix_coords = []
            try:
                thr = np.mean(dark_mean) + hot_sigma_k * np.median(dark_sigma)
                mask = dark_mean > thr
                ys, xs = np.where(mask)
                vals = dark_mean[ys, xs]
                hot_pix_coords = list(zip(xs.tolist(), ys.tolist(), vals.tolist()))
            except Exception:
                pass
            hot_count = len(hot_pix_coords)
            # Baseline compare
            baseline_path = 'N/A'
            baseline_delta = 0
            added = []
            removed = []
            try:
                # look for hotpixels_<serial>.txt anywhere under result/
                cand = os.path.join(os.getcwd(), 'result', f'hotpixels_{serial}.txt')
                if os.path.exists(cand):
                    baseline_path = cand
                    base = set()
                    with open(cand, 'r', encoding='utf-8') as f:
                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) >= 2:
                                try:
                                    base.add((int(parts[0]), int(parts[1])))
                                except Exception:
                                    pass
                    cur = set((int(x), int(y)) for x, y, _ in hot_pix_coords)
                    added_set = cur - base
                    removed_set = base - cur
                    added = list(added_set)
                    removed = list(removed_set)
                    baseline_delta = len(added) - len(removed)
            except Exception:
                pass

            # Color metrics (best-effort)
            stage(92, "Color metrics (if applicable)")
            color_ratio_rg = float('nan'); color_ratio_bg = float('nan'); wb_repeat = float('nan')
            if color_enabled:
                try:
                    # burst
                    col_stack = capture_stack(8, settle=1, delay=0.0, scene_name='Color')
                    ratios = []
                    for fr in col_stack:
                        if fr.ndim == 3 and fr.shape[2] == 3:
                            ch_means = np.mean(fr.reshape(-1, 3), axis=0)
                            R, G, B = ch_means[2], ch_means[1], ch_means[0]  # OpenCV BGR
                            ratios.append((float(R / (G + 1e-9)), float(B / (G + 1e-9))))
                    if ratios:
                        arr = np.array(ratios)
                        color_ratio_rg = float(np.mean(arr[:, 0]))
                        color_ratio_bg = float(np.mean(arr[:, 1]))
                        wb_repeat = float(100.0 * np.std(arr[:, 0]))  # % variation of R/G as proxy
                except Exception:
                    pass
                try:
                    emit_scene_stats('Color', col_stack, last_first_latency_ms.get('Color'))
                    log('INFO', f"Color Neutrality: color_gray_balance R/G={color_ratio_rg:.4g} B/G={color_ratio_bg:.4g} wb_repeatability_pct={wb_repeat:.2f}% pass={np.isfinite(color_ratio_rg) and np.isfinite(color_ratio_bg)} scene=Color")
                except Exception:
                    pass

            # Aggregate metrics and decisions
            warnings_list = []
            if flat_sat_pct > max_sat_pct:
                warnings_list.append(f"Flat scene saturation {flat_sat_pct:.1f}% exceeds max {max_sat_pct:.1f}%")
            if dark_sat_pct > 0.5:
                warnings_list.append(f"Dark scene not fully dark (sat {dark_sat_pct:.2f}%)")
            if np.isfinite(r2) and r2 < 0.95:
                warnings_list.append(f"Linearity R² below target: {r2:.3f}")
            if flicker_decision == 'WARN':
                warnings_list.append("Flicker peak exceeds pass tolerance")
            if hot_count > hot_warn:
                warnings_list.append(f"Hot pixels above warning band: {hot_count}")

            # Emit additional detailed warnings with limits and hints
            try:
                if flat_sat_pct > max_sat_pct:
                    log('WARNING', f"Saturation high: measured={flat_sat_pct:.2f}% limit={max_sat_pct:.2f}% hint=Reduce exposure to keep <{max_sat_pct:.0f}% saturation")
                if dark_sat_pct > 0.5:
                    log('WARNING', f"Dark not fully dark: measured_sat={dark_sat_pct:.2f}% limit=0.5% hint=Ensure lens cap/off illumination")
                if np.isfinite(r2) and r2 < 0.95:
                    log('WARNING', f"Linearity low: R2={r2:.3f} limit=0.95 hint=Stabilize illumination or use linear region")
                if flicker_decision == 'WARN':
                    try:
                        max_pk = max((p[1] for p in flicker_peaks), default=0.0)
                    except Exception:
                        max_pk = 0.0
                    log('WARNING', f"Flicker elevated: max_peak={max_pk:.2f}% pass_limit={flicker_pass_pct:.2f}% hint=Use DC lighting or higher exposure")
                if hot_count > hot_warn:
                    log('WARNING', f"Hot pixels: count={hot_count} warn_band={hot_warn} hint=Enable hot-pixel correction or reduce temperature")
            except Exception:
                pass

            # Overall PASS/FAIL policy (keep existing thresholds; only warn on new ones unless configured)
            overall_pass = True
            # Hard fails based on configured or classic checks
            if np.isfinite(r2) and r2 < 0.90:
                overall_pass = False
            if hot_count > hot_fail:
                overall_pass = False
            if flicker_decision == 'FAIL':
                overall_pass = False

            # Build report text (single file)
            bit_depth = 8
            try:
                frm = capture_frame()
                if frm is not None and frm.dtype == np.uint16:
                    bit_depth = 16
            except Exception:
                pass

            def fmt_tuple_list(lst, limit=20):
                if not lst:
                    return '[]'
                shown = lst[:limit]
                extra = '' if len(lst) <= limit else f" (+{len(lst)-limit} more…)"
                parts = []
                for t in shown:
                    try:
                        if isinstance(t, tuple) and len(t) == 2:
                            parts.append(f"({t[0]},{t[1]})")
                        elif isinstance(t, (list, tuple)) and len(t) >= 3:
                            parts.append(f"({t[0]},{t[1]},{int(t[2])})")
                        else:
                            parts.append(str(t))
                    except Exception:
                        parts.append(str(t))
                return '[' + ', '.join(parts) + ']' + extra

            lines = []
            lines.append("=== IMAGE QUALITY TEST RESULT =========================================")
            lines.append(f"Run ID: {run_id}     Camera: {model} / {serial}    SDK: {sdk_ver}")
            lines.append(f"Operator Notes: <lens/aperture/illum/CCT>  Warm-up: {warmup_minutes}")
            lines.append(f"Status: {status}")
            lines.append(f"Sensor Temp: N/A      PixelFormat: {gh.get_node_value('PixelFormat') if gh and gh.has_node('PixelFormat') else 'N/A'}       BitDepth: {bit_depth}")
            lines.append("")
            lines.append("[CONFIG]")
            lines.append(f"dark.N_frames={N_dark}")
            lines.append(f"flat.N_frames={N_flat}")
            lines.append(f"sweep.steps={sweep_steps}  sweep.frames_per_step={sweep_k}")
            lines.append(f"target_mean_pct={target_mean_pct}")
            lines.append(f"max_saturation_pct={max_sat_pct}")
            lines.append(f"gamma_required={'true' if gamma_required else 'false'}")
            lines.append(f"save_raw_images_prompted={'true' if save_images_prompt else 'false'}")
            # images_saved_to placeholder, filled later
            lines.append(f"images_saved_to=not saved")
            # Prompt states
            try:
                lines.append(f"dark_scene_prompt={dark_prompt_state}")
            except Exception:
                lines.append(f"dark_scene_prompt=confirmed")
            try:
                lines.append(f"light_scene_prompt={light_prompt_state}")
            except Exception:
                lines.append(f"light_scene_prompt=confirmed")
            if ('light_prompt_state' in locals() and light_prompt_state == 'canceled') or ('dark_prompt_state' in locals() and dark_prompt_state == 'canceled'):
                lines.append("scene_skipped_reason=user_canceled_prompt")
            lines.append("")
            lines.append("[SCENES & SETTINGS SNAPSHOTS]")
            def get_node(n):
                try:
                    return gh.get_node_value(n) if gh.has_node(n) else 'N/A'
                except Exception:
                    return 'N/A'
            lines.append(f"Dark: Exposure={get_node('ExposureTime') or get_node('ExposureTimeAbs')}, Gain={get_node('Gain')}, Gamma={get_node('Gamma')}, BlackLevel={get_node('BlackLevel')}, ROI={get_node('Width')}x{get_node('Height')}, FPS={get_node('AcquisitionFrameRate')}, Frames={N_dark}")
            lines.append(f"Flat: Exposure={get_node('ExposureTime') or get_node('ExposureTimeAbs')}, Gain={get_node('Gain')}, ...")
            lines.append(f"Sweep: Gains={get_node('Gain')}, Exposure steps={[round(e,2) for e in used_exps]}")
            lines.append(f"Edge(Optional): Exposure={get_node('ExposureTime') or get_node('ExposureTimeAbs')}, ...")
            lines.append(f"StrayLight: Exposure={get_node('ExposureTime') or get_node('ExposureTimeAbs')}, Gain={get_node('Gain')}, LeakCondition=<operator note>")
            if color_enabled:
                lines.append(f"Color(Optional): Exposure={get_node('ExposureTime') or get_node('ExposureTimeAbs')}, WB mode={get_node('BalanceWhiteAuto')}, Gains RGB=...")
            lines.append("")
            lines.append("[METRICS]")
            lines.append(f"TemporalNoise(EMVA): value={temporal_noise_dn:.4g}, units=DN, pass={np.isfinite(temporal_noise_dn)}, method=median per-pixel std over N_dark, scene=Dark")
            lines.append(f"DSNU(EMVA): value={dsnu_dn:.4g}, units=DN, pass={np.isfinite(dsnu_dn)}, method=std of dark mean frame, scene=Dark")
            lines.append(f"PRNU(EMVA): value={prnu:.4g}, units=ratio, pass={np.isfinite(prnu)}, method=std/mean of (Flat-Dark), scene=Flat")
            lines.append(f"Linearity: gain={slope:.4g}, offset={intercept:.4g}, R2={r2:.4g}, method=OLS on mean DN vs exposure, scene=Sweep")
            lines.append(f"DynamicRange: dr_db={dr_db:.4g}, dr_stops={dr_stops:.4g}, method=20log10(Sat/NoiseFloor), scenes=Dark+Sweep")
            lines.append(f"NoiseFloor(EMVA): value={noise_floor:.4g}, units=DN, method=median per-pixel std on Dark, scene=Dark")
            lines.append(f"MeanSignal: flat_mean_DN={mean_signal:.4g}, sat_pct={flat_sat_pct:.2f}")
            lines.append(f"MTF / MTF Proxy: mtf_proxy={mtf_proxy:.4g}")
            lines.append(f"FFT_Rolloff: slope={fft_rolloff:.4g}")
            lines.append(f"Flicker: peaks={[(round(a,2), round(b,2)) for a,b in flicker_peaks]}, decision={flicker_decision}")
            lines.append(f"HotPixels: count={hot_count}, top20={fmt_tuple_list(hot_pix_coords, 20)}, baseline_delta={baseline_delta}")
            lines.append(f"StrayLight: delta_DN={stray_delta:.4g}, increase_pct={stray_increase_pct:.2f}, note=DN-based")
            if color_enabled:
                lines.append(f"Color(CCM Neutrality): ratio_R/G={color_ratio_rg:.4g}, ratio_B/G={color_ratio_bg:.4g}, WB_repeatability={wb_repeat:.2f}%")
            lines.append("")
            lines.append("[WARNINGS & NOTES]")
            if warnings_list:
                for wmsg in warnings_list:
                    lines.append(f"- {wmsg}")
            else:
                lines.append("- None")
            lines.append("")
            lines.append("[PASS/FAIL SUMMARY]")
            lines.append(f"Overall: {'PASS' if overall_pass else 'FAIL'}")
            if not overall_pass:
                reasons = []
                if np.isfinite(r2) and r2 < 0.90:
                    reasons.append("Linearity R² below threshold")
                if hot_count > hot_fail:
                    reasons.append("Hot pixels exceed fail band")
                if flicker_decision == 'FAIL':
                    reasons.append("Flicker above fail band")
                lines.append(f"Reasons (for FAIL): {', '.join(reasons) if reasons else 'N/A'}")
            lines.append("")
            lines.append("[IMAGE REFERENCES]")
            lines.append("User declined image saving.")

            report_text = "\n".join(lines)

            # Final summary block in logs before finalization
            try:
                log('INFO', "---- Summary (key metrics) ----")
                log('INFO', f"temporal_noise_dn={temporal_noise_dn:.4g} scene=Dark pass={np.isfinite(temporal_noise_dn)}")
                log('INFO', f"dsnu_dn={dsnu_dn:.4g} scene=Dark pass={np.isfinite(dsnu_dn)}")
                log('INFO', f"prnu_pct={(prnu*100.0 if np.isfinite(prnu) else float('nan')):.4g}% scene=Flat pass={np.isfinite(prnu)}")
                log('INFO', f"linearity_r2={r2:.4g} scene=Sweep pass={(np.isfinite(r2) and r2>=0.95)}")
                log('INFO', f"dr_db={dr_db:.4g}dB dr_stops={dr_stops:.4g} scene=Sweep pass={np.isfinite(dr_db)}")
                log('INFO', f"noise_floor_dn={noise_floor:.4g} scene=Dark pass={np.isfinite(noise_floor)}")
                log('INFO', f"mtf_proxy={mtf_proxy:.4g} scene=Edge pass={np.isfinite(mtf_proxy)}")
                log('INFO', f"fft_rolloff_slope={fft_rolloff:.4g} scene=Edge pass={np.isfinite(fft_rolloff)}")
                log('INFO', f"flicker_decision={flicker_decision} scene=Flicker")
                log('INFO', f"hot_pixels_count={hot_count} scene=Dark pass={hot_count <= hot_fail}")
            except Exception:
                pass

            # Post-test prompt to save images/plots and finalize report on GUI thread
            def _finalize_on_gui():
                nonlocal report_text
                images_saved_to = 'not saved'
                figures = {}
                # Create figures now in GUI thread to avoid thread-unsafe backends
                try:
                    import matplotlib as _mpl
                    try:
                        _mpl.use('Agg')
                    except Exception:
                        pass
                    import matplotlib.pyplot as plt
                    # hist_dark
                    fig1 = plt.figure(figsize=(5,3)); plt.hist(dark_mean.ravel(), bins=64, color='gray'); plt.title('Dark Histogram'); plt.xlabel('DN'); plt.ylabel('Count'); figures['hist_dark.png'] = fig1
                    # hist_flat
                    fig2 = plt.figure(figsize=(5,3)); plt.hist(flat_mean.ravel(), bins=64, color='orange'); plt.title('Flat Histogram'); plt.xlabel('DN'); plt.ylabel('Count'); figures['hist_flat.png'] = fig2
                    # prnu/dsnu heatmaps
                    fig3 = plt.figure(figsize=(4,4)); plt.imshow(dark_mean, cmap='magma'); plt.title('DSNU map'); plt.colorbar(); figures['dsnu_heatmap.png'] = fig3
                    fig4 = plt.figure(figsize=(4,4)); plt.imshow(signal, cmap='viridis'); plt.title('PRNU map (signal)'); plt.colorbar(); figures['prnu_heatmap.png'] = fig4
                    # linearity
                    if len(used_exps) >= 2:
                        fig5 = plt.figure(figsize=(4,3)); plt.plot(used_exps, sweep_means, 'o');
                        try:
                            xx = np.linspace(min(used_exps), max(used_exps), 100); yy = slope*xx + intercept; plt.plot(xx, yy, '-');
                        except Exception:
                            pass
                        plt.xscale('log'); plt.xlabel('Exposure'); plt.ylabel('Mean DN'); plt.title('Linearity'); figures['linearity.png'] = fig5
                    # ptc
                    if len(sweep_means) >= 2:
                        fig6 = plt.figure(figsize=(4,3)); plt.plot(sweep_means, sweep_vars, 'o'); plt.xlabel('Mean DN'); plt.ylabel('Variance'); plt.title('PTC'); figures['ptc.png'] = fig6
                    # dr gauge (simple text figure)
                    fig7 = plt.figure(figsize=(4,2)); plt.title('Dynamic Range'); plt.text(0.1,0.5,f"DR: {dr_db:.1f} dB ({dr_stops:.2f} stops)"); plt.axis('off'); figures['dr_gauge.png'] = fig7
                    # mtf or fft rolloff
                    fig8 = plt.figure(figsize=(4,3)); plt.title('FFT Rolloff'); plt.bar([0], [fft_rolloff]); plt.xticks([0],["rolloff"]); figures['fft_rolloff.png'] = fig8
                    # hot pixel map
                    if hot_pix_coords:
                        fig9 = plt.figure(figsize=(4,4)); ys=[p[1] for p in hot_pix_coords]; xs=[p[0] for p in hot_pix_coords]; plt.scatter(xs, ys, s=2, c='r'); plt.gca().invert_yaxis(); plt.title('Hot Pixel Map'); figures['hot_pixel_map.png'] = fig9
                    # straylight hist
                    fig10 = plt.figure(figsize=(4,3)); plt.hist(stray_gray.ravel(), bins=64, color='purple'); plt.title('Stray-light Histogram'); figures['straylight_hist.png'] = fig10
                    # color balance
                    if color_enabled and np.isfinite(color_ratio_rg) and np.isfinite(color_ratio_bg):
                        fig11 = plt.figure(figsize=(4,3)); plt.bar(['R/G','B/G'], [color_ratio_rg, color_ratio_bg]); plt.ylim(0,2); plt.title('Gray Balance'); figures['color_gray_balance.png'] = fig11
                except Exception:
                    figures = {}

                if save_images_prompt and figures:
                    from PyQt5.QtWidgets import QMessageBox, QFileDialog, QWidget
                    # Prefer the main GUI window as parent for modality
                    try:
                        parent_widget = self.view if isinstance(self.view, QWidget) else None
                    except Exception:
                        parent_widget = None
                    try:
                        resp = QMessageBox.question(
                            parent_widget,
                            'Save Images',
                            'Do you want to save all images and plots from this test?',
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )
                    except Exception:
                        resp = QMessageBox.No
                    if resp == QMessageBox.Yes:
                        try:
                            # Reuse the standard folder picker component
                            folder = QFileDialog.getExistingDirectory(parent_widget, 'Select Directory to Save Images', '')
                        except Exception:
                            folder = ''
                        if folder:
                            # compute relative path to report directory
                            try:
                                images_saved_to = os.path.relpath(folder, os.path.dirname(report_path))
                            except Exception:
                                images_saved_to = folder
                            # Save all figures
                            for name, fig in figures.items():
                                try:
                                    fig.savefig(os.path.join(folder, name), dpi=120, bbox_inches='tight')
                                except Exception:
                                    pass
                            # Close figures to free resources
                            try:
                                import matplotlib.pyplot as plt
                                plt.close('all')
                            except Exception:
                                pass
                # Update report text with images_saved_to and image references
                rep_lines = report_text.splitlines()
                for i, ln in enumerate(rep_lines):
                    if ln.startswith('images_saved_to='):
                        rep_lines[i] = f"images_saved_to={'not saved' if images_saved_to=='not saved' else images_saved_to}"
                        break
                # Replace [IMAGE REFERENCES] section content
                try:
                    idx = rep_lines.index('[IMAGE REFERENCES]')
                    rep_lines = rep_lines[:idx+1]
                    if images_saved_to == 'not saved' or not figures:
                        rep_lines.append('User declined image saving.')
                    else:
                        # list filenames only
                        for fn in figures.keys():
                            rep_lines.append(f"- {fn}")
                except Exception:
                    pass
                report_text_final = "\n".join(rep_lines)

                # Write single report file
                try:
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(report_text_final)
                    log('SUCCESS', f"Wrote test_result.txt → {report_path}")
                except Exception as e:
                    log('ERROR', f"Failed to write report: {e}")

                # Show results dialog
                try:
                    self.view.update_test_results('Image Quality', report_text_final)
                except Exception:
                    pass

            # Invoke GUI-thread finalization
            try:
                # Slight delay so the progress dialog can close before showing prompts
                QTimer.singleShot(200, _finalize_on_gui)
            except Exception:
                # Fallback: write report without images
                try:
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(report_text)
                except Exception:
                    pass
                self.view.update_test_results('Image Quality', report_text)

            return True

        except Exception as e:
            err = f"Failed to run image quality tests: {e}"
            self.logger.error(err)
            try:
                self.view.show_error('Test Error', err)
            except Exception:
                pass
            return False

    def run_image_quality_tests_async(self, on_done):
        """Asynchronous wrapper to run ImageQuality in a background thread and report completion on the UI thread.

        on_done: callable(bool) invoked on UI thread with True/False when finished.
        """
        import threading

        def _runner():
            ok = False
            try:
                ok = bool(self.run_image_quality_tests())
            except Exception:
                ok = False
            # Report back on UI thread if possible
            try:
                QTimer.singleShot(0, lambda: on_done(ok))
            except Exception:
                try:
                    on_done(ok)
                except Exception:
                    pass

        try:
            t = threading.Thread(target=_runner, name="ImageQualityAsync", daemon=True)
            t.start()
        except Exception as e:
            try:
                QTimer.singleShot(0, lambda: on_done(False))
            except Exception:
                try:
                    on_done(False)
                except Exception:
                    pass

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
        """Run camera calibration - construct and show the calibration dialog directly."""
        try:
            self.logger.info("Starting camera calibration (GUI flow)")

            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            # Ensure genicam_helper has camera attached
            try:
                if getattr(self.genicam_helper, 'camera', None) is None:
                    self.genicam_helper.set_camera(self.camera_helper.camera)
            except Exception:
                pass

            # Stop any active live view so dialog initially shows chart only
            try:
                if getattr(self, 'is_live_grabbing', False):
                    self.logger.debug("Stopping live view before opening calibration dialog")
                    try:
                        self.stop_live_view()
                    except Exception:
                        pass
            except Exception:
                pass

            # Also ensure the view's live timer is stopped and live image cleared
            try:
                if hasattr(self.view, 'live_timer'):
                    try:
                        self.view.live_timer.stop()
                    except Exception:
                        pass
                if hasattr(self.view, 'image_label'):
                    try:
                        self.view.image_label.clear()
                    except Exception:
                        pass
            except Exception:
                pass

            # Lazy import of the dialog to avoid circular imports with the view module
            from gui.main_gui import CameraCalibrationDialog

            # Construct and execute the dialog directly so presenter controls the flow
            dlg = CameraCalibrationDialog(self.view, self.genicam_helper, self.camera_helper)
            res = dlg.exec_()
            accepted = (res == QDialog.Accepted)
            self.logger.info(f"Camera calibration dialog closed with result: {accepted}")
            return accepted

        except Exception as e:
            error_msg = f"Failed to initialize camera calibration: {str(e)}"
            self.logger.error(error_msg)
            try:
                self.view.show_error("Calibration Error", error_msg)
            except Exception:
                pass
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
        """Run camera initialization test (robust, non-invasive).

        Scope: modify test routine logic only; reuse existing helpers and UI wiring.
        """
        import time
        import json
        import os
        import platform
        from configparser import ConfigParser
        from pypylon import pylon

        TEST_NAME = "Camera Initialization Test"

        def log(level: str, msg: str):
            try:
                self.view.log_message(msg, level)
            except Exception:
                pass
            # Mirror to presenter logger at similar level
            lvl = (level or "INFO").upper()
            if lvl == "ERROR":
                self.logger.error(msg)
            elif lvl in ("WARN", "WARNING"):
                self.logger.warning(msg)
            elif lvl == "SUCCESS":
                self.logger.info(msg)
            else:
                self.logger.info(msg)

        # Load optional configuration with sensible defaults
        cfg = ConfigParser()
        try:
            cfg.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'config.ini'))
        except Exception:
            pass

        def cfg_get(section: str, option: str, default, cast=str):
            try:
                if not cfg.has_section(section) or not cfg.has_option(section, option):
                    return default
                val = cfg.get(section, option)
                return cast(val)
            except Exception:
                return default

        # Configurable inputs with defaults
        transport = cfg_get('CAMERA', 'transport', 'auto', str).lower()  # auto|GEV|U3V
        open_timeout_ms = cfg_get('CAMERA', 'open_timeout_ms', 3000, int)
        grab_timeout_ms = cfg_get('CAMERA', 'grab_timeout_ms', 2000, int)
        allowed_pixelformats = cfg_get('CAMERA', 'allowed_pixelformats', 'Mono8,BayerRG8,YCbCr422_8', str)
        allowed_pixelformats = [s.strip() for s in allowed_pixelformats.split(',') if s.strip()]
        gev_min_heartbeat_ms = cfg_get('CAMERA', 'gev_min_heartbeat_ms', 3000, int)
        expected_link_gbps = cfg_get('CAMERA', 'expected_link_gbps', 5, float)
        preferred_serial = cfg_get('CAMERA', 'preferred_serial', '', str).strip()
        userset_to_load = cfg_get('CAMERA', 'userset', '', str).strip()

        # No artifact directory creation (JSON output removed per request)

        # Stage helpers (log; progress mapping via text only)
        def stage(pct: int, text: str):
            log('INFO', f"[{pct}%] {text}")

        # Host/SDK block
        try:
            host = {
                'os': platform.platform(),
                'python': platform.python_version(),
                'pylon_version': getattr(pylon, 'PylonVersion', None) or getattr(pylon, 'GetPylonVersionString', lambda: 'unknown')(),
            }
        except Exception:
            host = {'os': platform.platform(), 'python': platform.python_version(), 'pylon_version': 'unknown'}
        log('INFO', f"Host/SDK: {host}")

        # Discovery & select
        t0 = time.time()
        stage(10, "Discover devices")
        try:
            devices = self.camera_helper.enumerate_cameras()
        except Exception as e:
            devices = []
            log('ERROR', f"Discovery failed: {e}")

        # Filter by transport
        def iface_kind(d: dict) -> str:
            return (d.get('interface') or '').lower()

        if transport == 'gev':
            devices = [d for d in devices if 'gig' in iface_kind(d) or 'gev' in iface_kind(d) or 'baslergig' in iface_kind(d)]
        elif transport == 'u3v':
            devices = [d for d in devices if 'usb' in iface_kind(d) or 'u3v' in iface_kind(d) or iface_kind(d) == 'baslerusb']
        # else auto = no extra filter

        if not devices:
            log('ERROR', f"No GenICam devices found on {transport.upper() if transport!='auto' else 'AUTO'}. Check cables/power/driver. For GEV: confirm NIC, IP subnet, firewall.")
            self.view.show_error(TEST_NAME, "No matching devices found.")
            return False

        # Select by serial if provided
        stage(20, "Select target device")
        target = None
        if preferred_serial:
            for d in devices:
                if d.get('id') == preferred_serial:
                    target = d; break
        if target is None:
            target = devices[0]
        log('INFO', f"Selected device: {target}")

        # Open with exclusive access (pylon opens exclusively by default)
        stage(30, "Open device")
        t_open0 = time.time()
        try:
            # Stop any live stream from GUI path before test open (UI already tries)
            try:
                if hasattr(self, 'stop_live_view'):
                    self.stop_live_view()
            except Exception:
                pass
            # If a camera is currently open via helper, close it to avoid exclusive-open conflict
            try:
                if self.camera_helper and self.camera_helper.camera and self.camera_helper.camera.IsOpen():
                    try:
                        if self.camera_helper.camera.IsGrabbing():
                            self.camera_helper.camera.StopGrabbing()
                    except Exception:
                        pass
                    self.camera_helper.camera.Close()
            except Exception:
                pass
            cam = self.camera_helper.connect_camera(target)
            self.genicam_helper.set_camera(cam)
            self.camera = cam
        except Exception as e:
            log('ERROR', f"Open failed: {e}")
            self.view.show_error(TEST_NAME, f"Exclusive access denied—camera in use by another app. Close it and retry. Details: {e}")
            return False
        open_time = time.time() - t_open0

        # Optional: load UserSet
        if userset_to_load:
            stage(35, "Load UserSet")
            try:
                self.genicam_helper.set_node_value('UserSetSelector', userset_to_load)
                self.genicam_helper.set_node_value('UserSetLoad', True)
                log('INFO', f"Loaded UserSet: {userset_to_load}")
            except Exception as e:
                log('WARN', f"Failed to load UserSet '{userset_to_load}': {e}")

        # Identity verification
        stage(45, "Read identity")
        ident = {}
        try:
            info = cam.GetDeviceInfo()
            # Pylon DeviceInfo methods
            def safe_get(m):
                try:
                    return getattr(info, m)()
                except Exception:
                    return ''
            ident = {
                'DeviceVendorName': safe_get('GetVendorName'),
                'DeviceModelName': safe_get('GetModelName'),
                'DeviceSerialNumber': safe_get('GetSerialNumber'),
                'DeviceVersion': safe_get('GetDeviceVersion') or safe_get('GetDeviceVersionString'),
                'DeviceFirmwareVersion': safe_get('GetFirmwareVersion') or safe_get('GetFirmwareVersionString'),
            }
            # Validate non-empty required
            required = ['DeviceVendorName', 'DeviceModelName', 'DeviceSerialNumber']
            if any(not ident.get(k) for k in required):
                raise RuntimeError("Required identity nodes missing/empty")
            log('INFO', f"Identity: {ident}")
        except Exception as e:
            log('ERROR', f"Identity read failed: {e}")
            # Continue to cleanup below
            try:
                cam.Close()
            except Exception:
                pass
            self.view.show_error(TEST_NAME, f"Identity verification failed: {e}")
            return False

        # Transport snapshot
        stage(55, "Read transport")
        transport_snapshot = {}
        try:
            if transport in ('auto', 'gev'):
                try:
                    transport_snapshot.update({
                        'GevCurrentIPAddress': self.genicam_helper.get_node_value('GevCurrentIPAddress') if self.genicam_helper.has_node('GevCurrentIPAddress') else None,
                        'GevSCPSPacketSize': self.genicam_helper.get_node_value('GevSCPSPacketSize') if self.genicam_helper.has_node('GevSCPSPacketSize') else None,
                        'GevSCPD': self.genicam_helper.get_node_value('GevSCPD') if self.genicam_helper.has_node('GevSCPD') else None,
                        'GevHeartbeatTimeout': self.genicam_helper.get_node_value('GevHeartbeatTimeout') if self.genicam_helper.has_node('GevHeartbeatTimeout') else None,
                    })
                except Exception as e:
                    log('WARN', f"GEV transport snapshot partial: {e}")
                # Heartbeat sanity
                try:
                    hb = transport_snapshot.get('GevHeartbeatTimeout')
                    if hb is not None and int(hb) < int(gev_min_heartbeat_ms):
                        log('WARN', f"GEV heartbeat ({hb} ms) below minimum {gev_min_heartbeat_ms} ms; attempting to increase…")
                        try:
                            self.genicam_helper.set_node_value('GevHeartbeatTimeout', int(gev_min_heartbeat_ms))
                            transport_snapshot['GevHeartbeatTimeout'] = self.genicam_helper.get_node_value('GevHeartbeatTimeout')
                            log('SUCCESS', f"GEV heartbeat increased to {transport_snapshot['GevHeartbeatTimeout']} ms")
                        except Exception as e2:
                            log('WARN', f"Failed to increase heartbeat: {e2}")
                except Exception:
                    pass
            if transport in ('auto', 'u3v'):
                try:
                    # Best-effort U3V link info
                    # Common nodes vary; try a few
                    link = {
                        'DeviceLinkThroughputLimit': self.genicam_helper.get_node_value('DeviceLinkThroughputLimit') if self.genicam_helper.has_node('DeviceLinkThroughputLimit') else None,
                        'DeviceLinkCurrentThroughput': self.genicam_helper.get_node_value('DeviceLinkCurrentThroughput') if self.genicam_helper.has_node('DeviceLinkCurrentThroughput') else None,
                        'DeviceLinkSpeed': self.genicam_helper.get_node_value('DeviceLinkSpeed') if self.genicam_helper.has_node('DeviceLinkSpeed') else None,
                    }
                    transport_snapshot.update(link)
                    # Sanity: link speed if available
                    sp = link.get('DeviceLinkSpeed')
                    if sp:
                        try:
                            gbps = float(sp) / 1e9
                            if gbps + 1e-6 < expected_link_gbps:
                                log('WARN', f"U3V link speed low ({gbps:.2f} Gbps < {expected_link_gbps:.2f} Gbps); continuing")
                        except Exception:
                            pass
                except Exception as e:
                    log('WARN', f"U3V transport snapshot partial: {e}")
        except Exception:
            pass

        # Stream preparation
        stage(65, "Configure stream")
        stream_cfg = {}
        try:
            # Trigger/Acquisition modes
            try:
                if self.genicam_helper.has_node('TriggerMode'):
                    self.genicam_helper.set_node_value('TriggerMode', 'Off')
            except Exception as e:
                log('WARN', f"Could not set TriggerMode=Off: {e}")
            try:
                if self.genicam_helper.has_node('AcquisitionMode'):
                    self.genicam_helper.set_node_value('AcquisitionMode', 'Continuous')
            except Exception as e:
                log('WARN', f"Could not set AcquisitionMode=Continuous: {e}")

            # PixelFormat priority attempt
            chosen_fmt = None
            for fmt in allowed_pixelformats:
                try:
                    if self.genicam_helper.has_node('PixelFormat'):
                        self.genicam_helper.set_node_value('PixelFormat', fmt)
                        chosen_fmt = fmt
                        log('INFO', f"PixelFormat set to {fmt}")
                        break
                except Exception:
                    continue
            if chosen_fmt is None:
                log('WARN', "PixelFormat not changeable; proceeding with current")
                try:
                    chosen_fmt = self.genicam_helper.get_node_value('PixelFormat') if self.genicam_helper.has_node('PixelFormat') else None
                except Exception:
                    pass

            # Payload and ROI sanity
            w = h = payload = None
            try:
                w = int(self.genicam_helper.get_node_value('Width')) if self.genicam_helper.has_node('Width') else None
                h = int(self.genicam_helper.get_node_value('Height')) if self.genicam_helper.has_node('Height') else None
            except Exception:
                pass
            try:
                payload = int(self.genicam_helper.get_node_value('PayloadSize')) if self.genicam_helper.has_node('PayloadSize') else None
            except Exception:
                pass
            if payload is None or payload <= 0:
                log('ERROR', f"Invalid PayloadSize: {payload}")
                cam.Close()
                self.view.show_error(TEST_NAME, "Invalid payload size")
                return False

            def bpp_for(fmt: str) -> float:
                # Common approximations
                m = (fmt or '').lower()
                if 'mono8' in m or 'bayer' in m and '8' in m:
                    return 8
                if 'mono12' in m or '12' in m:
                    return 12
                if 'mono16' in m or '16' in m:
                    return 16
                if 'ycbcr422_8' in m or 'yuv422' in m:
                    return 16  # 16 bits per pixel
                if 'rgb8' in m:
                    return 24
                return 0

            if w and h and chosen_fmt:
                bpp = bpp_for(chosen_fmt)
                if bpp > 0:
                    expected = int(w * h * bpp / 8)
                    if abs(expected - payload) > max(1, int(0.01 * expected)):
                        log('WARN', f"Payload mismatch: W×H×bpp={expected} vs PayloadSize={payload}")

            stream_cfg = {'Width': w, 'Height': h, 'PixelFormat': chosen_fmt, 'PayloadSize': payload,
                          'AcquisitionMode': 'Continuous', 'TriggerMode': 'Off'}
        except Exception as e:
            log('WARN', f"Stream configuration partial: {e}")

        # Acquisition cycle
        stage(80, "Acquire 3 frames")
        first_frame_latency = None
        frame_stats = {'count': 0, 'means': [], 'vars': [], 'suspicious': False}
        t_acq0 = time.time()
        try:
            # Start grabbing
            try:
                cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            except Exception:
                pass
            last_ts = None
            for i in range(3):
                t_f0 = time.time()
                try:
                    grab = cam.RetrieveResult(grab_timeout_ms)
                    ok = grab and grab.GrabSucceeded()
                    arr = grab.Array if ok else None
                    try:
                        grab.Release()
                    except Exception:
                        pass
                except Exception as e:
                    ok = False
                    arr = None
                    log('ERROR', f"Grab timeout or error: {e}")
                if not ok or arr is None:
                    cam.StopGrabbing()
                    cam.Close()
                    self.view.show_error(TEST_NAME, "Grab timeout—try increasing grab_timeout_ms; check bandwidth/packet size; verify PixelFormat/payload.")
                    return False
                if arr.size == 0:
                    cam.StopGrabbing(); cam.Close()
                    self.view.show_error(TEST_NAME, "Empty frame received")
                    return False

                # First frame latency
                if i == 0:
                    first_frame_latency = time.time() - t_f0

                # Timestamp monotonic check (using host time as proxy)
                now_ts = time.time()
                if last_ts is not None and now_ts < last_ts:
                    log('WARN', "Non-monotonic timestamps observed (host time proxy)")
                last_ts = now_ts

                # Quick stats
                try:
                    import numpy as _np
                    mean = float(_np.mean(arr))
                    var = float(_np.var(arr))
                    frame_stats['means'].append(mean)
                    frame_stats['vars'].append(var)
                    if var < 1e-6 or mean < 1.0:
                        frame_stats['suspicious'] = True
                except Exception:
                    pass
                frame_stats['count'] += 1

            # Stop grabbing after cycle
            try:
                cam.StopGrabbing()
            except Exception:
                pass
        except Exception as e:
            log('ERROR', f"Acquisition error: {e}")
            try:
                cam.StopGrabbing()
            except Exception:
                pass
            try:
                cam.Close()
            except Exception:
                pass
            return False

        # Mini robustness checks
        robustness = {'reopen_ok': False, 'exclusive_denied_handled': False, 'packet_size_fallback': False}
        try:
            # Reopen test
            try:
                cam.Close()
            except Exception:
                pass
            # Re-open
            cam = self.camera_helper.connect_camera(target)
            self.genicam_helper.set_camera(cam)
            # Re-grab 1 frame
            try:
                grab = cam.GrabOne(grab_timeout_ms)
                ok = grab and grab.GrabSucceeded()
                arr = grab.Array if ok else None
                try:
                    grab.Release()
                except Exception:
                    pass
                robustness['reopen_ok'] = bool(ok and arr is not None and arr.size > 0)
            except Exception:
                robustness['reopen_ok'] = False

            # Exclusive access denial simulation with a separate helper to avoid clobbering state
            try:
                temp_helper = self.camera_helper.__class__(simulate=self.camera_helper.simulate)
                try:
                    temp_helper.connect_camera(target)
                    # If it unexpectedly succeeds, close immediately and mark handled as False
                    try:
                        if temp_helper.camera and temp_helper.camera.IsOpen():
                            temp_helper.camera.Close()
                    except Exception:
                        pass
                    robustness['exclusive_denied_handled'] = False
                except Exception:
                    # Expected: device busy
                    robustness['exclusive_denied_handled'] = True
            except Exception:
                pass

            # Optional GEV packet size sanity
            try:
                if transport in ('auto', 'gev') and self.genicam_helper.has_node('GevSCPSPacketSize'):
                    try:
                        self.genicam_helper.set_node_value('GevSCPSPacketSize', 9000)
                    except Exception:
                        # fallback to 1500
                        try:
                            self.genicam_helper.set_node_value('GevSCPSPacketSize', 1500)
                            robustness['packet_size_fallback'] = True
                            log('WARN', 'Jumbo frames unsupported—falling back to 1500; verify NIC MTU and switch config.')
                        except Exception:
                            pass
            except Exception:
                pass
        finally:
            # Final cleanup
            try:
                if cam and cam.IsOpen():
                    try:
                        if cam.IsGrabbing():
                            cam.StopGrabbing()
                    except Exception:
                        pass
                    cam.Close()
            except Exception:
                pass
            # Restore connection for GUI flow (re-open selected target so live view can resume)
            try:
                cam2 = self.camera_helper.connect_camera(target)
                self.genicam_helper.set_camera(cam2)
                self.camera = cam2
                # Optionally resume live view for right-panel behavior
                try:
                    self.start_live_view()
                except Exception:
                    pass
            except Exception:
                pass

        # Timing
        total_duration = time.time() - t0
        timing = {
            'discovery_time_ms': int(1000 * (t_open0 - t0)),
            'open_time_ms': int(1000 * open_time),
            'first_frame_latency_ms': int(1000 * (first_frame_latency or 0)),
            'total_duration_ms': int(1000 * total_duration),
        }

        # Stage 90 still used for validation checkpoint, no persistence
        stage(90, "Validate state")

        # Pass/Fail evaluation
        passed = (
            bool(devices) and bool(target) and bool(ident.get('DeviceSerialNumber')) and
            frame_stats.get('count', 0) >= 3 and stream_cfg.get('PayloadSize', 0) > 0
        )
        if passed:
            log('SUCCESS', 'PASS')
        else:
            log('ERROR', 'FAIL')

        stage(100, f"Complete with {'PASS' if passed else 'FAIL'}")

        # Compose concise summary for UI results dialog
        summary_lines = [
            "=== Camera Initialization Test Results ===",
            f"Identity: {ident}",
            f"Transport: {transport_snapshot}",
            f"Stream: {stream_cfg}",
            f"Timing (ms): {timing}",
            f"Frames: count={frame_stats.get('count')} suspicious={frame_stats.get('suspicious')}",
            f"Robustness: {robustness}",
            f"Final: {'PASS' if passed else 'FAIL'}",
        ]
        self.view.update_test_results(TEST_NAME, "\n".join(summary_lines))
        return bool(passed)

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
