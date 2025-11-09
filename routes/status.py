# routes/status.py
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict
from datetime import datetime, timedelta
from utils.status_utils import update_user_status, check_offline_users


router = APIRouter(prefix="/status", tags=["User Status"])

@router.post("/heartbeat")
async def heartbeat(payload: Dict[str, str]):
    """
    Accept heartbeat from client and update last_seen.
    This is used for passive tab-open detection.
    """
    uid = payload.get("uid")
    if not uid:
        return JSONResponse({"error": "uid required"}, status_code=400)
    
    # --- 2. Call the imported function ---
    await update_user_status(uid, "online")
    # --- 3. REMOVED the inefficient call to check_offline_users() ---
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
    
    # --- 4. Call the imported function ---
    await update_user_status(uid, status)
    # --- 5. REMOVED the inefficient call to check_offline_users() ---
    return JSONResponse({"status": "ok"})

@router.get("/check_offline")
async def check_status():
    """
    (For Schedulers) Endpoint that runs offline status check manually.
    This should be called by a cron job, not the frontend.
    """
    await check_offline_users()
    return JSONResponse({"status": "ok"})