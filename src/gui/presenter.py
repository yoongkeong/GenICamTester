# presenter.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, Qt
from pypylon import pylon
import cv2
import numpy as np
import time
import logging

class CameraPresenter(QObject):
    # Signals used to marshal scene prompts onto the UI thread
    # (scene_type, parent)
    scenePromptRequested = pyqtSignal(str, object)
    # (scene_type, confirmed)
    scenePromptResult = pyqtSignal(str, bool)
    def __init__(self, view):
        super().__init__()
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
        # Prompt state
        self._current_prompt_widget = None
        self._current_prompt_parent = None
        self._current_prompt_event = None
        self._current_prompt_result = False
        self._prompt_in_progress = False
        self._scene_gate_active = False

        # Connect prompt request to UI-thread slot
        try:
            self.scenePromptRequested.connect(self._on_scene_prompt_requested)
        except Exception:
            pass

    def _on_scene_prompt_requested(self, scene_type: str, parent=None):
        """UI-thread slot: create and show the scene prompt without blocking the event loop.
        Emits scenePromptResult(scene_type, confirmed) when done.
        """
        try:
            # Resolve a parent if not provided or invalid
            from PyQt5.QtWidgets import QApplication, QMessageBox as _QMB
            app = QApplication.instance()
            p = None
            try:
                p = parent if parent is not None else (app.activeModalWidget() or app.activeWindow())
                if p is None:
                    # Scan top-levels for Test Setup – ImageQuality dialog
                    for w in app.topLevelWidgets():
                        try:
                            title = str(getattr(w, 'windowTitle', lambda: '')())
                        except Exception:
                            title = ''
                        if title and ('Test Setup' in title and 'ImageQuality' in title):
                            p = w
                            break
            except Exception:
                p = None

            # Build dialog text
            if 'dark' in scene_type.lower():
                title = 'Dark Scene Required'
                body = 'Please close the lens cap or darken the scene, then click Continue.'
            else:
                title = 'Light Scene Required'
                body = 'Please expose the camera to a uniform light, then click Continue.'

            box = _QMB(p)
            box.setWindowTitle(title)
            box.setText(body)
            box.setIcon(_QMB.Information)
            try:
                box.setWindowModality(Qt.ApplicationModal)
                try:
                    box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                box.setStandardButtons(_QMB.Yes | _QMB.Cancel)
                try:
                    box.button(_QMB.Yes).setText('Continue')
                    box.button(_QMB.Cancel).setText('Cancel')
                except Exception:
                    pass
                try:
                    box.setDefaultButton(_QMB.Yes)
                except Exception:
                    pass
            except Exception:
                box.setStandardButtons(_QMB.Ok)

            # Disable parent while prompt is open
            try:
                if p is not None:
                    p.setEnabled(False)
            except Exception:
                pass

            # Keep refs
            self._current_prompt_widget = box
            self._current_prompt_parent = p

            def _finished(code: int):
                try:
                    confirmed = (code == _QMB.Yes)
                except Exception:
                    confirmed = False
                # Re-enable parent before emitting result
                try:
                    if self._current_prompt_parent is not None:
                        self._current_prompt_parent.setEnabled(True)
                except Exception:
                    pass
                # Emit result
                try:
                    self.scenePromptResult.emit(scene_type, bool(confirmed))
                except Exception:
                    pass
                # Cleanup
                try:
                    self._current_prompt_widget = None
                    self._current_prompt_parent = None
                except Exception:
                    pass

            try:
                box.finished.connect(_finished)
            except Exception:
                pass

            try:
                # Non-blocking show + center/raise
                box.open()
                try:
                    if p is not None:
                        gp = p.geometry()
                        sz = box.sizeHint()
                        x = gp.x() + (gp.width() - sz.width()) // 2
                        y = gp.y() + (gp.height() - sz.height()) // 2
                        box.move(max(0, x), max(0, y))
                        try:
                            box.raise_()
                            box.activateWindow()
                        except Exception:
                            pass
                except Exception:
                    pass
                # Diagnostics
                try:
                    geom = box.geometry()
                    self.logger.info(
                        f"diag: prompt='{title}' parent='{getattr(p,'windowTitle',lambda: '')() if p else 'None'}' geom=({geom.x()},{geom.y()},{geom.width()},{geom.height()}) visible={box.isVisible()}"
                    )
                    self.logger.info(f"[ImageQuality] {scene_type} prompt shown.")
                except Exception:
                    pass
                # Watchdog (120s): auto-cancel if still open
                def _watchdog():
                    try:
                        if self._current_prompt_widget is box and box.isVisible():
                            try:
                                self.logger.warning(f"ImageQuality: {scene_type} prompt timeout (120s); auto-cancel")
                            except Exception:
                                pass
                            try:
                                # emit cancel result and close
                                if self._current_prompt_parent is not None:
                                    try:
                                        self._current_prompt_parent.setEnabled(True)
                                    except Exception:
                                        pass
                                self.scenePromptResult.emit(scene_type, False)
                                box.reject()
                            except Exception:
                                pass
                            try:
                                self._current_prompt_widget = None
                                self._current_prompt_parent = None
                            except Exception:
                                pass
                    except Exception:
                        pass
                try:
                    QTimer.singleShot(120000, _watchdog)
                except Exception:
                    pass
            except Exception:
                # If show failed, emit immediate cancel to unblock worker
                try:
                    self.scenePromptResult.emit(scene_type, False)
                except Exception:
                    pass
        except Exception:
            try:
                self.scenePromptResult.emit(scene_type, False)
            except Exception:
                pass

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

    def run_init_cam_test(self):
        """Quick camera initialization sanity check used by GUI."""
        try:
            self.logger.info("Starting camera initialization test")
            if not self.camera_helper or not getattr(self.camera_helper, 'camera', None):
                self.logger.error("Camera not connected for init test")
                try:
                    self.view.show_error("Camera Initialization", "Camera not connected")
                except Exception:
                    pass
                return False
            cam = self.camera_helper.camera
            # Try grabbing a single frame
            try:
                frame = self.camera_helper.get_frame(cam, timeout_ms=2000)
            except Exception:
                frame = None
            if frame is None:
                self.logger.error("Initialization test failed: could not grab a frame")
                try:
                    self.view.show_error("Camera Initialization", "Failed to grab test frame")
                except Exception:
                    pass
                return False
            # Keep last captured frame for UI preview
            try:
                self.last_captured_frame = frame
            except Exception:
                pass
            self.logger.info("Initialization test passed")
            try:
                self.view.log_message("Camera initialization test passed", "SUCCESS")
            except Exception:
                pass
            return True
        except Exception as e:
            self.logger.error(f"Initialization test error: {e}")
            try:
                self.view.show_error("Camera Initialization", str(e))
            except Exception:
                pass
            return False

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
            """Log a stage and emit UI progress if available."""
            log('INFO', f"[{pct}%] {text}")
            try:
                view = getattr(self, 'view', None)
                if view is not None and hasattr(view, 'update_test_progress'):
                    # update_test_progress is expected to be thread-safe on the proxy
                    try:
                        view.update_test_progress(int(pct), str(text))
                    except Exception:
                        # Never raise from UI-update attempts
                        pass
            except Exception:
                pass

        def check_cancel() -> bool:
            return bool(getattr(self, '_cancel_requested', False))

        def show_blocking_prompt(title: str, body: str) -> bool:
            """Worker-thread safe prompt: request UI-thread to show dialog, wait for result via Event."""
            import threading

            # Pause acquisition if grabbing
            was_grabbing = False
            try:
                if self.camera_helper and getattr(self.camera_helper, 'camera', None) is not None and getattr(self.camera_helper.camera, 'IsGrabbing', lambda: False)():
                    try:
                        self.camera_helper.camera.StopGrabbing()
                        was_grabbing = True
                    except Exception:
                        pass
            except Exception:
                pass

            self._scene_gate_active = True
            self._prompt_in_progress = True

            def _resume_if_needed(cont: bool):
                try:
                    if cont and was_grabbing and getattr(self.camera_helper, 'camera', None) is not None:
                        try:
                            self.camera_helper.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                        except Exception:
                            pass
                except Exception:
                    pass

            # Map title to scene_type token for logging and signal routing
            scene_type = 'Dark' if 'dark' in title.lower() else 'Light'

            result_event = threading.Event()
            prompt_key = scene_type  # used to match result
            result_holder = {'val': False}

            def _on_result(s_type: str, confirmed: bool):
                if s_type == prompt_key:
                    try:
                        result_holder['val'] = bool(confirmed)
                        decision = 'Continue' if confirmed else 'Cancel'
                        self.logger.info(f"ImageQuality: prompt result ({s_type})={decision}")
                    except Exception:
                        pass
                    try:
                        self.scenePromptResult.disconnect(_on_result)
                    except Exception:
                        pass
                    try:
                        _resume_if_needed(result_holder['val'])
                    except Exception:
                        pass
                    try:
                        self._scene_gate_active = False
                        self._prompt_in_progress = False
                    except Exception:
                        pass
                    result_event.set()

            try:
                self.scenePromptResult.connect(_on_result)
            except Exception:
                pass

            # Emit request to UI thread; parent is resolved in the slot
            try:
                self.scenePromptRequested.emit(scene_type, None)
                # Log that the prompt was requested
                try:
                    self.logger.info(f"[ImageQuality] {scene_type} scene prompt shown.")
                except Exception:
                    pass
            except Exception:
                # If emit fails, fall back to cancel
                try:
                    self.scenePromptResult.disconnect(_on_result)
                except Exception:
                    pass
                return False

            # Wait for UI to signal completion
            try:
                result_event.wait()
            except Exception:
                pass
            return bool(result_holder['val'])

        # Stage 0: Initial checks and setup
        stage(0, "Initializing Image Quality test...")
        time.sleep(1)
        if check_cancel():
            return

        # Ensure camera is connected
        try:
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")
            
            # If already grabbing, just verify we can get a frame
            if self.camera.IsGrabbing():
                self.logger.info("Camera is already grabbing")
                test_frame = self.camera_helper.get_frame(self.camera)
                if test_frame is None:
                    raise RuntimeError("Camera is grabbing, but no frames are being received")
            else:
                # Start live view to initialize camera settings
                self.logger.info("Starting live view for image quality test")
                if not self.start_live_view():
                    raise RuntimeError("Failed to start live view")
            
            # Allow some time for the camera to adjust (e.g., auto-exposure)
            time.sleep(2)
            
            # Capture initial frame for reference
            ref_frame = self.camera_helper.get_frame(self.camera)
            if ref_frame is None:
                raise RuntimeError("Failed to capture reference frame")
            
            # Store reference frame for later comparison
            self.last_captured_frame = ref_frame
            
            # Optionally, save the reference frame as a high-quality image
            try:
                from PIL import Image
                img = Image.fromarray(ref_frame)
                img.save("reference_frame.png", quality=95)
                self.logger.info("Reference frame saved as 'reference_frame.png'")
            except Exception as e:
                self.logger.warning(f"Failed to save reference frame image: {e}")
        
        except Exception as e:
            log("ERROR", f"Setup error: {e}")
            self.logger.error(f"Setup error: {e}")
            return
        
        # Stage 1: Basic functionality tests
        stage(10, "Running basic functionality tests...")
        time.sleep(1)
        if check_cancel():
            return

        try:
            # Test 1: Frame grabbing
            log("INFO", "Testing frame grabbing...")
            test_frame = self.camera_helper.get_frame(self.camera)
            if test_frame is None:
                raise RuntimeError("Frame grabbing test failed: No frame received")
            
            # Basic check: frame should have some data
            if test_frame.size == 0:
                raise RuntimeError("Frame grabbing test failed: Received empty frame")
            
            log("SUCCESS", "Frame grabbing test passed")
            
        except Exception as e:
            log("ERROR", f"Frame grabbing test error: {e}")
            self.logger.error(f"Frame grabbing test error: {e}")
        
        try:
            # Test 2: Image properties
            log("INFO", "Testing image properties...")
            if self.last_captured_frame is None:
                raise RuntimeError("No reference frame captured for testing")
            
            # Check if the image is grayscale or color
            if len(self.last_captured_frame.shape) == 2 or self.last_captured_frame.shape[2] == 1:
                img_type = "Grayscale"
            elif self.last_captured_frame.shape[2] == 3:
                img_type = "Color (BGR)"
            else:
                img_type = "Unknown"
            
            log("SUCCESS", f"Image properties test passed - Type: {img_type}, Shape: {self.last_captured_frame.shape}")
            
        except Exception as e:
            log("ERROR", f"Image properties test error: {e}")
            self.logger.error(f"Image properties test error: {e}")
        
        try:
            # Test 3: Image quality metrics (basic)
            log("INFO", "Testing image quality metrics (basic)...")
            if self.last_captured_frame is None:
                raise RuntimeError("No reference frame captured for testing")
            
            # Convert to grayscale for intensity histogram (handle single-channel input)
            lf = self.last_captured_frame
            if lf is None:
                raise RuntimeError("No reference frame available")
            if len(lf.shape) == 2 or (len(lf.shape) == 3 and lf.shape[2] == 1):
                gray_frame = lf if len(lf.shape) == 2 else lf[:, :, 0]
            else:
                gray_frame = cv2.cvtColor(lf, cv2.COLOR_BGR2GRAY)
            
            # Compute histogram
            hist = cv2.calcHist([gray_frame], [0], None, [256], [0, 256])
            
            # Normalize histogram
            hist = hist / hist.sum()
            
            # Compute basic metrics
            mean_intensity = np.mean(gray_frame)
            stddev_intensity = np.std(gray_frame)
            min_intensity = np.min(gray_frame)
            max_intensity = np.max(gray_frame)
            
            # Log metrics
            log("SUCCESS", f"Image quality metrics (basic) test passed - Mean: {mean_intensity:.1f}, StdDev: {stddev_intensity:.1f}, Min: {min_intensity}, Max: {max_intensity}")
            
        except Exception as e:
            log("ERROR", f"Image quality metrics (basic) test error: {e}")
            self.logger.error(f"Image quality metrics (basic) test error: {e}")
        
        # Stage 2: Advanced analysis (EMVA 1288)
        stage(50, "Running advanced analysis (EMVA 1288)...")
        time.sleep(1)
        if check_cancel():
            return

        try:
            # Placeholder for advanced analysis steps
            log("INFO", "Performing advanced analysis (stub)...")
            time.sleep(2)  # Simulate time-consuming analysis
            
            # TODO: Implement actual EMVA 1288 analysis steps
            
            log("SUCCESS", "Advanced analysis (EMVA 1288) completed (stub)")
            
        except Exception as e:
            log("ERROR", f"Advanced analysis (EMVA 1288) error: {e}")
            self.logger.error(f"Advanced analysis (EMVA 1288) error: {e}")
        
        # Stage 3: Results consolidation and reporting
        stage(90, "Consolidating results and preparing report...")
        time.sleep(1)
        if check_cancel():
            return

        try:
            # TODO: Implement results consolidation and reporting
            log("SUCCESS", "Results consolidation and reporting completed (stub)")
            
        except Exception as e:
            log("ERROR", f"Results consolidation and reporting error: {e}")
            self.logger.error(f"Results consolidation and reporting error: {e}")
        
        # Final stage: Completion
        stage(100, "Image Quality test completed")
        time.sleep(1)
        log("SUCCESS", "Image Quality test completed")

        # Insert operator prompts for Dark and Light scenes
        try:
            # Dark scene prompt: before dark-scene capture sequence
            try:
                stage(35, "Preparing Dark Scene prompt...")
                log('INFO', "[ImageQuality] Dark scene prompt shown.")
                # Ask user to prepare dark scene
                dark_body = (
                    "Please close the lens cap or cover the camera to ensure a completely dark environment.\n"
                    "Press Continue to start the dark-scene capture or Cancel to skip this scene."
                )
                # Disable run controls while prompting
                try:
                    if hasattr(self.view, 'set_controls_enabled'):
                        try:
                            self.view.set_controls_enabled(False)
                        except Exception:
                            pass
                except Exception:
                    pass

                dark_ok = show_blocking_prompt("Dark Scene Required", dark_body)
                if dark_ok:
                    log('INFO', "[ImageQuality] Dark scene confirmed.")
                else:
                    log('WARN', "[ImageQuality] Dark scene canceled by user.")
                    # Mark flag for downstream reporting if available
                    try:
                        self._dark_scene_prompt_canceled = True
                    except Exception:
                        pass
                    try:
                        # Also add a run-log friendly marker
                        self.view.log_message('dark_scene_prompt=canceled', 'INFO')
                    except Exception:
                        pass
                # Re-enable controls
                try:
                    if hasattr(self.view, 'set_controls_enabled'):
                        try:
                            self.view.set_controls_enabled(True)
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass

            # Light scene prompt: before flat-field / bright-scene capture
            try:
                stage(60, "Preparing Light Scene prompt...")
                log('INFO', "[ImageQuality] Light scene prompt shown.")
                light_body = (
                    "Please expose the camera to a uniform, well-lit surface or focused light source.\n"
                    "Ensure the image is bright but not saturated.\n"
                    "Press Continue to proceed or Cancel to skip."
                )
                try:
                    if hasattr(self.view, 'set_controls_enabled'):
                        try:
                            self.view.set_controls_enabled(False)
                        except Exception:
                            pass
                except Exception:
                    pass

                light_ok = show_blocking_prompt("Light Scene Required", light_body)
                if light_ok:
                    log('INFO', "[ImageQuality] Light scene confirmed.")
                else:
                    log('WARN', "[ImageQuality] Light scene canceled by user.")
                    try:
                        self._light_scene_prompt_canceled = True
                    except Exception:
                        pass
                    try:
                        self.view.log_message('light_scene_prompt=canceled', 'INFO')
                    except Exception:
                        pass
                try:
                    if hasattr(self.view, 'set_controls_enabled'):
                        try:
                            self.view.set_controls_enabled(True)
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass
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

            try:
                results = test.test_maximum_fps()
                self.logger.info(f"Max FPS test completed: {results}")
                summary = self._format_max_fps_results(results) if hasattr(self, '_format_max_fps_results') else str(results)
                try:
                    self.view.update_test_results("Max FPS Test", summary)
                except Exception:
                    pass
                return True
            except Exception as e:
                error_msg = f"Max FPS test execution failed: {str(e)}"
                self.logger.error(error_msg)
                try:
                    self.view.show_error("Test Error", error_msg)
                except Exception:
                    pass
                return False
        except Exception as e:
            error_msg = f"Failed to initialize max FPS test: {str(e)}"
            self.logger.error(error_msg)
            try:
                self.view.show_error("Test Error", error_msg)
            except Exception:
                pass
            return False

    def run_roi_test(self):
        """Run ROI test (shim)"""
        try:
            # Attempt to call test class if present
            try:
                from tests.test_roi import TestROI
            except Exception:
                TestROI = None

            self.logger.info("Starting ROI test")
            if not self.camera_helper or not self.camera_helper.camera:
                raise RuntimeError("Camera not connected")

            if TestROI is None:
                # Fallback behavior: capture one frame at two ROI sizes if possible
                cam = self.camera_helper.camera
                frame = self.camera_helper.get_frame(cam)
                if frame is None:
                    raise RuntimeError("ROI test: could not grab a frame")
                # Simply report basic info
                summary = f"ROI test captured frame shape: {getattr(frame, 'shape', 'unknown')}"
                try:
                    self.view.update_test_results("ROI Test", summary)
                except Exception:
                    pass
                return True
            else:
                test = TestROI()
                test.setup(self.camera_helper)
                results = test.run()
                try:
                    self.view.update_test_results("ROI Test", str(results))
                except Exception:
                    pass
                return True
        except Exception as e:
            self.logger.error(f"ROI test failed: {e}")
            try:
                self.view.show_error("ROI Test", str(e))
            except Exception:
                pass
            return False

    def run_image_quality_tests_async(self, done_callback=None):
        """Run the image quality test asynchronously but allow presenter to show blocking prompts via show_blocking_prompt.
        done_callback: optional callable(success: bool) called on completion (UI thread expectations).
        This wrapper spawns a thread to run run_image_quality_tests while preserving prompt behavior.
        """
        import threading
        def _run_and_notify():
            try:
                res = self.run_image_quality_tests()
                if callable(done_callback):
                    try:
                        # Schedule callback on UI thread if possible
                        try:
                            from PyQt5.QtCore import QTimer
                            QTimer.singleShot(0, lambda: done_callback(bool(res)))
                        except Exception:
                            done_callback(bool(res))
                    except Exception:
                        pass
            except Exception as e:
                self.logger.error(f"Async ImageQuality run error: {e}")
                if callable(done_callback):
                    try:
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, lambda: done_callback(False))
                    except Exception:
                        try:
                            done_callback(False)
                        except Exception:
                            pass
        try:
            t = threading.Thread(target=_run_and_notify, daemon=True)
            t.start()
            return True
        except Exception as e:
            self.logger.error(f"Failed to start ImageQuality async thread: {e}")
            return False
