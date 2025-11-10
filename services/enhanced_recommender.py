# ============================================================
# services/enhanced_recommender.py
# Updated recommendation engine that uses diagnostic results
# ============================================================

from typing import Any, Dict, List
from database.models import EnhancedRecommendationBase, EnhancedRecommendation
from services import module_service, quiz_service
from services import diagnostic_result_service, enhanced_recommendation_service
from datetime import datetime

async def generate_recommendations_from_diagnostic(diagnostic_result_id: str) -> List[Dict[str, Any]]:
    """
    Generates personalized recommendations based on diagnostic test results.
    This is the NEW recommendation engine that replaces the old activity-based one.
    """
    # 1. Fetch the diagnostic result
    result = await diagnostic_result_service.get(diagnostic_result_id)
    if not result:
        return []
    
    recommendations = []
    
    # 2. For each weak TOS topic, recommend relevant modules/quizzes
    for tos_perf in result.tos_performance:
        # Only recommend if score is below 75%
        if tos_perf.score_percentage >= 75.0:
            continue
        
        # Find the weakest Bloom's level for this topic
        weakest_bloom = min(tos_perf.bloom_breakdown.items(), key=lambda x: x[1])
        bloom_level = weakest_bloom[0]
        bloom_score = weakest_bloom[1]
        
        # 3. Find modules that match this TOS topic + Bloom's level
        matching_modules, _ = await module_service.where(
            "subject_id", "==", result.subject_id,
            limit=100
        )
        
        # Filter by title (simple keyword matching for demo)
        topic_keywords = tos_perf.topic_title.lower().split()
        relevant_modules = [
            m for m in matching_modules
            if any(kw in m.title.lower() for kw in topic_keywords) 
            and m.bloom_level == bloom_level
        ]
        
        # 4. Find matching quizzes
        matching_quizzes, _ = await quiz_service.where(
            "subject_id", "==", result.subject_id,
            limit=100
        )
        
        relevant_quizzes = [
            q for q in matching_quizzes
            if any(kw in (q.topic_title or "").lower() for kw in topic_keywords)
            and q.bloom_level == bloom_level
        ]
        
        # 5. Determine priority
        priority = "high" if bloom_score < 50 else "medium" if bloom_score < 65 else "low"
        
        # 6. Create recommendation
        rec_payload = EnhancedRecommendationBase(
            user_id=result.user_id,
            subject_id=result.subject_id,
            recommended_topic=tos_perf.topic_title,
            recommended_modules=[m.id for m in relevant_modules[:3]],
            recommended_quizzes=[q.id for q in relevant_quizzes[:3]],
            bloom_focus=bloom_level,
            priority=priority,
            reason=(
                f"Diagnostic test shows low performance in '{tos_perf.topic_title}' "
                f"({tos_perf.score_percentage:.1f}%). Weakest cognitive level: "
                f"'{bloom_level}' ({bloom_score:.1f}%)."
            ),
            diagnostic_result_id=diagnostic_result_id,
            confidence=0.90,
            timestamp=datetime.utcnow().isoformat()
        )
        
        try:
            new_rec = await enhanced_recommendation_service.create(rec_payload)
            recommendations.append(new_rec.model_dump())
        except Exception as e:
            print(f"Error saving recommendation: {e}")
    
    return recommendations