# services/analytics_service.py
import pandas as pd
from core.firebase import db
from services import (
    activity_service, 
    module_service, 
    quiz_service, 
    profile_service
)
from database.models import Activity
from typing import Dict, Any, List
from .role_service import get_role_id_by_designation 
from google.cloud.firestore_v1.base_query import FieldFilter # Import FieldFilter

async def get_student_analytics(student_id: str) -> Dict[str, Any]:
    # ... (rest of this function is fine) ...
    """
    Calculates a student's strengths, weaknesses, and topic performance
    based on their activities.
    """
    
    # 1. Get all of the student's activities (quiz scores, etc.)
    # --- THIS IS THE FIX ---
    activities = await activity_service.where("user_id", "==", student_id)
    
    if not activities:
        return {
            "summary": {"total_activities": 0, "overall_score": 0, "time_spent_sec": 0},
            "strengths": [], "weaknesses": [],
            "performance_by_bloom": [], "performance_by_topic": []
        }

    # 2. Convert to a Pandas DataFrame for easy analysis
    activities_data = [act.model_dump() for act in activities]
    df = pd.DataFrame(activities_data)
    
    # Check if 'score' column exists and is numeric, fill with 0 otherwise
    if 'score' not in df.columns or not pd.api.types.is_numeric_dtype(df['score']):
        df['score'] = 0.0
    else:
        df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0.0)
        
    # 3. Calculate "Strengths vs. Weaknesses" (by Bloom's Level)
    if 'bloom_level' in df.columns:
        # Ensure bloom_level is treated as string and handle potential None values
        df['bloom_level'] = df['bloom_level'].fillna('unknown')
        bloom_performance = df.groupby('bloom_level')['score'].mean().reset_index()
        bloom_performance = bloom_performance.round(2)
        strengths = bloom_performance[bloom_performance['score'] >= 80]['bloom_level'].tolist()
        weaknesses = bloom_performance[bloom_performance['score'] < 70]['bloom_level'].tolist()
        bloom_dict = bloom_performance.to_dict('records')
    else:
        strengths = []
        weaknesses = []
        bloom_dict = []

    # 4. Calculate Performance by Topic
    topic_scores = {}
    if 'activity_ref' in df.columns and 'activity_type' in df.columns:
        quiz_refs = df[df['activity_type'] == 'quiz']['activity_ref'].unique()
        for quiz_id in quiz_refs:
            if not quiz_id: continue
            quiz = await quiz_service.get(quiz_id) # Use the service
            if quiz and quiz.topic_title:
                # Ensure scores are numeric before calculating mean
                scores = pd.to_numeric(df[df['activity_ref'] == quiz_id]['score'], errors='coerce').fillna(0.0)
                topic_scores[quiz.topic_title] = round(scores.mean(), 2)
    
    # 5. Calculate Overall Summary
    total_duration = df['duration'].sum() if 'duration' in df.columns and pd.api.types.is_numeric_dtype(df['duration']) else 0
    
    summary = {
        "total_activities": len(df),
        "overall_score": round(df['score'].mean(), 2),
        "time_spent_sec": int(total_duration)
    }
    
    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "performance_by_bloom": bloom_dict,
        "performance_by_topic": [{"topic": k, "score": v} for k, v in topic_scores.items()]
    }


async def generate_all_student_features() -> pd.DataFrame:
    """
    Generates a feature matrix (the 'X') for ALL students.
    This is the input for your AI model.
    """
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("Warning: 'student' role not found. Cannot generate features.")
        return pd.DataFrame()

    # --- FIX: Use 'filter' keyword to remove UserWarning ---
    student_ids_query = db.collection("user_profiles").where(
        filter=FieldFilter("role_id", "==", student_role_id)
    ).stream()
    student_ids = [doc.id for doc in student_ids_query]
    
    all_features = []
    for student_id in student_ids:
        profile = await profile_service.get(student_id) # Use the service
        
        # This 'if' check now works because .get() will return None
        # for profiles that fail validation (e.g. missing 'user_id' field)
        if not profile or profile.deleted:
            continue
            
        analytics = await get_student_analytics(student_id)
        
        features = {
            "student_id": student_id,
            "pre_assessment_score": profile.pre_assessment_score or 0,
            "overall_score": analytics["summary"]["overall_score"],
            "total_activities": analytics["summary"]["total_activities"],
            "time_spent_sec": analytics["summary"]["time_spent_sec"]
        }
        
        for item in analytics["performance_by_bloom"]:
            features[f"bloom_{item['bloom_level']}"] = item['score']
            
        all_features.append(features)

    if not all_features:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_features).fillna(0)
    return df