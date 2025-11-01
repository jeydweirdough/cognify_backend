# routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends, status
from core.security import allowed_users
from core.firebase import db
import asyncio
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Dict, Any

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# The Firestore collection where your daily script will save the results
PREDICTIONS_COLLECTION = "daily_predictions"
# The collection that stores the pre-calculated reports for each student
ANALYTICS_COLLECTION = "student_analytics_reports"


# --- DELETED ---
# We are removing the on-demand 'get_student_analytics_py' function.
# It is too slow and expensive for a live API.
# This calculation will now be done by the daily batch script.


# --- EXISTING ENDPOINT (Unchanged) ---
@router.get("/global_predictions")
async def get_global_pass_fail_predictions(
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Admin/Faculty] Fetches the pre-calculated global AI predictions
    from the Firestore 'daily_predictions' collection.
    """
    def _fetch_predictions():
        doc_ref = db.collection(PREDICTIONS_COLLECTION).document("latest")
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics data not found. The daily job may not have run yet.")
        return doc.to_dict()

    try:
        predictions = await asyncio.to_thread(_fetch_predictions)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT 1 DELETED ---
# We are removing the /prediction/{user_id} endpoint because
# this data will now be included in the main /report/{user_id} endpoint.


# --- UPDATED ENDPOINT 2: Renamed and now returns the full report ---
@router.get("/report/{user_id}", response_model=Dict[str, Any])
async def get_student_report(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """
    [Admin/Faculty/Student (self)] Fetches the complete, pre-calculated
    analytics report for a single student. This includes their
    performance summary, bloom-level scores, and AI pass/fail prediction.
    """
    def _fetch_student_report():
        # This is now a simple, fast, and cheap (1 read) operation.
        doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics report for this student not found. The daily job may not have run.")
        return doc.to_dict()

    try:
        # This just fetches the pre-calculated document.
        analytics_data = await asyncio.to_thread(_fetch_student_report)
        return analytics_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {e}")


# --- EXISTING ENDPOINT (Unchanged) ---
@router.post("/retrain")
async def retrain_model(
    decoded=Depends(allowed_users(["admin"]))
):
    """
    This endpoint is now optional. It's better to let the daily
    GitHub Action handle retraining.
    """
    return {"message": "Retraining is now handled automatically once per day."}

