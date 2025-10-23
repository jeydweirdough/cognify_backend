from typing import List, Dict, Any
from database.firestore import db
from datetime import datetime
import uuid


def _fetch_student_activities(student_id: str) -> List[Dict[str, Any]]:
    """Fetch student's activities sorted by timestamp."""
    docs = db.collection("activities").where("student_id", "==", student_id).stream()
    activities = [d.to_dict() for d in docs]
    # Sort by timestamp if present
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return activities


def _fetch_modules_for_subject(subject_id: str) -> List[Dict[str, Any]]:
    """Fetch modules for a subject."""
    return [d.to_dict() for d in db.collection("modules")
            .where("subject_id", "==", subject_id).stream()]


def _fetch_tos(subject_id: str) -> Dict[str, Any]:
    """Fetch Table of Specifications for a subject."""
    doc = db.collection("tos").document(subject_id).get()
    if not doc.exists:
        return {}
    return doc.to_dict()


def _analyze_performance(activities: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Analyze student performance by topic."""
    topic_stats: Dict[str, Dict[str, float]] = {}
    
    for activity in activities:
        topic = activity.get("activity_ref", "") or activity.get("subject_id", "unknown")
        score = activity.get("score", 0)
        completion = activity.get("completion_rate", 0)
        
        if topic not in topic_stats:
            topic_stats[topic] = {
                "scores": [],
                "completions": [],
                "count": 0
            }
            
        if isinstance(score, (int, float)):
            topic_stats[topic]["scores"].append(float(score))
        if isinstance(completion, (int, float)):
            topic_stats[topic]["completions"].append(float(completion))
        topic_stats[topic]["count"] += 1
    
    # Calculate averages
    for topic, stats in topic_stats.items():
        scores = stats["scores"]
        completions = stats["completions"]
        stats["avg_score"] = sum(scores) / len(scores) if scores else 0
        stats["avg_completion"] = sum(completions) / len(completions) if completions else 0
        # Calculate improvement (difference between latest and earliest scores)
        stats["improvement"] = scores[-1] - scores[0] if len(scores) > 1 else 0
        # Remove raw lists
        stats.pop("scores")
        stats.pop("completions")
    
    return topic_stats


def _find_candidate_modules(topic_stats: Dict[str, Dict[str, float]], 
                          subject_id: str) -> List[Dict[str, Any]]:
    """Find suitable modules based on performance stats."""
    modules = _fetch_modules_for_subject(subject_id)
    tos = _fetch_tos(subject_id)
    
    # Score each module based on alignment with weak areas
    scored_modules = []
    for module in modules:
        score = 0.0
        module_title = module.get("title", "").lower()
        module_purpose = module.get("purpose", "").lower()
        
        for topic, stats in topic_stats.items():
            # Lower scores and completion rates increase module relevance
            topic_need = (100 - stats["avg_score"]) / 100.0
            completion_need = 1.0 - stats["avg_completion"]
            
            # Check if module covers this topic (simple text matching)
            topic_lower = topic.lower()
            if (topic_lower in module_title or 
                topic_lower in module_purpose or
                any(topic_lower in str(c.get("title", "")).lower() 
                    for c in tos.get("content", []))):
                # Higher score for modules matching weak topics
                score += (topic_need * 0.7 + completion_need * 0.3)
        
        if score > 0:
            scored_modules.append((score, module))
    
    # Sort by score descending
    scored_modules.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored_modules]


def pick_recommendations_for_student(student_id: str, max_recommendations: int = 3) -> List[Dict[str, Any]]:
    """Generate recommendations for a student based on their activity patterns."""
    # Get student's activities
    activities = _fetch_student_activities(student_id)
    if not activities:
        return []
    
    # Get current/most recent subject
    recent = activities[0] if activities else {}
    subject_id = recent.get("subject_id")
    if not subject_id:
        return []
    
    # Analyze performance by topic
    topic_stats = _analyze_performance(activities)
    
    # Find suitable modules
    candidate_modules = _find_candidate_modules(topic_stats, subject_id)
    
    # Create recommendations
    recommendations = []
    for module in candidate_modules[:max_recommendations]:
        # Find the topic stats that led to this recommendation
        module_topic = next(
            (topic for topic, stats in topic_stats.items() 
             if topic.lower() in str(module.get("title", "")).lower()),
            None
        )
        
        stats = topic_stats.get(module_topic, {}) if module_topic else {}
        
        recommendation = {
            "recommendation_id": str(uuid.uuid4()),
            "student_id": student_id,
            "subject_id": subject_id,
            "recommended_topic": module_topic or module.get("title"),
            "recommended_module": module.get("module_id"),
            "bloom_focus": module.get("bloom_level"),
            "reason": (f"Performance needs improvement in {module_topic}"
                      f" (avg score: {stats.get('avg_score', 0):.1f},"
                      f" completion: {stats.get('avg_completion', 0):.2f})"),
            "confidence": min(1.0, max(0.1, 
                (100 - stats.get("avg_score", 0)) / 100.0 * 0.7 +
                (1.0 - stats.get("avg_completion", 0)) * 0.3
            )),
            "timestamp": datetime.utcnow().isoformat()
        }
        recommendations.append(recommendation)
    
    # Store recommendations in Firestore
    for rec in recommendations:
        db.collection("recommendations").document(rec["recommendation_id"]).set(rec)
    
    return recommendations