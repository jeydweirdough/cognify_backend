import asyncio
from datetime import datetime
import pandas as pd
import numpy as np
from google.cloud.firestore_v1.base_query import FieldFilter
from core.firebase import db
from services import role_service, activity_service
from collections import defaultdict 

def safe_float(val):
    try:
        if val is None: return 0.0
        if isinstance(val, (int, float)):
            if pd.isna(val) or np.isnan(val) or np.isinf(val): return 0.0
            return float(round(val, 2))
        return 0.0
    except: return 0.0

def get_current_iso_time():
    return datetime.utcnow().isoformat()

def apply_prediction_logic(analytics_data: dict):
    summary = analytics_data.get("summary", {})
    
    current_score = safe_float(summary.get("average_score", 0))
    completion_rate = safe_float(summary.get("completion_rate", 0))
    study_sessions = int(summary.get("total_sessions", 0))
    
    # --- FIX 1: SCORE PRIORITY LOGIC ---
    # Base probability weighted on Score (80%) and Effort (20%)
    probability = (current_score * 0.8) + (completion_rate * 0.2)
    
    is_passing = probability >= 75.0
    
    # OVERRIDE: If the student actually knows the material (Score >= 75), they PASS.
    if current_score >= 75.0:
        is_passing = True
        probability = max(probability, current_score) # Boost confidence

    # FAILSAFE: If score is failing (< 60), they FAIL regardless of effort.
    if current_score < 60.0: 
        is_passing = False

    risk_factors = []
    if current_score < 75.0: risk_factors.append("Low Average Score")
    if completion_rate < 50.0: risk_factors.append("Low Activity Completion")
    if study_sessions < 3: risk_factors.append("Insufficient Study Sessions")

    analytics_data["prediction"] = {
        "predicted_to_pass": bool(is_passing),
        "confidence_score": safe_float(probability),
        "risk_factors": risk_factors,
        "predicted_score": current_score,
        "last_updated": get_current_iso_time()
    }
    return analytics_data 

async def get_live_analytics(student_id: str) -> dict:
    try:
        docs = db.collection("activities").where(
            filter=FieldFilter("user_id", "==", student_id)
        ).stream()
        
        activities_data = [doc.to_dict() for doc in docs]

        if not activities_data:
            return {
                "student_id": student_id,
                "summary": { "total_activities": 0, "average_score": 0.0, "completion_rate": 0.0, "total_sessions": 0, "last_active": None },
                "performance_by_bloom": {},
                "recent_activity": []
            }

        df = pd.DataFrame(activities_data)
        df['score'] = pd.to_numeric(df.get('score'), errors='coerce').fillna(0.0)
        df['completion_rate'] = pd.to_numeric(df.get('completion_rate'), errors='coerce').fillna(0.0)

        average_score = safe_float(df['score'].mean())
        avg_completion = safe_float(df['completion_rate'].mean())
        total_sessions = len(df)
        last_active = df['created_at'].max() if 'created_at' in df else None

        bloom_performance = {}
        if 'bloom_level' in df.columns:
            bloom_grp = df.groupby('bloom_level')['score'].mean()
            bloom_performance = {level: safe_float(score) for level, score in bloom_grp.items()}

        recent = df.sort_values('created_at', ascending=False).head(5)
        recent_activities = recent.to_dict('records')

        return {
            "student_id": student_id,
            "summary": {
                "total_activities": len(df),
                "average_score": average_score,
                "completion_rate": avg_completion,
                "total_sessions": total_sessions,
                "last_active": last_active
            },
            "performance_by_bloom": bloom_performance,
            "recent_activity": recent_activities
        }
    except Exception as e:
        print(f"Error in get_live_analytics: {e}")
        return {
            "student_id": student_id,
            "summary": { "total_activities": 0, "average_score": 0.0, "completion_rate": 0.0, "total_sessions": 0, "last_active": None },
            "performance_by_bloom": {}, 
            "recent_activity": []
        }

def _fetch_all_student_data_sync(student_role_id: str):
    try:
        profiles_query = db.collection("user_profiles").where(
            filter=FieldFilter("role_id", "==", student_role_id)
        ).where(
            filter=FieldFilter("deleted", "!=", True)
        ).stream()
        return list(profiles_query)
    except Exception as e:
        print(f"🔥 FIRESTORE QUERY ERROR: {e}")
        return []

async def get_global_analytics_report():
    try:
        student_role_id = await role_service.get_role_id_by_designation("student")
        if not student_role_id:
            return {"summary": {}, "predictions": []}

        all_students = await asyncio.to_thread(_fetch_all_student_data_sync, student_role_id)
        if not all_students:
            return {"summary": {}, "predictions": []}

        tasks = [get_live_analytics(student.id) for student in all_students]
        all_analytics_results = await asyncio.gather(*tasks)
        
        predictions_list = []
        
        # --- FIX 2: AGGREGATE GLOBAL BLOOM DATA ---
        global_bloom_scores = defaultdict(list)
        
        for i, analytics_data in enumerate(all_analytics_results):
            apply_prediction_logic(analytics_data)
            student_doc = all_students[i].to_dict()
            
            # Collect scores for global average
            for bloom, score in analytics_data.get("performance_by_bloom", {}).items():
                global_bloom_scores[bloom].append(score)

            predictions_list.append({
                "student_id": analytics_data["student_id"],
                "first_name": student_doc.get('first_name'),
                "last_name": student_doc.get('last_name'),
                "predicted_to_pass": analytics_data["prediction"]["predicted_to_pass"],
                "overall_score": analytics_data["summary"]["average_score"]
            })

        total_students = len(predictions_list)
        pass_count = sum(1 for p in predictions_list if p["predicted_to_pass"])
        fail_count = total_students - pass_count
        pass_rate = safe_float((pass_count / total_students) * 100) if total_students > 0 else 0.0

        # Calculate class averages
        global_bloom_avg = {k: safe_float(sum(v)/len(v)) for k, v in global_bloom_scores.items()}

        return {
            "summary": {
                "total_students_predicted": total_students,
                "count_predicted_to_pass": pass_count,
                "count_predicted_to_fail": fail_count,
                "predicted_pass_rate": pass_rate,
                "global_bloom_performance": global_bloom_avg # Frontend needs this!
            },
            "predictions": predictions_list
        }
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return {"summary": {}, "predictions": []}