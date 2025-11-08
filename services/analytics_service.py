# services/analytics_service.py
import pandas as pd
from typing import Dict, Any, List, Tuple
from services import activity_service, profile_service
from core.firebase import db
from google.cloud.firestore_v1.base_query import FieldFilter
import asyncio

# --- 1. DEFINE OUR SIMPLE ALGORITHM ---
# We can easily change this "passing score" later
PASSING_THRESHOLD = 75.0

async def get_live_analytics(student_id: str) -> Dict[str, Any]:
    """
    Calculates a student's analytics report (summary and performance)
    on-demand by fetching their live activity data.
    """
    
    # 1. Fetch all non-deleted activities for the student
    activities_list, _ = await activity_service.where(
        "user_id", "==", student_id,
        limit=1000  # Fetch a large number of activities for a full report
    )
    
    if not activities_list:
        return {
            "summary": {
                "overall_score": 0.0, 
                "total_activities": 0, 
                "time_spent_sec": 0
            },
            "performance_by_bloom": {}
        }

    # 2. Convert to DataFrame for easy analysis
    activities_data = [act.model_dump() for act in activities_list]
    df = pd.DataFrame(activities_data)
    
    # Ensure numeric types, fill missing with 0
    df['score'] = pd.to_numeric(df.get('score'), errors='coerce').fillna(0.0)
    df['duration'] = pd.to_numeric(df.get('duration'), errors='coerce').fillna(0.0)
    
    # 3. Calculate Bloom's performance
    bloom_performance = df.groupby('bloom_level')['score'].mean()
    
    # --- FIX: Cast numpy.float64 to native Python float ---
    bloom_dict = {level: float(round(score, 2)) for level, score in bloom_performance.items()}
    
    # 4. Calculate summary
    # --- FIX: Cast all numpy types (int64, float64) to native Python types ---
    summary = {
        "total_activities": int(len(df)),
        "overall_score": float(round(df['score'].mean(), 2)),
        "time_spent_sec": int(df['duration'].sum())
    }
    
    return {
        "summary": summary, 
        "performance_by_bloom": bloom_dict
    }

# --- 2. NEW FUNCTION TO APPLY OUR LOGIC ---
def apply_prediction_logic(analytics_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies the simple pass/fail algorithm to an analytics report.
    """
    overall_score = analytics_data.get("summary", {}).get("overall_score", 0.0)
    
    # The Algorithm:
    is_passing = overall_score >= PASSING_THRESHOLD
    
    # --- FIX: Cast numpy.bool_ to native Python bool ---
    analytics_data["prediction"] = {
        "predicted_to_pass": bool(is_passing),
        "pass_probability": float(100.0 if is_passing else 0.0), # Simple logic
        "overall_score": float(overall_score)
    }
    # --- END FIX ---
    return analytics_data

# --- 3. NEW FUNCTION TO GET THE GLOBAL REPORT ---
async def get_global_analytics_report() -> Dict[str, Any]:
    """
    Generates a live global report for all students.
    This is a heavy operation and should be cached by the frontend.
    """
    
    def _fetch_all_student_data_sync() -> List[Dict[str, Any]]:
        # This is a fast, efficient way to get all student IDs
        # We query 'roles' to find the student role_id first
        roles_query = db.collection("roles").where(
            filter=FieldFilter("designation", "==", "student")
        ).limit(1).stream()
        
        student_role_id = None
        for doc in roles_query:
            student_role_id = doc.id
            
        if not student_role_id:
            print("Error: 'student' role not found in DB.")
            return []

        # Now get all profiles with that role_id
        profiles_query = db.collection("user_profiles").where(
            filter=FieldFilter("role_id", "==", student_role_id)
        ).where(
            filter=FieldFilter("deleted", "!=", True)
        ).stream()
        
        return [{"id": doc.id, **doc.to_dict()} for doc in profiles_query]

    # Run the DB query in a thread
    all_students = await asyncio.to_thread(_fetch_all_student_data_sync)
    
    # Now, get analytics for each student (concurrently)
    tasks = [get_live_analytics(student.get("id")) for student in all_students]
    all_analytics_results = await asyncio.gather(*tasks)
    
    # --- Build the final global report ---
    total_students = 0
    total_pass = 0
    predictions_list = []
    
    for i, analytics_data in enumerate(all_analytics_results):
        student = all_students[i]
        
        # Apply our simple algorithm
        report_with_prediction = apply_prediction_logic(analytics_data)
        
        # Add to lists
        total_students += 1
        if report_with_prediction["prediction"]["predicted_to_pass"]:
            total_pass += 1
            
        # --- FIX: Ensure all values added to the list are native Python types ---
        predictions_list.append({
            "student_id": student.get("id"),
            "first_name": student.get("first_name"),
            "last_name": student.get("last_name"),
            "predicted_to_pass": bool(report_with_prediction["prediction"]["predicted_to_pass"]),
            "overall_score": float(report_with_prediction["summary"]["overall_score"])
        })
        # --- END FIX ---
        
    # --- FIX: Cast summary values to native Python types ---
    return {
        "summary": {
            "total_students_predicted": int(total_students),
            "count_predicted_to_pass": int(total_pass),
            "count_predicted_to_fail": int(total_students - total_pass),
            "predicted_pass_rate": float(round((total_pass / total_students) * 100, 2)) if total_students > 0 else 0.0
        },
        "predictions": predictions_list
    }
    # --- END FIX ---