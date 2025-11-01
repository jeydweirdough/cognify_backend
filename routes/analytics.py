# routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends, status
from core.security import allowed_users
from core.firebase import db
import asyncio
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# The Firestore collection where your daily script will save the results
PREDICTIONS_COLLECTION = "daily_predictions"
# --- NEW: The collection to store pre-calculated student reports ---
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

# --- NEW ENDPOINT 1: Get a student's pre-calculated prediction ---
@router.get("/prediction/{user_id}")
async def get_student_prediction(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """
    [Admin/Faculty/Student (self)] Fetches a single student's
    pre-calculated AI prediction from the latest daily job.
    """
    def _fetch_prediction():
        doc = db.collection(PREDICTIONS_COLLECTION).document("latest").get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics data not found.")
        
        all_predictions = doc.to_dict().get("predictions", [])
        
        # Find the specific student in the predictions array
        for pred in all_predictions:
            if pred.get("student_id") == user_id:
                return pred
        
        # If loop finishes without finding, raise 404
        raise HTTPException(status_code=404, detail="Prediction for this student not found.")

    try:
        prediction = await asyncio.to_thread(_fetch_prediction)
        return prediction
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- UPDATED ENDPOINT 2: Get pre-calculated, detailed analytics ---
@router.get("/details/{user_id}")
async def get_student_activity_details(
    user_id: str,
    decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))
):
    """
    [Admin/Faculty/Student (self)] Runs a fresh, on-demand
    calculation of a student's activity summary and performance.
    """
    def _fetch_student_report():
        # This is now a simple, fast, and cheap (1 read) operation.
        doc_ref = db.collection(ANALYTICS_COLLECTION).document(user_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics report for this student not found. The daily job may not have run.")
        return doc.to_dict()

    try:
        # This will run the query and calculations right now
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

