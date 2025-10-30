import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from core.firebase import db
from datetime import datetime, timedelta
from core.config import settings
# --- FIX: Import FieldFilter ---
from google.cloud.firestore_v1.base_query import FieldFilter

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
            user_ref.set(update_data, merge=True)
            print(f"Updated status for {uid} to {status}")
        except Exception as e:
            print(f"Error updating status for {uid}: {e}")
    
    await asyncio.to_thread(_update_db)

async def check_offline_users():
    """Mark users as offline if they haven't been seen in 45 seconds"""
    def _check_db():
        try:
            # --- FIX: Added the 'filter=' keyword to the query ---
            users = db.collection("user_profiles").where(
                filter=FieldFilter("status", "in", ["online", "busy"])
            ).stream()
            
            cutoff = datetime.utcnow() - timedelta(seconds=45)
            
            for user in users:
                data = user.to_dict()
                last_seen = data.get("last_seen")
                
                if hasattr(last_seen, "timestamp"):
                    last_seen = datetime.fromtimestamp(last_seen.timestamp())
                
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