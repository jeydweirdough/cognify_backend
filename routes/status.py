import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from database.firestore import db
from datetime import datetime

router = APIRouter(prefix="/status", tags=["User Status"])

# This class will keep track of all active users
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"User {user_id} connected.")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"User {user_id} disconnected.")

manager = ConnectionManager()


# This helper function updates Firestore
async def update_user_status(uid: str, status: str):
    """Updates the user's status and last_seen time in Firestore."""
    def _update_db():
        try:
            user_ref = db.collection("user_profiles").document(uid)
            update_data = {
                "status": status,
                "last_seen": datetime.utcnow()
            }
            # Use set with merge=True to create the fields if they don't exist
            user_ref.set(update_data, merge=True)
            print(f"Updated status for {uid} to {status}")
        except Exception as e:
            print(f"Error updating status for {uid}: {e}")
    
    # Run the blocking database call in a separate thread
    await asyncio.to_thread(_update_db)


# This is the new WebSocket endpoint
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    await update_user_status(user_id, "online")

    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            
            if data.get("type") == "set_status":
                new_status = data.get("status") # e.g., "busy" or "online"
                if new_status in ["busy", "online"]:
                    await update_user_status(user_id, new_status)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await update_user_status(user_id, "offline")
    except Exception as e:
        print(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)
        await update_user_status(user_id, "offline")