# routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends
from core.security import allowed_users
import asyncio
from typing import Dict, Any
from datetime import datetime

# --- 1. Import all our new service functions ---
from services import analytics_service 

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# --- 2. RE-ADD THE GLOBAL PREDICTIONS ENDPOINT ---
@router.get("/global_predictions")
async def get_global_pass_fail_predictions(
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Fetches a LIVE, logic-based GLOBAL prediction
    report for the main dashboard.
    
    NOTE: This is a heavy, on-demand calculation.
    """
    try:
        global_report = await analytics_service.get_global_analytics_report()
        global_report["last_updated"] = datetime.utcnow().isoformat()
        return global_report
    except Exception as e:
        print(f"Error generating global report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. UPDATE THE STUDENT REPORT ENDPOINT ---
@router.get("/student_report/{user_id}")
async def get_student_analytics_report(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """
    [Student/Faculty/Admin] Fetches a LIVE, on-demand analytics 
    report for a SINGLE student.
    
    This report now includes a simple, logic-based pass/fail
    prediction (not AI).
    """
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    # Students can only view their own report
    if caller_role == "student" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only view your own analytics report.")

    try:
        # 1. Get the live analytics (summary & bloom)
        analytics_data = await analytics_service.get_live_analytics(user_id)
        
        # 2. Apply our simple prediction algorithm
        report_with_prediction = analytics_service.apply_prediction_logic(analytics_data)
        
        # 3. Return the combined report
        return {
            "student_id": user_id,
            "summary": report_with_prediction.get("summary", {}),
            "performance_by_bloom": report_with_prediction.get("performance_by_bloom", {}),
            "prediction": report_with_prediction.get("prediction", {}), # <-- This is now included
            "last_updated": datetime.utcnow().isoformat() # Report is live
        }
    except Exception as e:
        print(f"Error generating live report for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))