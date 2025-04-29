from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
from datetime import datetime

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
    await manager.connect(websocket, camera_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any incoming messages from clients if needed
            # Currently just echo back
            await websocket.send_json({
                "type": "echo",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, camera_id)

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