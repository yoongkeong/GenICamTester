from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import base64
import cv2
import numpy as np
import asyncio
from datetime import datetime
from pypylon import pylon
from src.lib.camera_helper import CameraHelper

class ConnectionManager:
    def __init__(self):
        # Store active connections by camera_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, camera_id: str):
        await websocket.accept()
        if camera_id not in self.active_connections:
            self.active_connections[camera_id] = set()
        self.active_connections[camera_id].add(websocket)

    def disconnect(self, websocket: WebSocket, camera_id: str):
        self.active_connections[camera_id].remove(websocket)
        if not self.active_connections[camera_id]:
            del self.active_connections[camera_id]

    async def broadcast_to_camera(self, camera_id: str, message: dict):
        if camera_id in self.active_connections:
            for connection in self.active_connections[camera_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    await self.disconnect(connection, camera_id)

manager = ConnectionManager()

async def handle_websocket(websocket: WebSocket, camera_id: str):
    camera_helper = CameraHelper()
    streaming = False
    print(f"WebSocket connection attempt for camera {camera_id}")
    
    await manager.connect(websocket, camera_id)
    try:
        # Get all cameras
        cameras = CameraHelper.enumerate_cameras()
        target_device = None
        
        # Find the camera with matching ID
        for device in cameras:
            if device['id'] == camera_id:
                target_device = device
                break
        
        if not target_device:
            print(f"Camera {camera_id} not found in available devices: {cameras}")
            await websocket.send_json({"error": "Camera not found"})
            return
        
        print(f"Connecting to camera {camera_id}...")
        # Connect to the specific camera
        camera_helper.connect_camera(camera_id)
        print(f"Successfully connected to camera {camera_id}")
        
        while True:
            try:
                # Receive control messages from client
                data = await websocket.receive_json()
                command = data.get('command')
                
                if command == 'start_stream':
                    if not streaming:
                        print(f"Starting stream for camera {camera_id}...")
                        camera_helper.start_grabbing()
                        streaming = True
                        # Start streaming in background task
                        stream_task = asyncio.create_task(stream_frames(websocket, camera_helper))
                        await websocket.send_json({"status": "streaming_started"})
                        print(f"Stream started for camera {camera_id}")
                
                elif command == 'stop_stream':
                    if streaming:
                        print(f"Stopping stream for camera {camera_id}...")
                        camera_helper.stop_grabbing()
                        streaming = False
                        await websocket.send_json({"status": "streaming_stopped"})
                        print(f"Stream stopped for camera {camera_id}")
                
                elif command == 'get_status':
                    status_msg = {
                        "status": "streaming" if streaming else "ready",
                        "camera_id": camera_id,
                        "camera_name": target_device['name']
                    }
                    await websocket.send_json(status_msg)
                    print(f"Status sent for camera {camera_id}: {status_msg}")
            
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for camera {camera_id}")
                break
            except Exception as e:
                error_msg = str(e)
                print(f"Error in websocket handler for camera {camera_id}: {error_msg}")
                await websocket.send_json({"error": error_msg})
                break
    
    finally:
        print(f"Cleaning up connection for camera {camera_id}")
        if streaming:
            camera_helper.stop_grabbing()
        camera_helper.disconnect_camera()
        manager.disconnect(websocket, camera_id)

async def stream_frames(websocket: WebSocket, camera_helper: CameraHelper):
    """Stream frames from the camera over websocket."""
    try:
        while True:
            # Get frame from camera
            frame = camera_helper.get_frame()
            if frame is not None:
                # Convert to JPEG format
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if success:
                    # Convert to base64 and send
                    base64_image = base64.b64encode(buffer).decode('utf-8')
                    await websocket.send_json({
                        "type": "frame",
                        "data": base64_image,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    print("Failed to encode frame")
            
            # Add a small delay to control frame rate (adjust as needed)
            await asyncio.sleep(0.033)  # ~30 FPS
    except WebSocketDisconnect:
        print("WebSocket disconnected during streaming")
    except Exception as e:
        print(f"Error in stream_frames: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception as send_error:
            print(f"Error sending error message: {send_error}")

async def send_test_update(camera_id: str, test_name: str, status: str, message: str, data: dict = None):
    """Send a test update to all clients watching a specific camera"""
    await manager.broadcast_to_camera(camera_id, {
        "type": "test_update",
        "test_name": test_name,
        "status": status,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    })

async def send_camera_status(camera_id: str, status: str, message: str):
    """Send camera status updates to connected clients"""
    await manager.broadcast_to_camera(camera_id, {
        "type": "camera_status",
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })