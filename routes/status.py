import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Optional
from database.firestore import db
from datetime import datetime
from core.config import settings
from starlette.websockets import WebSocketState

router = APIRouter(prefix="/status", tags=["User Status"])

# This class will keep track of all active users
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.ping_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            print(f"User {user_id} connected.")
            
            # Start ping task for this connection
            self.ping_tasks[user_id] = asyncio.create_task(self._keep_alive(websocket, user_id))
        except Exception as e:
            print(f"Error connecting user {user_id}: {e}")
            raise

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
            # Cancel ping task if it exists
            if user_id in self.ping_tasks:
                self.ping_tasks[user_id].cancel()
                del self.ping_tasks[user_id]
                
            print(f"User {user_id} disconnected.")

    async def _keep_alive(self, websocket: WebSocket, user_id: str):
        """Send periodic pings to keep the connection alive"""
        try:
            while True:
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break
                    
                await asyncio.sleep(settings.WS_PING_INTERVAL)
                try:
                    await websocket.send_text('ping')
                except Exception as e:
                    print(f"Error sending ping to {user_id}: {e}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Keep-alive error for {user_id}: {e}")
        finally:
            self.disconnect(user_id)

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


# Health check endpoint for WebSocket
@router.get("/ws/health")
async def websocket_health():
    return JSONResponse({"status": "ok"})

# WebSocket endpoint
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    try:
        await manager.connect(websocket, user_id)
        await update_user_status(user_id, "online")

        while True:
            try:
                # Set a timeout for receiving messages
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.WS_PING_TIMEOUT
                )
                
                if data.get("type") == "set_status":
                    new_status = data.get("status")
                    if new_status in ["busy", "online"]:
                        await update_user_status(user_id, new_status)
                elif data.get("type") == "pong":
                    # Handle pong response
                    continue

            except asyncio.TimeoutError:
                # Check if client is still connected
                try:
                    await websocket.send_text("ping")
                except:
                    raise WebSocketDisconnect()
            
            except WebSocketDisconnect:
                raise

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for {user_id}")
        manager.disconnect(user_id)
        await update_user_status(user_id, "offline")
        
    except Exception as e:
        print(f"WebSocket error for {user_id}: {str(e)}")
        manager.disconnect(user_id)
        await update_user_status(user_id, "offline")
        
    finally:
        # Ensure cleanup happens
        try:
            manager.disconnect(user_id)
            await update_user_status(user_id, "offline")
        except:
            pass