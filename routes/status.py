import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from database.firestore import db
from datetime import datetime, timedelta
from core.config import settings

router = APIRouter(prefix="/status", tags=["User Status"])

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

async def check_offline_users():
    """Mark users as offline if they haven't been seen in 45 seconds"""
    def _check_db():
        try:
            # Get all online users
            users = db.collection("user_profiles").where("status", "in", ["online", "busy"]).stream()
            
            # Current time minus 45 seconds
            cutoff = datetime.utcnow() - timedelta(seconds=45)
            
            for user in users:
                data = user.to_dict()
                last_seen = data.get("last_seen")
                
                # Convert Firestore timestamp to datetime if needed
                if hasattr(last_seen, "timestamp"):
                    last_seen = datetime.fromtimestamp(last_seen.timestamp())
                
                # If user hasn't sent a heartbeat recently, mark as offline
                if last_seen and last_seen < cutoff:
                    user.reference.update({
                        "status": "offline",
                        "last_seen": datetime.utcnow()
                    })
                    print(f"Marked {user.id} as offline (no recent heartbeat)")
                    
        except Exception as e:
            print(f"Error checking offline status: {e}")
    
    await asyncio.to_thread(_check_db)

@router.post("/heartbeat")
async def heartbeat(payload: Dict[str, str]):
    """Accept heartbeat from client and update last_seen"""
    uid = payload.get("uid")
    if not uid:
        return JSONResponse({"error": "uid required"}, status_code=400)
    
    await update_user_status(uid, "online")
    await check_offline_users()  # Update offline status for users without recent heartbeats
    return JSONResponse({"status": "ok"})

@router.post("/set")
async def set_status(payload: Dict[str, str]):
    """Set user status (online/busy/offline)"""
    uid = payload.get("uid")
    status = payload.get("status")
    
    if not uid or not status:
        return JSONResponse({"error": "uid and status required"}, status_code=400)
    
    if status not in ["online", "busy", "offline"]:
        return JSONResponse({"error": "invalid status"}, status_code=400)
    
    await update_user_status(uid, status)
    await check_offline_users()  # Update offline status for users without recent heartbeats
    return JSONResponse({"status": "ok"})

@router.get("/check")
async def check_status():
    """Endpoint that runs offline status check manually"""
    await check_offline_users()
    return JSONResponse({"status": "ok"})


# HTTP fallback endpoints for polling-based status updates
@router.post("/heartbeat")
async def heartbeat(payload: Dict[str, str]):
    """Accepts a heartbeat payload like {"uid": "user123"} and updates last_seen only."""
    uid = payload.get("uid")
    if not uid:
        return JSONResponse({"error": "uid required"}, status_code=400)

    await update_user_status(uid, "online")
    return JSONResponse({"status": "ok"})


@router.post("/set")
async def set_status(payload: Dict[str, str]):
    """Set explicit status e.g. {"uid": "user123", "status": "busy"}"""
    uid = payload.get("uid")
    status = payload.get("status")
    if not uid or not status:
        return JSONResponse({"error": "uid and status required"}, status_code=400)

    if status not in ["online", "busy", "offline"]:
        return JSONResponse({"error": "invalid status"}, status_code=400)

    await update_user_status(uid, status)
    return JSONResponse({"status": "ok"})