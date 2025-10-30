from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List
from services.analytics_service import get_student_analytics, generate_all_student_features
from core.security import allowed_users
import joblib
import pandas as pd
import os

# --- (No firebase imports needed) ---
# --- We will need settings for the fallback path ---
from core.config import settings

# --- Import train function ---
from ml.train_model import train 

router = APIRouter(prefix="/analytics", tags=["Analytics & AI"])

# --- AI Model is loaded into this global variable ---
model = None

@router.on_event("startup")
def load_model():
    """
    Load the ML model on startup.
    Loads the 'fallback' model bundled with the repo.
    """
    global model
    try:
        # Load the local fallback file
        if os.path.exists(settings.MODEL_FALLBACK_PATH):
            model = joblib.load(settings.MODEL_FALLBACK_PATH)
            print(f"✅ AI model loaded from local fallback: {settings.MODEL_FALLBACK_PATH}")
        else:
            print(f"❌ ERROR: No model found in local fallback path: {settings.MODEL_FALLBACK_PATH}")
            print("Predictions will be disabled.")
            model = None
            
    except Exception as e:
        print(f"⚠️ Warning: Could not load model from local file. Error: {e}")
        model = None

# --- Endpoint 1: Individual Analytics ---
@router.get("/student/{student_id}", dependencies=[Depends(allowed_users(["admin", "faculty_member", "student"]))])
async def get_analytics_for_student(student_id: str, decoded=Depends(allowed_users(["admin", "faculty_member", "student"]))):
    """
    Get the descriptive analytics (strengths, weaknesses, etc.) for
    a single student.
    """
    if decoded.get("role") == "student" and decoded.get("uid") != student_id:
        raise HTTPException(status_code=403, detail="Students can only view their own analytics.")
        
    analytics = await get_student_analytics(student_id)
    if not analytics or analytics["summary"]["total_activities"] == 0:
        raise HTTPException(status_code=404, detail="No analytics found for this student.")
    
    return analytics

# --- Endpoint 2: Global AI Predictions ---
@router.get("/global_predictions", dependencies=[Depends(allowed_users(["admin", "faculty_member"]))])
async def get_global_pass_fail_predictions():
    """
    [Admin/Faculty Only] Runs the AI model on all current students
    to predict who will pass and who will fail.
    """
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="AI model is not loaded. Run the training script first.")
        
    features_df = await generate_all_student_features()
    if features_df.empty:
        raise HTTPException(status_code=404, detail="No student data found to predict on.")

    student_ids = features_df['student_id']
    X_live = features_df.drop(columns=['student_id', 'overall_score'], errors='ignore')
    
    model_columns = model.feature_names_in_
    X_live = X_live.reindex(columns=model_columns, fill_value=0)
    
    predictions = model.predict(X_live)
    probabilities = model.predict_proba(X_live)[:, 1] 
    
    results = []
    for i, student_id in enumerate(student_ids):
        results.append({
            "student_id": student_id,
            "predicted_to_pass": bool(predictions[i]),
            "pass_probability": round(probabilities[i] * 100, 2)
        })

    total_pass = sum(predictions)
    total_students = len(results)
    
    return {
        "summary": {
            "total_students_predicted": total_students,
            "count_predicted_to_pass": int(total_pass),
            "count_predicted_to_fail": int(total_students - total_pass),
            "predicted_pass_rate": round((total_pass / total_students) * 100, 2) if total_students > 0 else 0
        },
        "predictions": results
    }

# --- NEW: Endpoint 3: Dynamic Re-training (In-Memory) ---
@router.post("/retrain", dependencies=[Depends(allowed_users(["admin"]))])
async def retrain_model(background_tasks: BackgroundTasks):
    """
    [Admin Only] Triggers a full model retrain in the background.
    The new model is loaded into server memory (it is NOT saved to a file).
    """
    
    async def run_training_in_background():
        """Wrapper to run async train and update global model."""
        global model
        print("--- BACKGROUND TASK: Starting model retrain... ---")
        new_model = await train() # This runs the full training
        if new_model:
            model = new_model # Update the live server's model in memory
            print("--- BACKGROUND TASK: Model retrain complete. New model is live in memory. ---")
        else:
            print("--- BACKGROUND TASK: Model retrain failed. Old model is still in use. ---")

    background_tasks.add_task(run_training_in_background)
    
    return {"message": "Model training started in background. New model will be live in memory shortly."}

