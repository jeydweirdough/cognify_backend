"""Test data population script for Cognify Backend."""
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uuid

from database.firestore import db
from .config import *

def generate_id(prefix: str) -> str:
    """Generate a unique ID with test prefix."""
    return f"{TEST_PREFIX}{prefix}_{str(uuid.uuid4())[:8]}"

async def populate_test_data():
    """Populate Firestore with test data."""
    print("🔄 Populating test data...")
    
    # 1. Create test student
    student_ref = db.collection("students").document(TEST_STUDENT_ID)
    student_ref.set({
        **SAMPLE_STUDENT_DATA,
        "student_id": TEST_STUDENT_ID,
        "created_at": datetime.utcnow().isoformat()
    })
    print(f"✅ Created test student: {TEST_STUDENT_ID}")

    # 2. Create test subject TOS
    tos_ref = db.collection("tos").document(TEST_SUBJECT_ID)
    tos_ref.set({
        **SAMPLE_TOS_DATA,
        "id": TEST_SUBJECT_ID,
        "created_at": datetime.utcnow().isoformat()
    })
    print(f"✅ Created test TOS: {TEST_SUBJECT_ID}")

    # 3. Create test modules
    for i, module_id in enumerate(TEST_MODULE_IDS):
        module_ref = db.collection("modules").document(module_id)
        module_ref.set({
            **SAMPLE_MODULE_DATA,
            "module_id": module_id,
            "subject_id": TEST_SUBJECT_ID,
            "title": f"{SAMPLE_MODULE_DATA['title']} {i+1}",
            "created_at": datetime.utcnow().isoformat()
        })
    print(f"✅ Created {len(TEST_MODULE_IDS)} test modules")

    # 4. Create test assessment
    assessment_ref = db.collection("assessments").document(TEST_ASSESSMENT_ID)
    assessment_ref.set({
        **SAMPLE_ASSESSMENT_DATA,
        "assessment_id": TEST_ASSESSMENT_ID,
        "created_at": datetime.utcnow().isoformat()
    })
    print(f"✅ Created test assessment: {TEST_ASSESSMENT_ID}")

    # 5. Create test quizzes
    for i, quiz_id in enumerate(TEST_QUIZ_IDS):
        quiz_ref = db.collection("quizzes").document(quiz_id)
        quiz_ref.set({
            "quiz_id": quiz_id,
            "subject_id": TEST_SUBJECT_ID,
            "topic_title": "Theories",
            "bloom_level": "applying",
            "question": f"Test Question {i+1}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
            "created_at": datetime.utcnow().isoformat()
        })
    print(f"✅ Created {len(TEST_QUIZ_IDS)} test quizzes")

    # 6. Create test activities (with timestamps spread over last week)
    now = datetime.utcnow()
    for i, activity_id in enumerate(TEST_ACTIVITY_IDS):
        activity_ref = db.collection("activities").document(activity_id)
        activity_ref.set({
            **SAMPLE_ACTIVITY_DATA,
            "activity_id": activity_id,
            "student_id": TEST_STUDENT_ID,
            "activity_ref": TEST_MODULE_IDS[i % len(TEST_MODULE_IDS)],
            "score": 75 + (i * 5),  # Showing improvement
            "timestamp": (now - timedelta(days=7-i)).isoformat()
        })
    print(f"✅ Created {len(TEST_ACTIVITY_IDS)} test activities")

    # 7. Create test recommendations
    for i, rec_id in enumerate(TEST_RECOMMENDATION_IDS):
        rec_ref = db.collection("recommendations").document(rec_id)
        rec_ref.set({
            "recommendation_id": rec_id,
            "student_id": TEST_STUDENT_ID,
            "subject_id": TEST_SUBJECT_ID,
            "recommended_topic": "Theories",
            "recommended_module": TEST_MODULE_IDS[i % len(TEST_MODULE_IDS)],
            "bloom_focus": "applying",
            "reason": "Test recommendation reason",
            "confidence": 0.85,
            "timestamp": datetime.utcnow().isoformat()
        })
    print(f"✅ Created {len(TEST_RECOMMENDATION_IDS)} test recommendations")

    print("\n🎉 Test data population complete!")
    print("\nTest IDs for reference:")
    print(f"Student ID: {TEST_STUDENT_ID}")
    print(f"Subject ID: {TEST_SUBJECT_ID}")
    print(f"Module IDs: {', '.join(TEST_MODULE_IDS)}")
    print(f"Assessment ID: {TEST_ASSESSMENT_ID}")


if __name__ == "__main__":
    asyncio.run(populate_test_data())