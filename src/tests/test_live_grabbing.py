import sys
import os
import time
import cv2
import numpy as np

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.camera_helper import CameraHelper

def test_live_grabbing():
    helper = CameraHelper()
    
    # List available cameras
    cameras = CameraHelper.enumerate_cameras()
    print(f"Found {len(cameras)} cameras:")
    for camera in cameras:
        print(f"Camera ID: {camera['id']}, Name: {camera['name']}")
    
    if not cameras:
        print("No cameras found!")
        return
    
    try:
        # Connect to the first available camera
        print("\nConnecting to camera...")
        helper.connect_camera()
        
        # Start grabbing
        print("Starting image acquisition...")
        helper.start_grabbing()
        
        # Grab 10 frames
        print("\nGrabbing 10 frames:")
        for i in range(10):
            frame = helper.get_frame()
            if frame is not None:
                print(f"Frame {i+1}: Shape={frame.shape}, Type={frame.dtype}")
                # Optional: Save a frame
                if i == 0:
                    cv2.imwrite('test_frame.png', frame)
            else:
                print(f"Frame {i+1}: Failed to grab!")
            time.sleep(0.1)  # Small delay between frames
        
        # Stop grabbing
        print("\nStopping image acquisition...")
        helper.stop_grabbing()
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        # Disconnect camera
        print("Disconnecting camera...")
        helper.disconnect_camera()

if __name__ == "__main__":
    test_live_grabbing()
