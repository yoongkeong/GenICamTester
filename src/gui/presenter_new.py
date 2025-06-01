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
                return
                
            if not self.camera.IsOpen():
                error_msg = "Cannot start live view: Camera is not open"
                self.logger.error(error_msg)
                self.view.log_message(error_msg, "ERROR")
                return

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
                return
                
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
                return
                
            self.is_live_grabbing = True
            self.logger.info("Live view started successfully")
            self.view.log_message("Live view started", "SUCCESS")
            
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

    # ... Rest of the presenter class implementation ...
