# test/populate_test_data.py
import asyncio
import random
import sys
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# --- SETUP PATHS ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from services.role_service import get_role_id_by_designation
from test.config import TEST_PREFIX, SUBJECTS_DATA, MODULES_DATA, STUDENT_PERSONAS, PERSONA_BASE_SCORES

# --- IMPORT MODELS FOR VALIDATION ---
from database.models import (
    Subject, TOS, DiagnosticAssessment, Module, Quiz, 
    UserProfileModel, DiagnosticResult, Recommendation, 
    Activity, StudySession, ContentSection, SubContent, 
    BloomEntry, StudentProgress
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_iso_time(days_ago=0, minutes_ago=0):
    t = datetime.now(timezone.utc) - timedelta(days=days_ago, minutes=minutes_ago)
    return t.isoformat()

def generate_score(persona, bloom_level):
    config = PERSONA_BASE_SCORES.get(persona, {"default": 75, "min": 60, "max": 90})
    difficulty = 0
    if bloom_level in ["analyzing", "evaluating", "creating"]:
        difficulty = 5
    
    score = random.uniform(config["min"], config["max"]) - difficulty
    return max(0, min(100, round(score, 2)))

async def ensure_roles_exist():
    """Ensures admin, faculty, and student roles exist."""
    print("   > Checking roles...")
    roles_data = [
        {"id": "PifcrriKAGM6YdWORP5I", "designation": "admin", "label": "Admin"},
        {"id": "vhVbVsvMKiogI6rNLS7n", "designation": "faculty_member", "label": "Faculty Member"},
        {"id": "Tzc78QtZcaVbzFtpHoOL", "designation": "student", "label": "Student"}
    ]
    for role in roles_data:
        doc_ref = db.collection("roles").document(role["id"])
        if not doc_ref.get().exists:
            doc_ref.set(role)

def create_tos_model(subject_name, tos_id):
    """Generates a TOS object using Pydantic models."""
    
    # Content Sections matching TOSBase structure
    sections = [
        ContentSection(
            title="Fundamental Concepts",
            weight_total=0.2,
            no_items=20,
            sub_content=[
                SubContent(purpose="Define key terms", blooms_taxonomy=[BloomEntry(root={"remembering": 10})]),
                SubContent(purpose="Explain theories", blooms_taxonomy=[BloomEntry(root={"understanding": 10})])
            ]
        ),
        ContentSection(
            title="Application & Analysis",
            weight_total=0.5,
            no_items=50,
            sub_content=[
                SubContent(purpose="Apply concepts", blooms_taxonomy=[BloomEntry(root={"applying": 25})]),
                SubContent(purpose="Analyze cases", blooms_taxonomy=[BloomEntry(root={"analyzing": 25})])
            ]
        ),
        ContentSection(
            title="Evaluation & Synthesis",
            weight_total=0.3,
            no_items=30,
            sub_content=[
                SubContent(purpose="Evaluate methods", blooms_taxonomy=[BloomEntry(root={"evaluating": 15})]),
                SubContent(purpose="Create plans", blooms_taxonomy=[BloomEntry(root={"creating": 15})])
            ]
        )
    ]
    
    return TOS(
        id=tos_id,
        subject_name=subject_name,
        pqf_level=7,
        difficulty_distribution={"easy": 0.3, "moderate": 0.4, "difficult": 0.3},
        content=sections,
        total_items=100,
        created_at=get_iso_time()
    )

# ============================================================
# MAIN POPULATION LOGIC
# ============================================================

async def populate_test_data():
    print("\n🚀 STARTING FULL DATASET SIMULATION...")
    await ensure_roles_exist()
    
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("❌ Error: 'student' role not found in DB.")
        return

    # ---------------------------------------------------------
    # 1. CREATE ACADEMIC CONTENT (Subjects, TOS, Modules, Quizzes)
    # ---------------------------------------------------------
    print("\n📚 Generating Academic Content...")
    
    created_content_map = defaultdict(list) # subject_id -> list of module objects
    
    for subj_data in SUBJECTS_DATA:
        subj_id = subj_data["id"]
        
        # B. Create TOS (Table of Specifications)
        tos_id = f"{TEST_PREFIX}tos_{subj_id.split('_')[-1]}"
        tos_model = create_tos_model(subj_data["subject_name"], tos_id)
        db.collection("tos").document(tos_id).set(tos_model.to_dict())

        # A. Create Subject (Linked to TOS)
        subject_model = Subject(
            **subj_data,
            subject_id=subj_id,
            active_tos_id=tos_id
        )
        db.collection("subjects").document(subj_id).set(subject_model.to_dict())
        print(f"   + Subject: {subject_model.subject_name}")

        # C. Create Diagnostic Assessment
        diag_id = f"{TEST_PREFIX}diag_{subj_id.split('_')[-1]}"
        diag_model = DiagnosticAssessment(
            id=diag_id,
            subject_id=subj_id,
            title=f"Diagnostic: {subject_model.subject_name}",
            total_items=50,
            passing_score=75.0,
            time_limit_minutes=60,
            questions=[], # Simplified for demo
            created_at=get_iso_time()
        )
        db.collection("diagnostic_assessments").document(diag_id).set(diag_model.to_dict())

        # D. Create Modules & Quizzes
        modules_list = MODULES_DATA.get(subj_id, [])
        for idx, mod_def in enumerate(modules_list):
            mod_id = f"{TEST_PREFIX}mod_{subj_id.split('_')[-1]}_{idx}"
            
            # Create Module
            module_model = Module(
                id=mod_id,
                subject_id=subj_id,
                title=mod_def["title"],
                bloom_level=mod_def["bloom_level"],
                material_type=mod_def["material_type"],
                estimated_time=mod_def["estimated_time"],
                purpose=mod_def["purpose"],
                cover_image_url="https://via.placeholder.com/150", 
                author="Faculty",
                short_description=f"Learn about {mod_def['title']}",
                created_at=get_iso_time()
            )
            db.collection("modules").document(mod_id).set(module_model.to_dict())
            created_content_map[subj_id].append(module_model)

            # Create Associated Quiz
            quiz_id = f"{TEST_PREFIX}quiz_{mod_id.split('_')[-1]}"
            quiz_model = Quiz(
                id=quiz_id,
                question_id=f"q_{quiz_id}",
                subject_id=subj_id,
                topic_title=mod_def["title"],
                bloom_level=mod_def["bloom_level"],
                question=f"Sample question for {mod_def['title']}",
                options=["A", "B", "C", "D"],
                answer="A",
                created_at=get_iso_time()
            )
            db.collection("quizzes").document(quiz_id).set(quiz_model.to_dict())

    # ---------------------------------------------------------
    # 2. CREATE STUDENTS & ACTIVITY HISTORY
    # ---------------------------------------------------------
    print(f"\n👥 Creating {len(STUDENT_PERSONAS)} Students & simulating history...")

    for i, student_def in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        persona = student_def["persona"]
        first_name = student_def["name"].split()[0]
        last_name = student_def["name"].split()[1]

        # A. Create User Profile
        # Initialize progress dictionary
        progress_dict = {
            "Fundamental Concepts": random.uniform(0.1, 0.9),
            "Application & Analysis": random.uniform(0.1, 0.9),
            "Evaluation & Synthesis": random.uniform(0.1, 0.9)
        }
        
        profile_model = UserProfileModel(
            id=student_id,
            email=student_def["email"],
            first_name=first_name,
            last_name=last_name,
            nickname=first_name,
            user_name=f"{first_name.lower()}_{last_name.lower()}",
            role_id=student_role_id,
            profile_picture=student_def["img"],
            image=student_def["img"],
            ai_confidence=random.uniform(0.6, 0.95),
            progress=StudentProgress(root=progress_dict),
            created_at=get_iso_time(days_ago=30)
        )
        # Note: We use .to_dict() but handle the 'status' field manually as it's not in the base model
        profile_data = profile_model.to_dict()
        profile_data["status"] = "offline" 
        db.collection("user_profiles").document(student_id).set(profile_data)
        
        print(f"   > Processed {student_def['name']} ({persona})...")

        # B. Simulate Diagnostic Results (Take 2 random subjects)
        taken_subjects = random.sample(SUBJECTS_DATA, 2)
        for subj in taken_subjects:
            diag_id = f"{TEST_PREFIX}diag_{subj['id'].split('_')[-1]}"
            diag_score = generate_score(persona, "understanding") 
            result_id = f"{TEST_PREFIX}res_{student_id.split('_')[-1]}_{subj['id'].split('_')[-1]}"
            
            # Mock TOS Performance
            tos_perf_list = []
            for section in ["Fundamental Concepts", "Application & Analysis"]:
                tos_perf_list.append({
                    "topic_title": section,
                    "total_questions": 20,
                    "correct_answers": int(20 * (diag_score/100)),
                    "score_percentage": diag_score,
                    "bloom_breakdown": {"remembering": diag_score, "analyzing": diag_score - 5}
                })

            diagnostic_result_model = DiagnosticResult(
                id=result_id,
                user_id=student_id,
                assessment_id=diag_id,
                subject_id=subj["id"],
                overall_score=diag_score,
                passing_status="passed" if diag_score >= 75 else "failed",
                time_taken_seconds=random.randint(1800, 3000),
                tos_performance=tos_perf_list,
                timestamp=get_iso_time(days_ago=random.randint(10, 20))
            )
            db.collection("diagnostic_results").document(result_id).set(diagnostic_result_model.to_dict())

            # Generate Recommendations based on this result (Mock)
            if diag_score < 85:
                rec_id = f"{TEST_PREFIX}rec_{result_id.split('_')[-1]}"
                recommendation_model = Recommendation(
                    id=rec_id,
                    user_id=student_id,
                    subject_id=subj["id"],
                    recommended_topic="Application & Analysis",
                    recommended_modules=[], 
                    recommended_quizzes=[],
                    bloom_focus="analyzing",
                    priority="high" if diag_score < 60 else "medium",
                    reason="Diagnostic result indicates weakness in analysis.",
                    diagnostic_result_id=result_id,
                    confidence=0.85,
                    timestamp=get_iso_time()
                )
                db.collection("recommendations").document(rec_id).set(recommendation_model.to_dict())

        # C. Simulate Activities & Study Sessions
        num_sessions = random.randint(5, 10)
        total_activities = 0
        total_score_accum = 0

        for sess_idx in range(num_sessions):
            sess_id = f"{TEST_PREFIX}sess_{student_id.split('_')[-1]}_{sess_idx}"
            sess_subject = random.choice(SUBJECTS_DATA)
            sess_modules = created_content_map[sess_subject["id"]]
            
            if not sess_modules: continue

            activities_in_session = []
            session_scores = []
            
            # Do 2-3 activities per session
            for act_idx in range(random.randint(2, 3)):
                mod = random.choice(sess_modules)
                score = generate_score(persona, mod.bloom_level)
                
                act_id = f"{TEST_PREFIX}act_{student_id.split('_')[-1]}_{sess_idx}_{act_idx}"
                
                activity_model = Activity(
                    id=act_id,
                    user_id=student_id,
                    subject_id=sess_subject["id"],
                    activity_type="module_completion",
                    activity_ref=mod.id,
                    bloom_level=mod.bloom_level,
                    score=score,
                    completion_rate=1.0,
                    duration=mod.estimated_time,
                    created_at=get_iso_time(days_ago=random.randint(1, 10))
                )
                db.collection("activities").document(act_id).set(activity_model.to_dict())
                
                activities_in_session.append(act_id)
                session_scores.append(score)
                total_activities += 1
                total_score_accum += score

            # Create Study Session Log
            sess_avg = sum(session_scores) / len(session_scores) if session_scores else 0
            
            study_session_model = StudySession(
                id=sess_id,
                user_id=student_id,
                subject_id=sess_subject["id"],
                session_type="review",
                activity_ids=activities_in_session,
                duration_seconds=random.randint(1200, 3600),
                avg_score=round(sess_avg, 2),
                completion_status="completed",
                timestamp=get_iso_time(days_ago=random.randint(1, 10))
            )
            db.collection("study_sessions").document(sess_id).set(study_session_model.to_dict())

        # D. Generate Student Analytics Report (Snapshot)
        avg_overall = total_score_accum / total_activities if total_activities > 0 else 0
        db.collection("student_analytics_reports").document(student_id).set({
            "student_id": student_id,
            "summary": {
                "average_score": round(avg_overall, 2),
                "total_activities": total_activities,
                "completion_rate": 0.95, 
                "total_sessions": num_sessions,
                "last_active": get_iso_time()
            },
            "performance_by_bloom": {
                "remembering": generate_score(persona, "remembering"),
                "analyzing": generate_score(persona, "analyzing"),
                "creating": generate_score(persona, "creating")
            },
            "last_updated": get_iso_time()
        })

    print(f"\n✅ DONE. Populated:")
    print(f"   - {len(SUBJECTS_DATA)} Subjects with TOS")
    print(f"   - {len(SUBJECTS_DATA) * 4} Modules & Quizzes")
    print(f"   - {len(STUDENT_PERSONAS)} Students with Profiles")
    print(f"   - {len(STUDENT_PERSONAS) * 2} Diagnostic Results")
    print(f"   - ~{len(STUDENT_PERSONAS) * 8} Study Sessions & Activities")

if __name__ == "__main__":
    asyncio.run(populate_test_data())