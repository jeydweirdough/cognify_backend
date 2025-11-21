import asyncio
from datetime import datetime, timedelta, timezone
import random
import sys
from pathlib import Path
from collections import defaultdict

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from firebase_admin import auth
from services.role_service import get_role_id_by_designation

# =============================================================================
# 1. CONFIGURATION & CONSTANTS
# =============================================================================

TEST_PREFIX = "demo_"

def get_iso_time(days_offset=0):
    dt = datetime.now(timezone.utc) + timedelta(days=days_offset)
    return dt.isoformat()

# 🎨 Mobile UI Colors
PALETTE = [
    {"icon_color": "#D8C713", "icon_bg": "#F0F5D5", "card_bg": "#FDFFB8"},
    {"icon_color": "#4C609B", "icon_bg": "#E2E6F2", "card_bg": "#FFE8CD"},
    {"icon_color": "#30C49F", "icon_bg": "#FCF5EE", "card_bg": "#FCF5EE"},
    {"icon_color": "#D38A4D", "icon_bg": "#F9ECE3", "card_bg": "#F4F8D3"},
]

# FIXED: Changed 'name' to 'subject_name' to match Pydantic Model
SUBJECTS_DATA = [
    {
        "id": f"{TEST_PREFIX}subj_psych_assessment",
        "subject_name": "Psychological Assessment", # <--- RENAMED
        "pqf_level": 7,
        "description": "Understanding and using psychological tests to measure behavior and mental processes.",
        "icon_name": "book",
    },
    {
        "id": f"{TEST_PREFIX}subj_abnormal_psych",
        "subject_name": "Abnormal Psychology", # <--- RENAMED
        "pqf_level": 7,
        "description": "Study of psychological disorders, their causes, and treatments.",
        "icon_name": "brain",
    },
    {
        "id": f"{TEST_PREFIX}subj_dev_psych",
        "subject_name": "Developmental Psychology", # <--- RENAMED
        "pqf_level": 7,
        "description": "Study of human growth and changes from childhood to adulthood.",
        "icon_name": "child_care",
    },
    {
        "id": f"{TEST_PREFIX}subj_io_psych",
        "subject_name": "Industrial/Organizational Psychology", # <--- RENAMED
        "pqf_level": 7,
        "description": "Application of psychology to workplace behavior and performance.",
        "icon_name": "business",
    }
]

# 👨‍🏫 2 FACULTY MEMBERS
FACULTY_DATA = [
    {"name": "Dr. Victor Frankenstein", "email": "victor.f@faculty.edu", "designation": "faculty_member"},
    {"name": "Prof. Minerva McGonagall", "email": "minerva.m@faculty.edu", "designation": "faculty_member"},
]

# 👩‍🎓 15 STUDENTS (Diverse Personas)
STUDENT_PERSONAS = [
    # High Achievers
    {"name": "Maria Santos", "persona": "high_achiever", "email": "maria.santos@student.edu"},
    {"name": "James Reid", "persona": "high_achiever", "email": "james.reid@student.edu"},
    {"name": "Sofia Andres", "persona": "high_achiever", "email": "sofia.andres@student.edu"},
    {"name": "Daniel Padilla", "persona": "high_achiever", "email": "daniel.padilla@student.edu"},
    {"name": "Kathryn Bernardo", "persona": "high_achiever", "email": "kathryn.bernardo@student.edu"},
    
    # Average Students
    {"name": "Juan Reyes", "persona": "average_student", "email": "juan.reyes@student.edu"},
    {"name": "Nadine Lustre", "persona": "average_student", "email": "nadine.lustre@student.edu"},
    {"name": "Enrique Gil", "persona": "average_student", "email": "enrique.gil@student.edu"},
    {"name": "Liza Soberano", "persona": "average_student", "email": "liza.soberano@student.edu"},
    {"name": "Joshua Garcia", "persona": "average_student", "email": "joshua.garcia@student.edu"},
    
    # Struggling Students
    {"name": "Patricia Luna", "persona": "struggling_student", "email": "patricia.luna@student.edu"},
    {"name": "Baron Geisler", "persona": "struggling_student", "email": "baron.geisler@student.edu"},
    {"name": "Kylie Padilla", "persona": "struggling_student", "email": "kylie.padilla@student.edu"},
    {"name": "Aljur Abrenica", "persona": "struggling_student", "email": "aljur.abrenica@student.edu"},
    {"name": "Coco Martin", "persona": "struggling_student", "email": "coco.martin@student.edu"},
]

# =============================================================================
# 2. GENERATORS
# =============================================================================

def create_tos_data(subject_id, subject_name):
    """Creates a valid TOS structure matching models.py"""
    return {
        "id": f"{TEST_PREFIX}tos_{subject_id.split('_')[-1]}",
        "subject_name": subject_name,
        "pqf_level": 7,
        "difficulty_distribution": {"easy": 0.3, "moderate": 0.4, "difficult": 0.3},
        "total_items": 100,
        "is_active": True,
        "created_at": get_iso_time(),
        "content": [
            {
                "title": "Core Concepts",
                "no_items": 40,
                "weight_total": 0.4,
                "sub_content": [
                    {"purpose": "Definitions", "blooms_taxonomy": [{"remembering": 20}]},
                    {"purpose": "Theories", "blooms_taxonomy": [{"understanding": 20}]}
                ]
            },
            {
                "title": "Application",
                "no_items": 60,
                "weight_total": 0.6,
                "sub_content": [
                    {"purpose": "Case Studies", "blooms_taxonomy": [{"applying": 30}, {"analyzing": 30}]}
                ]
            }
        ]
    }

def create_diagnostic_assessment(subject_id, subject_name, tos_topics):
    """Creates a diagnostic assessment with questions mapped to TOS topics"""
    questions = []
    for i, topic in enumerate(tos_topics):
        questions.append({
            "question_id": f"q_{i}",
            "topic_title": topic,
            "tos_topic_title": topic, 
            "bloom_level": "remembering",
            "question": f"Diagnostic question about {topic}?",
            "options": ["Answer A", "Answer B", "Answer C", "Answer D"],
            "answer": "Answer A",
            "cognitive_weight": 1.0
        })

    return {
        "id": f"{TEST_PREFIX}diag_{subject_id.split('_')[-1]}",
        "subject_id": subject_id,
        "title": f"Diagnostic: {subject_name}",
        "instructions": "Complete this assessment to identify your weak areas.",
        "total_items": len(questions),
        "questions": questions,
        "passing_score": 75.0,
        "type": "diagnostic",
        "created_at": get_iso_time()
    }

# =============================================================================
# 3. MAIN POPULATION FUNCTION
# =============================================================================

async def populate_test_data():
    print("🚀 Starting FIXED test data population...")
    print("=" * 60)

    # 0. Setup Roles
    student_role_id = await get_role_id_by_designation("student")
    faculty_role_id = await get_role_id_by_designation("faculty_member")
    
    if not student_role_id or not faculty_role_id:
        print("❌ Roles not found. Please run seed_roles first.")
        return

    created_modules = defaultdict(list)
    created_diagnostics = {}

    # 1. SUBJECTS, TOS, & DIAGNOSTICS
    print("\n📚 Creating Subjects ecosystem...")
    for idx, subj in enumerate(SUBJECTS_DATA):
        # Use subject_name here
        tos_data = create_tos_data(subj["id"], subj["subject_name"])
        db.collection("tos").document(tos_data["id"]).set(tos_data)
        
        tos_topics = [c["title"] for c in tos_data["content"]]
        diag_data = create_diagnostic_assessment(subj["id"], subj["subject_name"], tos_topics)
        db.collection("diagnostic_assessments").document(diag_data["id"]).set(diag_data)
        created_diagnostics[subj["id"]] = diag_data["id"]

        colors = PALETTE[idx % len(PALETTE)]
        db.collection("subjects").document(subj["id"]).set({
            **subj,
            **colors,
            "subject_id": subj["id"],
            "active_tos_id": tos_data["id"],
            "created_at": get_iso_time(),
            "deleted": False
        })
        print(f"  ✅ Subject: {subj['subject_name']}")

        # 2. CONTENT (Modules)
        for m_idx in range(1, 4):
            mod_id = f"{subj['id']}_mod_{m_idx}"
            gen_summary_id = f"{mod_id}_summary"
            gen_quiz_id = f"{mod_id}_quiz"
            gen_flash_id = f"{mod_id}_flash"

            # Create placeholder generated content to satisfy links
            db.collection("generated_summaries").document(gen_summary_id).set({
                "id": gen_summary_id, "module_id": mod_id, "subject_id": subj["id"],
                "summary_text": "Summary...", "source_url": "http://x.com", "source_char_count": 100
            })
            db.collection("generated_quizzes").document(gen_quiz_id).set({
                "id": gen_quiz_id, "module_id": mod_id, "subject_id": subj["id"],
                "questions": [{"question": "Q?", "options": ["A","B"], "answer": "A"}]
            })

            module_data = {
                "id": mod_id,
                "subject_id": subj["id"],
                "title": f"{subj['subject_name']} - Module {m_idx}",
                "description": f"Learn about topic {m_idx}",
                "author": "Dr. Cognify",
                "cover_image_url": "https://placehold.co/600x400/png",
                "material_type": "pdf",
                "bloom_level": "understanding",
                "estimated_time": 30,
                "generated_summary_id": gen_summary_id,
                "generated_quiz_id": gen_quiz_id,
                "generated_flashcards_id": gen_flash_id,
                "created_at": get_iso_time(),
                "deleted": False
            }
            db.collection("modules").document(mod_id).set(module_data)
            created_modules[subj["id"]].append(module_data)

    # 3. CREATE FACULTY MEMBERS
    print("\n👨‍🏫 Creating 2 Faculty Members...")
    for faculty in FACULTY_DATA:
        uid = f"{TEST_PREFIX}{faculty['name'].replace(' ', '_').lower().replace('.', '')}"
        try:
            auth.create_user(uid=uid, email=faculty['email'], password="demo123")
        except Exception:
            pass 
        
        db.collection("user_profiles").document(uid).set({
            "id": uid,
            "email": faculty['email'],
            "first_name": faculty['name'].split()[0],
            "last_name": faculty['name'].split()[-1],
            "role_id": faculty_role_id,
            "status": "offline",
            "created_at": get_iso_time()
        })
        print(f"  👤 {faculty['name']} ({faculty['email']})")

    # 4. CREATE STUDENTS & JOURNEYS
    print(f"\n👥 Creating {len(STUDENT_PERSONAS)} Students and simulation journeys...")
    for student in STUDENT_PERSONAS:
        uid = f"{TEST_PREFIX}{student['name'].replace(' ', '_').lower()}"
        
        try:
            auth.create_user(uid=uid, email=student['email'], password="demo123")
        except Exception:
            pass 
            
        db.collection("user_profiles").document(uid).set({
            "id": uid,
            "email": student['email'],
            "first_name": student['name'].split()[0],
            "last_name": student['name'].split()[-1],
            "role_id": student_role_id,
            "progress": {},
            "status": "offline",
            "created_at": get_iso_time()
        })
        
        # Simulate interactions for the first subject
        target_subj_id = SUBJECTS_DATA[0]["id"]
        target_diag_id = created_diagnostics[target_subj_id]
        target_modules = created_modules[target_subj_id]

        # Determine score based on persona
        if student["persona"] == "high_achiever":
            score = 88.0
        elif student["persona"] == "average_student":
            score = 76.0
        else:
            score = 60.0
        
        # Create Diagnostic Result
        result_id = f"{uid}_res_{target_subj_id.split('_')[-1]}"
        db.collection("diagnostic_results").document(result_id).set({
            "id": result_id,
            "user_id": uid,
            "assessment_id": target_diag_id,
            "subject_id": target_subj_id,
            "overall_score": score,
            "passing_status": "passed" if score >= 75 else "failed",
            "time_taken_seconds": 1200,
            "timestamp": get_iso_time(-5),
            "tos_performance": [] 
        })

        # Only create extensive history for non-struggling students
        if student["persona"] != "struggling_student":
            rec_id = f"{uid}_rec_1"
            db.collection("recommendations").document(rec_id).set({
                "id": rec_id,
                "user_id": uid,
                "subject_id": target_subj_id,
                "recommended_modules": [m["id"] for m in target_modules[:2]],
                "bloom_focus": "applying",
                "priority": "high",
                "reason": "Based on your diagnostic result",
                "diagnostic_result_id": result_id,
                "confidence": 0.95,
                "timestamp": get_iso_time(-4)
            })

            act1_id = f"{uid}_act_1"
            db.collection("activities").document(act1_id).set({
                "id": act1_id,
                "user_id": uid,
                "subject_id": target_subj_id,
                "activity_type": "module",
                "activity_ref": target_modules[0]["id"],
                "score": None,
                "completion_rate": 1.0,
                "duration": 900,
                "timestamp": get_iso_time(-2)
            })
        
        print(f"  👤 {student['name']} - {student['persona']}")

    print("\n✅ Database populated with 15 Students and 2 Faculty!")
    print("🔑 Password for all users: demo123")

if __name__ == "__main__":
    asyncio.run(populate_test_data())