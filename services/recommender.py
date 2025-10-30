# services/recommender.py
from typing import List, Dict, Any
from core.firebase import db
from datetime import datetime
import asyncio
import uuid

# --- FIX: Import services, but NOT subject_service ---
from services import (
    activity_service, 
    module_service, 
    tos_service, 
    recommendation_service
)
# --- FIX: Import Subject model and db directly ---
from database.models import RecommendationBase, Subject, TOS


async def _fetch_student_activities(student_id: str) -> List[Dict[str, Any]]:
    """Fetch student's activities sorted by timestamp."""
    activities = await activity_service.where("student_id", "==", student_id)
    activities_data = [act.model_dump() for act in activities]
    activities_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return activities_data

async def _fetch_modules_for_subject(subject_id: str) -> List[Dict[str, Any]]:
    """Fetch modules for a subject."""
    modules = await module_service.where("subject_id", "==", subject_id)
    return [m.model_dump() for m in modules]

async def _fetch_active_tos(subject_id: str) -> Dict[str, Any]:
    """Fetch the *active* Table of Specifications for a subject."""
    
    # --- FIX: Fetch subject manually instead of using a service ---
    def _get_subject():
        doc = db.collection("subjects").document(subject_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["subject_id"] = doc.id
        return Subject.model_validate(data)
    
    subject = await asyncio.to_thread(_get_subject)
    # --- End Fix ---

    if not subject or not subject.active_tos_id:
        print(f"Warning: No active TOS specified for subject {subject_id}")
        # Fallback: Try to find *any* TOS for the subject
        all_tos = await tos_service.where("subject_id", "==", subject_id)
        if not all_tos:
            return {}
        return all_tos[0].model_dump() # Return the first one found
    
    tos = await tos_service.get(subject.active_tos_id)
    if not tos:
        return {}
    return tos.model_dump()

def _analyze_performance(activities: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Analyze student performance by topic (bloom_level)."""
    topic_stats: Dict[str, Dict[str, Any]] = {}
    
    for activity in activities:
        topic = activity.get("bloom_level")
        if not topic: # Skip activities without a bloom_level
            continue
            
        score = activity.get("score", 0)
        completion = activity.get("completion_rate", 0)
        
        if topic not in topic_stats:
            topic_stats[topic] = {"scores": [], "completions": [], "count": 0}
            
        if isinstance(score, (int, float)):
            topic_stats[topic]["scores"].append(float(score))
        if isinstance(completion, (int, float)):
            topic_stats[topic]["completions"].append(float(completion))
        topic_stats[topic]["count"] += 1
    
    # Calculate averages
    avg_stats = {}
    for topic, stats in topic_stats.items():
        scores = stats["scores"]
        completions = stats["completions"]
        avg_score = sum(scores) / len(scores) if scores else 0
        avg_completion = sum(completions) / len(completions) if completions else 0
        avg_stats[topic] = {
            "avg_score": avg_score,
            "avg_completion": avg_completion,
            "count": stats["count"]
        }
    
    return avg_stats

async def _find_candidate_modules(
    topic_stats: Dict[str, Dict[str, float]], 
    subject_id: str
) -> List[Dict[str, Any]]:
    """Find suitable modules based on performance stats."""
    
    modules = await _fetch_modules_for_subject(subject_id)
    
    scored_modules = []
    for module in modules:
        score = 0.0
        module_bloom = module.get("bloom_level", "").lower()
        
        # Check if this module's bloom_level is a weak topic
        if module_bloom in topic_stats:
            stats = topic_stats[module_bloom]
            # Recommend if score is below 80 or completion below 100
            if stats["avg_score"] < 80.0 or stats["avg_completion"] < 1.0:
                topic_need = (100 - stats["avg_score"]) / 100.0
                completion_need = 1.0 - stats["avg_completion"]
                # Weighted score: low score is more important
                score = (topic_need * 0.7 + completion_need * 0.3)
        
        if score > 0.2: # Only recommend if there's a clear need
            scored_modules.append((score, module))
    
    scored_modules.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored_modules]

async def pick_recommendations_for_student(student_id: str, max_recommendations: int = 3) -> List[Dict[str, Any]]:
    """Generate recommendations for a student based on their activity patterns."""
    
    activities = await _fetch_student_activities(student_id)
    if not activities:
        return []
    
    recent = activities[0]
    subject_id = recent.get("subject_id")
    if not subject_id:
        return []
    
    topic_stats = _analyze_performance(activities)
    
    candidate_modules = await _find_candidate_modules(topic_stats, subject_id)
    
    recommendations = []
    for module in candidate_modules[:max_recommendations]:
        bloom_focus = module.get("bloom_level")
        stats = topic_stats.get(bloom_focus, {"avg_score": 0, "avg_completion": 0})
        
        rec_payload = RecommendationBase(
            student_id=student_id,
            subject_id=subject_id,
            recommended_topic=module.get("title"),
            recommended_module=module.get("id"), # Use the module's 'id'
            bloom_focus=bloom_focus,
            reason=(
                f"Low performance in '{bloom_focus}' activities. "
                f"Avg score: {stats.get('avg_score', 0):.1f}, "
                f"Avg completion: {stats.get('avg_completion', 0):.2f}"
            ),
            confidence=0.85, # Placeholder
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            new_rec = await recommendation_service.create(rec_payload)
            recommendations.append(new_rec.model_dump())
        except Exception as e:
            print(f"Error saving recommendation: {e}")
    
    return recommendations