# routes/analytics.py
from fastapi import APIRouter, HTTPException, Depends
from core.security import allowed_users
from core.firebase import db
import asyncio

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# The Firestore collection where your daily script will save the results
PREDICTIONS_COLLECTION = "daily_predictions"

@router.get("/global_predictions")
async def get_global_pass_fail_predictions(
    decoded=Depends(allowed_users(["admin", "faculty_member"]))
):
    """
    [Vercel API] Fetches the pre-calculated AI predictions
    from the Firestore 'daily_predictions' collection.
    This endpoint is now fast and lightweight.
    """
    def _fetch_predictions():
        doc_ref = db.collection(PREDICTIONS_COLLECTION).document("latest")
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Analytics data not found. The daily job may not have run yet.")
        return doc.to_dict()

    try:
        # Use asyncio.to_thread to avoid blocking
        predictions = await asyncio.to_thread(_fetch_predictions)
        return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# The /student/{student_id} endpoint is removed
# because that logic is now part of the daily batch job.

@router.post("/retrain")
async def retrain_model(
    decoded=Depends(allowed_users(["admin"]))
):
    """
    This endpoint is now optional. It's better to let the daily
    GitHub Action handle retraining.
    """
    return {"message": "Retraining is now handled automatically once per day."}