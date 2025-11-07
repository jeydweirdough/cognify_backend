"""Test data population script for Cognify Backend."""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import sys
import os
from pathlib import Path
import random

# --- Add base directory to path ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
# ----------------------------------

from core.firebase import db
# --- FIX: Import the new student list ---
from .config import *

# This imports the actual models from your app to ensure data is correct
from database.models import (
    UserProfileBase, StudentProgress, Subject, TOS, BloomEntry, 
    SubContent, ContentSection
)
from services.role_service import get_role_id_by_designation

def get_iso_time():
    return datetime.now(timezone.utc).isoformat()

async def create_content():
    """Creates all test modules and quizzes from config."""
    print(f"Creating {len(TEST_MODULES_DATA)} test modules...")
    for mod_data in TEST_MODULES_DATA:
        module_ref = db.collection("modules").document(mod_data["id"])
        module_ref.set({
            "id": mod_data["id"],
            "subject_id": TEST_SUBJECT_ID,
            "title": mod_data["title"],
            "bloom_level": mod_data["bloom_level"],
            "purpose": f"Purpose for {mod_data['title']}",
            "material_type": "reading",
            "material_url": "https://example.com/test/module",
            "estimated_time": 30,
            "created_at": get_iso_time(),
            "deleted": False
        })

    print(f"Creating {len(TEST_QUIZZES_DATA)} test quizzes...")
    for quiz_data in TEST_QUIZZES_DATA:
        quiz_ref = db.collection("quizzes").document(quiz_data["id"])
        quiz_ref.set({
            "id": quiz_data["id"],
            "subject_id": TEST_SUBJECT_ID,
            "topic_title": quiz_data["title"],
            "bloom_level": quiz_data["bloom_level"],
            "question": f"Test Question for {quiz_data['title']}",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
            "created_at": get_iso_time(),
            "deleted": False
        })

def generate_realistic_scores(persona: str, bloom_level: str) -> (float, float, int):
    """
    Generates a realistic score, completion, and duration
    based on the student's persona and the content's bloom level.
    """
    score = 75.0
    completion = random.uniform(0.9, 1.0)
    duration = random.randint(1200, 3600) # 20-60 minutes

    # Simple bloom levels
    if bloom_level in ["remembering", "understanding"]:
        if persona == "high_achiever":
            score = random.randint(85, 100)
        elif persona == "struggler":
            score = random.randint(40, 65)
        elif persona == "poor_application": # Good at remembering!
            score = random.randint(90, 100)
        elif persona == "good_crammer": # Bad at remembering!
            score = random.randint(50, 70)

    # Complex bloom levels
    elif bloom_level in ["applying", "analyzing"]:
        if persona == "high_achiever":
            score = random.randint(85, 100)
        elif persona == "struggler":
            score = random.randint(40, 60)
        elif persona == "poor_application": # Bad at applying!
            score = random.randint(40, 60)
        elif persona == "good_crammer": # Good at applying!
            score = random.randint(85, 100)

    return score, round(completion, 2), duration


async def create_student_activities(student_id: str, persona: str) -> int:
    """
    Generates a full, realistic activity log for a single student.
    They will complete every module and quiz.
    """
    now = datetime.now(timezone.utc)
    activity_count = 0
    
    # Combine all content
    all_content = [
        {"type": "module", "ref_id": mod["id"], "bloom_level": mod["bloom_level"]} for mod in TEST_MODULES_DATA
    ] + [
        {"type": "quiz", "ref_id": quiz["id"], "bloom_level": quiz["bloom_level"]} for quiz in TEST_QUIZZES_DATA
    ]
    
    # Create an activity for every piece of content
    for i, content in enumerate(all_content):
        score, completion, duration = generate_realistic_scores(persona, content["bloom_level"])
        
        activity_id = f"{TEST_PREFIX}act_{student_id[len(TEST_PREFIX):]}_{content['ref_id'][len(TEST_PREFIX):]}"
        act_ref = db.collection("activities").document(activity_id)
        
        # Stagger timestamps
        timestamp = (now - timedelta(days=len(all_content) - i)).isoformat()
        
        act_ref.set({
            "id": activity_id,
            "user_id": student_id,
            "subject_id": TEST_SUBJECT_ID,
            "activity_type": content["type"],
            "activity_ref": content["ref_id"],
            "bloom_level": content["bloom_level"],
            "score": score,
            "completion_rate": completion,
            "duration": duration,
            "timestamp": timestamp,
            "created_at": timestamp,
            "deleted": False
        })
        activity_count += 1
        
    return activity_count


async def populate_test_data():
    """Populate Firestore with test data that matches the application schema."""
    print("🔄 Populating test data...")
    
    print("ℹ️  Fetching real 'student' role ID from 'roles' collection...")
    real_student_role_id = await get_role_id_by_designation("student")
    
    if not real_student_role_id:
        print("❌ CRITICAL ERROR: Could not find the 'student' role in your 'roles' collection.")
        print("Please ensure a role with designation 'student' exists in Firestore.")
        return
    
    print(f"✅ Found 'student' role. Using ID: {real_student_role_id}")

    # 1. Create test Subject and TOS
    subject_ref = db.collection("subjects").document(TEST_SUBJECT_ID)
    subject_data = Subject(subject_id=TEST_SUBJECT_ID, **SAMPLE_SUBJECT_DATA).model_dump(exclude_none=True)
    # --- FIX: Add the 'deleted' field so the API query can find it ---
    subject_ref.set({**subject_data, "deleted": False})
    print(f"✅ Created test subject: {TEST_SUBJECT_ID}")

    tos_ref = db.collection("tos").document(TEST_TOS_ID)
    tos_data = TOS(id=TEST_TOS_ID, **SAMPLE_TOS_DATA).to_dict()
    tos_ref.set({
        **tos_data,
        "created_at": get_iso_time(),
        "deleted": False
    })
    print(f"✅ Created test TOS: {TEST_TOS_ID}")

    # 2. Create all test content (Modules, Quizzes)
    await create_content()
    print(f"✅ Created {len(TEST_MODULES_DATA)} modules and {len(TEST_QUIZZES_DATA)} quizzes.")

    # 3. Create all 12 test students and their 144 activities
    all_students_to_create = [
        {"id": TEST_PASS_STUDENT_ID, "data": SAMPLE_PASS_STUDENT_DATA, "persona": "high_achiever"},
        {"id": TEST_FAIL_STUDENT_ID, "data": SAMPLE_FAIL_STUDENT_DATA, "persona": "struggler"},
    ]
    all_students_to_create.extend(ADDITIONAL_STUDENT_DATA)
    
    total_activities_created = 0
    print(f"Creating {len(all_students_to_create)} test students and their activity logs...")

    for student in all_students_to_create:
        student_id = student["id"]
        
        # Create the user profile
        student_ref = db.collection("user_profiles").document(student_id)
        student_data_dict = {**student["data"], "role_id": real_student_role_id}
        
        # Create a default progress map if it doesn't exist
        if "progress" not in student_data_dict:
             student_data_dict["progress"] = {"Theories": 0.0, "Globalization": 0.0}
        
        student_data = UserProfileBase(**student_data_dict).model_dump(exclude_none=True)
        student_ref.set({
            **student_data,
            "id": student_id,
            "created_at": get_iso_time(),
            "deleted": False
        })
        
        # Create all activities for this student
        num_activities = await create_student_activities(student_id, student["persona"])
        total_activities_created += num_activities
    
    print(f"✅ Created {len(all_students_to_create)} total students.")
    print(f"✅ Created {total_activities_created} total activities.")

    # 4. Create test recommendations (for one of the failing students)
    for i, rec_id in enumerate(TEST_RECOMMENDATION_IDS):
        rec_ref = db.collection("recommendations").document(rec_id)
        rec_ref.set({
            "id": rec_id, "deleted": False,
            "user_id": TEST_FAIL_STUDENT_ID, # Give recs to the original fail student
            "subject_id": TEST_SUBJECT_ID,
            "recommended_topic": "Applying Trait Theory",
            "recommended_module": TEST_MODULES_DATA[4]["id"], # Points to "mod_app_01"
            "bloom_focus": "applying",
            "reason": "Test recommendation: Low scores in 'applying' activities.",
            "confidence": 0.85,
            "timestamp": get_iso_time(), "created_at": get_iso_time()
        })
    print(f"✅ Created {len(TEST_RECOMMENDATION_IDS)} test recommendations for {TEST_FAIL_STUDENT_ID}")

    print("\n🎉 Test data population complete!")
    print("\nTest IDs for reference:")
    print(f"Original Pass Student ID: {TEST_PASS_STUDENT_ID} (Persona: high_achiever)")
    print(f"Original Fail Student ID: {TEST_FAIL_STUDENT_ID} (Persona: struggler)")
    print(f"View the 10 other students (e.g., {ADDITIONAL_STUDENT_DATA[0]['id']}) in Firestore.")


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
         sys.path.insert(0, str(BASE_DIR))
    
    from core.firebase import db
    from database.models import (
        UserProfileBase, StudentProgress, Subject, TOS, BloomEntry, 
        SubContent, ContentSection
    )
    from services.role_service import get_role_id_by_designation

    asyncio.run(populate_test_data())

