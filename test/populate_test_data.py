"""
REALISTIC test data population for Cognify Backend.
Based on the manuscript requirements with authentic learning patterns.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import random
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from database.models import get_current_iso_time
from services.role_service import get_role_id_by_designation
from firebase_admin import auth
from .config import (
    TEST_PREFIX, SUBJECTS_DATA, STUDENT_PERSONAS, PERSONA_BASE_SCORES
)

def get_iso_time():
    return datetime.now(timezone.utc).isoformat()


def create_tos_for_subject(subject_id: str, subject_name: str):
    """Creates a realistic TOS document"""
    return {
        "id": f"{TEST_PREFIX}tos_{subject_id.split('_')[-1]}_v1",
        "subject_id": subject_id,
        "subject_name": subject_name,
        "pqf_level": 7,
        "difficulty_distribution": {"easy": 0.30, "moderate": 0.40, "difficult": 0.30},
        "content": [
            {
                "title": "Fundamental Concepts",
                "sub_content": [
                    {"purpose": "Define key terms and concepts", "blooms_taxonomy": [{"remembering": 10}]},
                    {"purpose": "Explain theoretical foundations", "blooms_taxonomy": [{"understanding": 10}]}
                ],
                "no_items": 20,
                "weight_total": 0.20
            },
            {
                "title": "Application and Analysis",
                "sub_content": [
                    {"purpose": "Apply concepts to case studies", "blooms_taxonomy": [{"applying": 15}]},
                    {"purpose": "Analyze psychological phenomena", "blooms_taxonomy": [{"analyzing": 15}]}
                ],
                "no_items": 30,
                "weight_total": 0.30
            },
            {
                "title": "Evaluation and Integration",
                "sub_content": [
                    {"purpose": "Evaluate methods and approaches", "blooms_taxonomy": [{"evaluating": 20}]},
                    {"purpose": "Synthesize multiple perspectives", "blooms_taxonomy": [{"creating": 10}]}
                ],
                "no_items": 30,
                "weight_total": 0.30
            },
            {
                "title": "Professional Practice",
                "sub_content": [
                    {"purpose": "Apply ethical guidelines", "blooms_taxonomy": [{"applying": 10}]},
                    {"purpose": "Evaluate professional scenarios", "blooms_taxonomy": [{"evaluating": 10}]}
                ],
                "no_items": 20,
                "weight_total": 0.20
            }
        ],
        "total_items": 100,
        "is_active": True,
        "created_at": get_iso_time(),
        "deleted": False
    }


def generate_diagnostic_assessment(subject_id: str, subject_name: str, tos_data: dict):
    """Creates a realistic diagnostic assessment"""
    questions = []
    q_num = 1
    
    for section in tos_data["content"]:
        topic_title = section["title"]
        
        for sub in section.get("sub_content", []):
            for bloom_entry in sub.get("blooms_taxonomy", []):
                bloom_level = list(bloom_entry.keys())[0]
                count = bloom_entry[bloom_level]
                
                for i in range(min(3, count)):
                    questions.append({
                        "question_id": f"q{q_num}",
                        "tos_topic_title": topic_title,
                        "bloom_level": bloom_level,
                        "question": f"Sample {bloom_level} question for {topic_title} in {subject_name}",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "answer": "Option A",
                        "cognitive_weight": 1.0
                    })
                    q_num += 1
    
    return {
        "id": f"{TEST_PREFIX}diag_{subject_id.split('_')[-1]}",
        "subject_id": subject_id,
        "title": f"Diagnostic Assessment: {subject_name}",
        "instructions": (
            "This diagnostic test will help identify your strengths and areas for improvement. "
            "Answer all questions to the best of your ability."
        ),
        "total_items": len(questions),
        "questions": questions,
        "passing_score": 75.0,
        "time_limit_minutes": 60,
        "created_at": get_iso_time(),
        "deleted": False
    }


def generate_realistic_score(persona: str, bloom_level: str, variation: float = 5.0) -> float:
    """
    Generates realistic scores based on student persona and cognitive level.
    Adds natural variation (+/- variation).
    """
    base_scores = PERSONA_BASE_SCORES.get(persona, {})
    base_score = base_scores.get(bloom_level, 70)
    
    var = random.uniform(-variation, variation)
    final_score = max(0, min(100, base_score + var))
    
    return round(final_score, 1)


def create_modules_for_subject(subject_id: str, subject_name: str):
    """Create sample modules for a subject"""
    bloom_levels = ["remembering", "understanding", "applying", "analyzing", "evaluating", "creating"]
    modules = []
    
    for i, bloom in enumerate(bloom_levels, 1):
        module_id = f"{TEST_PREFIX}mod_{subject_id.split('_')[-1]}_{bloom[:3]}_{i}"
        modules.append({
            "id": module_id,
            "subject_id": subject_id,
            "title": f"{subject_name}: {bloom.capitalize()} Module {i}",
            "purpose": f"Master {bloom} level concepts",
            "bloom_level": bloom,
            "material_type": "reading",
            "material_url": "https://example.com/module.pdf",
            "estimated_time": random.randint(30, 60),
            "created_at": get_iso_time(),
            "deleted": False
        })
    
    return modules


def create_activities_for_student(student_id: str, persona: str, subject_id: str, modules: list, num_activities: int = 15):
    """Create realistic activities for a student"""
    activities = []
    now = datetime.now(timezone.utc)
    
    for i in range(num_activities):
        module = random.choice(modules)
        bloom_level = module["bloom_level"]
        score = generate_realistic_score(persona, bloom_level)
        
        activity_id = f"{TEST_PREFIX}act_{student_id.split('_')[-1]}_{subject_id.split('_')[-1]}_{i+1}"
        timestamp = (now - timedelta(days=num_activities - i, hours=random.randint(0, 23))).isoformat()
        
        activities.append({
            "id": activity_id,
            "user_id": student_id,
            "subject_id": subject_id,
            "activity_type": random.choice(["module", "quiz", "practice"]),
            "activity_ref": module["id"],
            "bloom_level": bloom_level,
            "score": score,
            "completion_rate": random.uniform(0.85, 1.0) if score > 50 else random.uniform(0.5, 0.85),
            "duration": random.randint(1200, 3600),
            "timestamp": timestamp,
            "created_at": timestamp,
            "deleted": False
        })
    
    return activities


async def populate_test_data():
    """Populate Firestore with realistic test data"""
    print("🚀 Starting REALISTIC test data population...")
    print("=" * 60)
    
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("❌ CRITICAL: 'student' role not found!")
        return
    
    print(f"✅ Found 'student' role. Using ID: {student_role_id}\n")
    
    # 1. CREATE SUBJECTS, TOS, AND DIAGNOSTICS
    print(f"📚 Creating {len(SUBJECTS_DATA)} Psychology subjects with TOS...")
    all_modules = {}
    
    for subj_data in SUBJECTS_DATA:
        subject_id = subj_data["id"]
        
        # Create TOS
        tos_data = create_tos_for_subject(subject_id, subj_data["name"])
        tos_ref = db.collection("tos").document(tos_data["id"])
        tos_ref.set(tos_data)
        
        # Create Subject
        subj_ref = db.collection("subjects").document(subject_id)
        subj_ref.set({
            "id": subject_id,
            "subject_id": subject_id,
            "subject_name": subj_data["name"],
            "pqf_level": subj_data["pqf_level"],
            "active_tos_id": tos_data["id"],
            "deleted": False
        })
        
        # Create Diagnostic Assessment
        diag_data = generate_diagnostic_assessment(subject_id, subj_data["name"], tos_data)
        diag_ref = db.collection("diagnostic_assessments").document(diag_data["id"])
        diag_ref.set(diag_data)
        
        # Create Modules
        modules = create_modules_for_subject(subject_id, subj_data["name"])
        for module in modules:
            db.collection("modules").document(module["id"]).set(module)
        
        all_modules[subject_id] = modules
        
        print(f"  ✅ {subj_data['name']}")
        print(f"     - TOS: {tos_data['id']}")
        print(f"     - Diagnostic: {diag_data['id']} ({diag_data['total_items']} questions)")
        print(f"     - Modules: {len(modules)}")
    
    # 2. CREATE STUDENTS
    print(f"\n👥 Creating {len(STUDENT_PERSONAS)} realistic students...")
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        email = student["email"]
        password = "demo123"  # Default password for all demo students
        
        # Create Firebase Auth user
        try:
            auth.create_user(uid=student_id, email=email, password=password)
            print(f"  ✅ Created auth user: {email} (UID: {student_id})")
        except auth.EmailAlreadyExistsError:
            print(f"  ℹ️  Auth user {email} already exists, skipping.")
        except Exception as e:
            print(f"  ❌ Failed to create auth user {email}: {e}")
            continue
        
        # Create Firestore profile
        db.collection("user_profiles").document(student_id).set({
            "id": student_id,
            "email": email,
            "first_name": student["name"].split()[0],
            "last_name": student["name"].split()[1],
            "role_id": student_role_id,
            "pre_assessment_score": None,
            "progress": {},
            "created_at": get_iso_time(),
            "deleted": False
        })
        
        print(f"  ✅ {student['name']} ({student['persona']})")
    
    # 3. GENERATE DIAGNOSTIC RESULTS AND ACTIVITIES
    print("\n🧪 Generating diagnostic results and activities...")
    total_activities = 0
    
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        persona = student["persona"]
        
        # Take diagnostic for first 2 subjects
        for subj_data in SUBJECTS_DATA[:2]:
            subject_id = subj_data["id"]
            diag_id = f"{TEST_PREFIX}diag_{subject_id.split('_')[-1]}"
            
            # Fetch diagnostic
            diag_doc = db.collection("diagnostic_assessments").document(diag_id).get()
            if not diag_doc.exists:
                continue
            
            diag = diag_doc.to_dict()
            
            # Calculate TOS performance
            tos_performance = []
            all_scores = []
            
            topic_questions = defaultdict(lambda: {"questions": [], "bloom_breakdown": defaultdict(list)})
            
            for q in diag["questions"]:
                topic_questions[q["tos_topic_title"]]["questions"].append(q)
            
            for topic_title, data in topic_questions.items():
                topic_correct = 0
                topic_total = len(data["questions"])
                
                for q in data["questions"]:
                    bloom = q["bloom_level"]
                    score = generate_realistic_score(persona, bloom)
                    
                    if score > 60:
                        topic_correct += 1
                    
                    data["bloom_breakdown"][bloom].append(score)
                
                topic_score = (topic_correct / topic_total) * 100
                all_scores.append(topic_score)
                
                bloom_breakdown = {}
                for bloom, scores in data["bloom_breakdown"].items():
                    bloom_breakdown[bloom] = round(sum(scores) / len(scores), 1)
                
                tos_performance.append({
                    "topic_title": topic_title,
                    "total_questions": topic_total,
                    "correct_answers": topic_correct,
                    "score_percentage": round(topic_score, 1),
                    "bloom_breakdown": bloom_breakdown
                })
            
            overall_score = round(sum(all_scores) / len(all_scores), 1)
            passing_status = "passed" if overall_score >= 75.0 else "failed"
            
            # Save diagnostic result
            result_id = f"{TEST_PREFIX}result_{student_id.split('_')[-1]}_{subject_id.split('_')[-1]}"
            db.collection("diagnostic_results").document(result_id).set({
                "id": result_id,
                "user_id": student_id,
                "assessment_id": diag_id,
                "subject_id": subject_id,
                "overall_score": overall_score,
                "passing_status": passing_status,
                "time_taken_seconds": random.randint(2400, 3600),
                "tos_performance": tos_performance,
                "timestamp": get_iso_time(),
                "created_at": get_iso_time(),
                "deleted": False
            })
            
            # Create activities for this subject
            modules = all_modules[subject_id]
            activities = create_activities_for_student(student_id, persona, subject_id, modules, num_activities=15)
            
            for activity in activities:
                db.collection("activities").document(activity["id"]).set(activity)
            
            total_activities += len(activities)
            
            print(f"  ✅ {student['name']}: {subj_data['name']} - {overall_score}% ({passing_status}), {len(activities)} activities")
    
    print("\n" + "=" * 60)
    print("🎉 REALISTIC DATA POPULATION COMPLETE!")
    print("\n📊 Summary:")
    print(f"  - {len(SUBJECTS_DATA)} Subjects")
    print(f"  - {len(SUBJECTS_DATA)} TOS Documents")
    print(f"  - {len(SUBJECTS_DATA)} Diagnostic Assessments")
    print(f"  - {sum(len(mods) for mods in all_modules.values())} Modules")
    print(f"  - {len(STUDENT_PERSONAS)} Students")
    print(f"  - {len(STUDENT_PERSONAS) * 2} Diagnostic Results")
    print(f"  - {total_activities} Activities")
    print("\n✨ Ready for demo!")
    print("\nDefault password for all students: demo123")


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    
    from core.firebase import db
    from firebase_admin import auth
    from database.models import get_current_iso_time
    from services.role_service import get_role_id_by_designation
    
    asyncio.run(populate_test_data())


# ============================================================
# FILE: test/cleanup_test_data.py (FIX - Import TEST_PREFIX)
# ============================================================
"""Clean up test data from Firestore."""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from .config import TEST_PREFIX  # ✅ Import instead of redefining
from google.cloud.firestore_v1.base_query import FieldFilter

async def cleanup_test_data():
    """Remove all test data from Firestore"""
    print("🔄 Starting test data cleanup...")
    print(f"Using TEST_PREFIX: {TEST_PREFIX}")

    collections = [
        "user_profiles",
        "subjects",
        "modules",
        "activities",
        "assessments",
        "quizzes",
        "recommendations",
        "tos",
        "generated_summaries",
        "generated_quizzes",
        "generated_flashcards",
        "student_motivations",
        "diagnostic_assessments",
        "diagnostic_results",
        "study_sessions",
        "content_verifications",
        "student_analytics_reports",
    ]

    total_deleted = 0

    for collection_name in collections:
        col_ref = db.collection(collection_name)
        docs_to_delete = []
        
        try:
            query = col_ref.where(filter=FieldFilter('id', '>=', TEST_PREFIX))\
                           .where(filter=FieldFilter('id', '<', TEST_PREFIX + u'\uf8ff'))
            
            docs = query.stream()
            for doc in docs:
                if doc.id.startswith(TEST_PREFIX):
                    docs_to_delete.append(doc.reference)
        except Exception:
            all_docs = col_ref.stream()
            for doc in all_docs:
                if doc.id.startswith(TEST_PREFIX):
                    docs_to_delete.append(doc.reference)
        
        for doc_ref in docs_to_delete:
            doc_ref.delete()

        total_deleted += len(docs_to_delete)
        if len(docs_to_delete) > 0:
            print(f"✅ Deleted {len(docs_to_delete)} test document(s) from '{collection_name}'")
        else:
            print(f"ℹ️  No test data found in '{collection_name}'")

    print(f"\n🧹 Cleanup complete! Removed {total_deleted} test documents")


if __name__ == "__main__":
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
         
    from core.firebase import db
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    asyncio.run(cleanup_test_data())
