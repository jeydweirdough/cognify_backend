# ============================================================
# services/diagnostic_analytics.py
# Analytics specifically for diagnostic assessments
# ============================================================

import asyncio
from typing import Dict, Any, List
from collections import defaultdict
from services import diagnostic_result_service
from services import tos_service

async def get_subject_diagnostic_summary(subject_id: str) -> Dict[str, Any]:
    """
    Generates a summary of diagnostic performance for a subject.
    Shows which TOS topics are most challenging for students.
    """
    # Fetch all diagnostic results for this subject
    all_results, _ = await diagnostic_result_service.where(
        "subject_id", "==", subject_id,
        limit=1000
    )
    
    if not all_results:
        return {
            "subject_id": subject_id,
            "total_students_tested": 0,
            "avg_overall_score": 0.0,
            "pass_rate": 0.0,
            "tos_topic_performance": []
        }
    
    # Aggregate data
    total_students = len(all_results)
    total_score = sum(r.overall_score for r in all_results)
    passed = sum(1 for r in all_results if r.passing_status == "passed")
    
    # Aggregate TOS topic performance
    topic_stats = defaultdict(lambda: {"scores": [], "bloom_breakdown": defaultdict(list)})
    
    for result in all_results:
        for tos_perf in result.tos_performance:
            topic_stats[tos_perf.topic_title]["scores"].append(tos_perf.score_percentage)
            
            # Aggregate Bloom's performance
            for bloom, score in tos_perf.bloom_breakdown.items():
                topic_stats[tos_perf.topic_title]["bloom_breakdown"][bloom].append(score)
    
    # Calculate averages
    tos_topic_performance = []
    for topic, data in topic_stats.items():
        avg_score = sum(data["scores"]) / len(data["scores"])
        
        bloom_avgs = {}
        for bloom, scores in data["bloom_breakdown"].items():
            bloom_avgs[bloom] = round(sum(scores) / len(scores), 2)
        
        tos_topic_performance.append({
            "topic_title": topic,
            "avg_score": round(avg_score, 2),
            "student_count": len(data["scores"]),
            "bloom_performance": bloom_avgs,
            "difficulty_level": "high" if avg_score < 60 else "medium" if avg_score < 75 else "low"
        })
    
    # Sort by difficulty (lowest scores first)
    tos_topic_performance.sort(key=lambda x: x["avg_score"])
    
    return {
        "subject_id": subject_id,
        "total_students_tested": total_students,
        "avg_overall_score": round(total_score / total_students, 2),
        "pass_rate": round((passed / total_students) * 100, 2),
        "tos_topic_performance": tos_topic_performance
    }