# presenter.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer
from pypylon import pylon
import cv2
import numpy as np
import time

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
        self._init_logging()

    def _init_logging(self):
        """Initialize logging for the presenter"""
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Add console handler if not already added
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

    def detect_usb_camera(self):
        try:
            self.logger.info("Detecting USB cameras...")
            cameras = self.camera_helper.enumerate_cameras()
            self.logger.debug(f"Found cameras: {cameras}")
            
            # Look for any USB-related interface types
            usb_cameras = [cam for cam in cameras 
                         if any(usb_type in cam['interface'].lower() 
                               for usb_type in ['usb', 'baslerusb', 'genapi'])]
            self.logger.debug(f"Found USB cameras: {usb_cameras}")
            
            if not usb_cameras:
                self.logger.warning("No USB cameras found")
                QMessageBox.warning(self.view, "USB Camera Detection", "No USB cameras found.")
                return
            
            # Connect to the first USB camera
            self.logger.info(f"Connecting to USB camera: {usb_cameras[0]['id']}")
            self.camera_helper.connect_camera(usb_cameras[0]['id'])
            camera_info = (
                f"Camera detected:\nSerial Number: {usb_cameras[0]['id']}\n"
                f"Model: {usb_cameras[0]['name']}\n"
                f"Interface: {usb_cameras[0]['interface']}\n"
                f"Full Name: {usb_cameras[0].get('full_name', 'N/A')}"
            )
            self.view.display_camera_info(camera_info)
            self.view.navigate_to_test_selection()
            
        except Exception as e:
            self.logger.error(f"USB camera detection error: {str(e)}")
            QMessageBox.critical(self.view, "Error", f"Failed to connect to USB camera: {str(e)}")

    def detect_gige_camera(self, use_dhcp=True, ip_settings=None):
        try:
            self.logger.info("Detecting GigE cameras...")
            cameras = self.camera_helper.enumerate_cameras()
            self.logger.debug(f"Found cameras: {cameras}")
            
            gige_cameras = [cam for cam in cameras if 'GigE' in cam['interface']]
            self.logger.debug(f"Found GigE cameras: {gige_cameras}")
            
            if not gige_cameras:
                self.logger.warning("No GigE cameras found")
                QMessageBox.warning(self.view, "GigE Camera Detection", "No GigE cameras found.")
                return
            
            # Connect to the first GigE camera
            self.logger.info(f"Connecting to GigE camera: {gige_cameras[0]['id']}")
            self.camera_helper.connect_camera(gige_cameras[0]['id'])
            camera_info = (
                f"Camera detected:\nSerial Number: {gige_cameras[0]['id']}\n"
                f"Model: {gige_cameras[0]['name']}\n"
                f"Interface: {gige_cameras[0]['interface']}\n"
                f"IP Address: {gige_cameras[0].get('ip_address', 'N/A')}\n"
                f"Full Name: {gige_cameras[0].get('full_name', 'N/A')}"
            )
            self.view.display_camera_info(camera_info)
            self.view.navigate_to_test_selection()
            
        except Exception as e:
            self.logger.error(f"GigE camera detection error: {str(e)}")
            QMessageBox.critical(self.view, "Error", f"Failed to connect to GigE camera: {str(e)}")

    def start_live_grabbing(self):
        """Start live image grabbing"""
        try:
            if not self.is_live_grabbing:
                self.logger.info("Starting live grabbing")
                if not self.camera_helper:
                    raise RuntimeError("Camera helper not initialized")
                self.camera_helper.start_grabbing()
                self.is_live_grabbing = True
                
                # Create timer for live view updates
                self.live_timer = QTimer()
                self.live_timer.timeout.connect(self.update_live_view)
                self.live_timer.start(33)  # ~30 FPS
                
                self.view.update_live_button_state(True)
        except Exception as e:
            self.logger.error(f"Failed to start live grabbing: {str(e)}")
            QMessageBox.critical(self.view, "Error", f"Failed to start live grabbing: {str(e)}")
            self.stop_live_grabbing()

    def stop_live_grabbing(self):
        """Stop live image grabbing"""
        try:
            if self.is_live_grabbing:
                self.logger.info("Stopping live grabbing")
                if self.live_timer:
                    self.live_timer.stop()
                    self.live_timer = None
                
                if self.camera_helper:
                    self.camera_helper.stop_grabbing()
                self.is_live_grabbing = False
                self.view.update_live_button_state(False)
        except Exception as e:
            self.logger.error(f"Failed to stop live grabbing: {str(e)}")
            QMessageBox.critical(self.view, "Error", f"Failed to stop live grabbing: {str(e)}")

    def update_live_view(self):
        """Update the live view with the latest frame"""
        try:
            if self.is_live_grabbing and self.camera_helper:
                frame = self.camera_helper.get_frame()
                if frame is not None:
                    self.view.update_live_image(frame)
        except Exception as e:
            self.logger.error(f"Error updating live view: {str(e)}")
            self.stop_live_grabbing()

    def start_long_run_test(self):
        """Start long run test with live frame grabbing"""
        try:
            self.logger.info("Starting long run test")
            self.view.log_message("Starting long run test")
            self.is_long_run_test = True
            self.long_run_start_time = time.time()
            self.long_run_frame_count = 0
            self.long_run_last_fps_update = time.time()
            self.long_run_last_frame_count = 0
            
            # Start grabbing if not already grabbing
            if self.camera_helper and not self.camera_helper.camera.IsGrabbing():
                self.camera_helper.start_grabbing()
                
        except Exception as e:
            self.logger.error(f"Error starting long run test: {str(e)}")
            self.view.log_message(f"Error starting long run test: {str(e)}", "ERROR")
            
    def stop_long_run_test(self):
        """Stop long run test"""
        try:
            self.logger.info("Stopping long run test")
            self.view.log_message("Long run test stopped")
            self.is_long_run_test = False
            if self.camera_helper:
                self.camera_helper.stop_grabbing()
                
            # Log final statistics
            stats = self.get_long_run_stats()
            self.view.log_message(
                f"Test completed - Total frames: {stats['frames_captured']:,}, "
                f"Average FPS: {stats['average_fps']:.1f}")
                
        except Exception as e:
            self.logger.error(f"Error stopping long run test: {str(e)}")
            self.view.log_message(f"Error stopping long run test: {str(e)}", "ERROR")
            
    def get_long_run_stats(self):
        """Get current statistics for long run test"""
        try:
            current_time = time.time()
            elapsed = current_time - self.long_run_start_time
            
            # Calculate current FPS over the last second
            frames_since_last = self.long_run_frame_count - self.long_run_last_frame_count
            time_since_last = current_time - self.long_run_last_fps_update
            current_fps = frames_since_last / time_since_last if time_since_last > 0 else 0
            
            # Calculate average FPS
            average_fps = self.long_run_frame_count / elapsed if elapsed > 0 else 0
            
            # Update last values
            self.long_run_last_fps_update = current_time
            self.long_run_last_frame_count = self.long_run_frame_count
            
            # Log progress every minute
            if int(elapsed) % 60 == 0:
                self.view.log_message(
                    f"Long run test progress - Frames: {self.long_run_frame_count:,}, "
                    f"Current FPS: {current_fps:.1f}")
            
            return {
                "elapsed_time": elapsed,
                "frames_captured": self.long_run_frame_count,
                "current_fps": current_fps,
                "average_fps": average_fps
            }
        except Exception as e:
            self.logger.error(f"Error getting long run stats: {str(e)}")
            return {}

    def get_current_frame(self):
        """Get the current frame from the camera"""
        try:
            if self.camera_helper and self.camera_helper.camera:
                frame = self.camera_helper.get_frame(increment_count=self.is_long_run_test)
                if frame is not None:
                    # If this is part of a long run test, increment the frame counter
                    if self.is_long_run_test:
                        self.long_run_frame_count += 1
                return frame
            return None
        except Exception as e:
            self.logger.error(f"Error getting current frame: {str(e)}")
            return None

    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources")
        self.stop_live_grabbing()
        if self.camera_helper:
            self.camera_helper.disconnect_camera()
