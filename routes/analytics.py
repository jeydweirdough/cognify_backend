# routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends
from core.security import allowed_users
from core.firebase import db
import asyncio
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# The Firestore collection where your daily script saves the *global* report
PREDICTIONS_COLLECTION = "daily_predictions"
# The Firestore collection where your daily script saves the *individual* reports
STUDENT_ANALYTICS_COLLECTION = "student_analytics_reports"


@router.get("/global_predictions")
async def get_global_pass_fail_predictions(
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Fetches the pre-calculated GLOBAL AI predictions
    from the 'daily_predictions' collection for the main dashboard.
    This is fast and efficient (1 read).
    """
    def _fetch_predictions():
        doc_ref = db.collection(PREDICTIONS_COLLECTION).document("latest")
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Global analytics data not found. The daily job may not have run yet.")
        return doc.to_dict()

    try:
        predictions = await asyncio.to_thread(_fetch_predictions)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student_report/{user_id}")
async def get_student_analytics_report(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """
    [Student/Faculty/Admin] Fetches the pre-calculated, combined analytics 
    and AI prediction report for a SINGLE student.
    
    This fulfills the "Progress and Report Module" from your manuscript.
    It is fast and efficient (1 read).
    """
    caller_role = decoded.get("role")
    caller_uid = decoded.get("uid")

    # Students can only view their own report
    if caller_role == "student" and user_id != caller_uid:
        raise HTTPException(status_code=403, detail="You may only view your own analytics report.")

    def _fetch_student_report():
        doc_ref = db.collection(STUDENT_ANALYTICS_COLLECTION).document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Analytics report not found for user {user_id}. The daily job may not have run yet.")
        
        report = doc.to_dict()
        
        # Ensure the report has all key parts, provide defaults if not
        return {
            "student_id": report.get("student_id", user_id),
            "summary": report.get("summary", {}),
            "performance_by_bloom": report.get("performance_by_bloom", {}),
            "prediction": report.get("prediction", {}),
            "ai_motivation": report.get("ai_motivation", "Keep up the hard work!"),
            "last_updated": report.get("last_updated")
        }

    try:
        report = await asyncio.to_thread(_fetch_student_report)
        return report
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

