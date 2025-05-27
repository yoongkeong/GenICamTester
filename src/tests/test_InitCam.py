# test_InitCam.py
import sys
import os
from datetime import datetime
from src.lib.camera_helper import CameraHelper

class test_InitCam:
    def __init__(self):
        self.camera_helper = None
        
    def run(self, camera_id: str, parameters: dict = None):
        """Run the camera initialization test
        
        Args:
            camera_id (str): The ID of the camera to test
            parameters (dict, optional): Additional test parameters. Defaults to None.
            
        Returns:
            dict: Test results containing success status and details
        """
        try:
            self.camera_helper = CameraHelper()
            
            # Get all cameras
            cameras = CameraHelper.enumerate_cameras()
            target_device = None
            
            # Find the camera with matching ID
            for device in cameras:
                if device['id'] == camera_id:
                    target_device = device
                    break
            
            if not target_device:
                return {
                    "success": False,
                    "error": f"Camera {camera_id} not found",
                    "details": {
                        "available_cameras": cameras
                    }
                }
            
            # Connect to camera
            print(f"Connecting to camera {camera_id}...")
            self.camera_helper.connect_camera(camera_id)
            
            # Verify camera is open
            if not self.camera_helper.camera.IsOpen():
                return {
                    "success": False,
                    "error": "Camera failed to initialize",
                    "details": {
                        "camera_id": camera_id,
                        "device_info": target_device
                    }
                }
            
            # Get camera info
            camera_info = {
                "vendor": self.camera_helper.camera.GetDeviceInfo().GetVendorName(),
                "model": self.camera_helper.camera.GetDeviceInfo().GetModelName(),
                "serial": self.camera_helper.camera.GetDeviceInfo().GetSerialNumber(),
                "firmware": self.camera_helper.camera.GetDeviceInfo().GetFirmwareVersion()
            }
            
            return {
                "success": True,
                "message": "Camera initialized successfully",
                "details": {
                    "camera_id": camera_id,
                    "device_info": camera_info,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "camera_id": camera_id,
                    "exception_type": type(e).__name__
                }
            }
        finally:
            if self.camera_helper:
                self.camera_helper.disconnect_camera()
