# test/realistic_populate.py
"""
REALISTIC test data population that matches the manuscript requirements.
This creates a complete, demo-ready dataset with:
- 4 Psychology subjects (matching the RPM exam)
- Diagnostic assessments for each subject
- 15 realistic students with complete learning journeys
- Study sessions (not individual activities)
- TOS-aligned content and recommendations
"""

import asyncio
from datetime import datetime, timedelta, timezone
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from database.models import get_current_iso_time
from services.role_service import get_role_id_by_designation
from datetime import date

TEST_PREFIX = "demo_"

# ============================================================
# REALISTIC SUBJECT DATA (4 RPM Exam Subjects)
# ============================================================

SUBJECTS_DATA = [
    {
        "id": f"{TEST_PREFIX}subj_psych_assessment",
        "name": "Psychological Assessment",
        "pqf_level": 7,
        "description": "Methods and tools for psychological evaluation"
    },
    {
        "id": f"{TEST_PREFIX}subj_abnormal_psych",
        "name": "Abnormal Psychology",
        "pqf_level": 7,
        "description": "Understanding psychological disorders and their assessment"
    },
    {
        "id": f"{TEST_PREFIX}subj_developmental_psych",
        "name": "Developmental Psychology",
        "pqf_level": 7,
        "description": "Human development across the lifespan"
    },
    {
        "id": f"{TEST_PREFIX}subj_industrial_org_psych",
        "name": "Industrial/Organizational Psychology",
        "pqf_level": 7,
        "description": "Psychology in workplace and organizational settings"
    }
]

def get_iso_time():
    # 1. Get the current time, making it "aware" of the UTC timezone
    now_utc = datetime.now(timezone.utc)
    
    # 2. Convert it to an ISO 8601 formatted string
    # This will look like: '2025-11-11T09:30:15.123456+00:00'
    return now_utc.isoformat()

# ============================================================
# REALISTIC TOS DATA (Simplified versions)
# ============================================================

def create_tos_for_subject(subject_id: str, subject_name: str):
    """Creates a realistic TOS document"""
    return {
        "id": f"{TEST_PREFIX}tos_{subject_id.split('_')[-1]}_v1",
        "subject_name": subject_name,
        "pqf_level": 7,
        "difficulty_distribution": {"easy": 0.30, "moderate": 0.40, "difficult": 0.30},
        "content": [
            {
                "title": "Fundamental Concepts",
                "sub_content": [
                    {
                        "purpose": "Define key terms and concepts",
                        "blooms_taxonomy": [{"remembering": 10}]
                    },
                    {
                        "purpose": "Explain theoretical foundations",
                        "blooms_taxonomy": [{"understanding": 10}]
                    }
                ],
                "no_items": 20,
                "weight_total": 0.20
            },
            {
                "title": "Application and Analysis",
                "sub_content": [
                    {
                        "purpose": "Apply concepts to case studies",
                        "blooms_taxonomy": [{"applying": 15}]
                    },
                    {
                        "purpose": "Analyze psychological phenomena",
                        "blooms_taxonomy": [{"analyzing": 15}]
                    }
                ],
                "no_items": 30,
                "weight_total": 0.30
            },
            {
                "title": "Evaluation and Integration",
                "sub_content": [
                    {
                        "purpose": "Evaluate methods and approaches",
                        "blooms_taxonomy": [{"evaluating": 20}]
                    },
                    {
                        "purpose": "Synthesize multiple perspectives",
                        "blooms_taxonomy": [{"creating": 10}]
                    }
                ],
                "no_items": 30,
                "weight_total": 0.30
            },
            {
                "title": "Professional Practice",
                "sub_content": [
                    {
                        "purpose": "Apply ethical guidelines",
                        "blooms_taxonomy": [{"applying": 10}]
                    },
                    {
                        "purpose": "Evaluate professional scenarios",
                        "blooms_taxonomy": [{"evaluating": 10}]
                    }
                ],
                "no_items": 20,
                "weight_total": 0.20
            }
        ],
        "total_items": 100,
        "is_active": True
    }

# ============================================================
# REALISTIC STUDENT PERSONAS (15 Students)
# ============================================================

STUDENT_PERSONAS = [
    # Top Performers (5) - Will pass
    {"name": "Maria Santos", "persona": "diligent_achiever", "email": "maria.santos@student.edu"},
    {"name": "Juan Reyes", "persona": "consistent_performer", "email": "juan.reyes@student.edu"},
    {"name": "Ana Cruz", "persona": "fast_learner", "email": "ana.cruz@student.edu"},
    {"name": "Carlos Mendoza", "persona": "methodical_student", "email": "carlos.mendoza@student.edu"},
    {"name": "Sofia Rodriguez", "persona": "high_achiever", "email": "sofia.rodriguez@student.edu"},
    
    # Mid-Level Students (5) - Mixed results
    {"name": "Miguel Torres", "persona": "improving_student", "email": "miguel.torres@student.edu"},
    {"name": "Elena Ramirez", "persona": "inconsistent_performer", "email": "elena.ramirez@student.edu"},
    {"name": "Diego Flores", "persona": "late_bloomer", "email": "diego.flores@student.edu"},
    {"name": "Isabel Garcia", "persona": "average_student", "email": "isabel.garcia@student.edu"},
    {"name": "Roberto Diaz", "persona": "slow_but_steady", "email": "roberto.diaz@student.edu"},
    
    # Struggling Students (5) - At risk of failing
    {"name": "Patricia Luna", "persona": "struggling_student", "email": "patricia.luna@student.edu"},
    {"name": "Fernando Castillo", "persona": "procrastinator", "email": "fernando.castillo@student.edu"},
    {"name": "Carmen Morales", "persona": "overwhelmed_student", "email": "carmen.morales@student.edu"},
    {"name": "Luis Alvarez", "persona": "unmotivated_student", "email": "luis.alvarez@student.edu"},
    {"name": "Rosa Jimenez", "persona": "conceptual_struggler", "email": "rosa.jimenez@student.edu"},
]

# ============================================================
# DIAGNOSTIC ASSESSMENT GENERATOR
# ============================================================

def generate_diagnostic_assessment(subject_id: str, subject_name: str, tos_data: dict):
    """Creates a realistic diagnostic assessment"""
    questions = []
    q_num = 1
    
    # Generate questions for each TOS topic
    for section in tos_data["content"]:
        topic_title = section["title"]
        
        for sub in section.get("sub_content", []):
            for bloom_entry in sub.get("blooms_taxonomy", []):
                bloom_level = list(bloom_entry.keys())[0]
                count = bloom_entry[bloom_level]
                
                # Generate 2 sample questions per bloom level
                for i in range(min(2, count)):
                    questions.append({
                        "question_id": f"q{q_num}",
                        "tos_topic_title": topic_title,
                        "bloom_level": bloom_level,
                        "question": f"Sample {bloom_level} question for {topic_title}",
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

# ============================================================
# REALISTIC SCORE GENERATOR
# ============================================================

def generate_realistic_diagnostic_score(persona: str, bloom_level: str, topic: str) -> float:
    """
    Generates realistic scores based on student persona, cognitive level, and topic.
    """
    base_scores = {
        # Top performers
        "diligent_achiever": {"remembering": 95, "understanding": 92, "applying": 88, "analyzing": 85, "evaluating": 82, "creating": 80},
        "consistent_performer": {"remembering": 90, "understanding": 88, "applying": 85, "analyzing": 82, "evaluating": 80, "creating": 78},
        "fast_learner": {"remembering": 92, "understanding": 95, "applying": 90, "analyzing": 88, "evaluating": 85, "creating": 82},
        "methodical_student": {"remembering": 88, "understanding": 90, "applying": 92, "analyzing": 90, "evaluating": 88, "creating": 85},
        "high_achiever": {"remembering": 98, "understanding": 95, "applying": 92, "analyzing": 90, "evaluating": 88, "creating": 85},
        
        # Mid-level
        "improving_student": {"remembering": 75, "understanding": 72, "applying": 78, "analyzing": 75, "evaluating": 72, "creating": 70},
        "inconsistent_performer": {"remembering": 85, "understanding": 70, "applying": 75, "analyzing": 68, "evaluating": 72, "creating": 65},
        "late_bloomer": {"remembering": 70, "understanding": 72, "applying": 75, "analyzing": 78, "evaluating": 80, "creating": 75},
        "average_student": {"remembering": 75, "understanding": 75, "applying": 75, "analyzing": 75, "evaluating": 75, "creating": 75},
        "slow_but_steady": {"remembering": 78, "understanding": 75, "applying": 72, "analyzing": 70, "evaluating": 68, "creating": 65},
        
        # Struggling
        "struggling_student": {"remembering": 65, "understanding": 62, "applying": 58, "analyzing": 55, "evaluating": 52, "creating": 50},
        "procrastinator": {"remembering": 60, "understanding": 58, "applying": 55, "analyzing": 52, "evaluating": 50, "creating": 48},
        "overwhelmed_student": {"remembering": 68, "understanding": 65, "applying": 60, "analyzing": 58, "evaluating": 55, "creating": 52},
        "unmotivated_student": {"remembering": 62, "understanding": 60, "applying": 58, "analyzing": 55, "evaluating": 52, "creating": 50},
        "conceptual_struggler": {"remembering": 75, "understanding": 60, "applying": 55, "analyzing": 50, "evaluating": 48, "creating": 45},
    }
    
    base_score = base_scores.get(persona, {}).get(bloom_level, 70)
    
    # Add realistic variation (+/- 5%)
    variation = random.uniform(-5, 5)
    final_score = max(0, min(100, base_score + variation))
    
    return round(final_score, 1)

# ============================================================
# MAIN POPULATION FUNCTION
# ============================================================

async def populate_realistic_data():
    """Populates the database with a complete, realistic dataset"""
    
    print("🚀 Starting REALISTIC test data population...")
    print("=" * 60)
    
    # Get student role
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("❌ CRITICAL: 'student' role not found!")
        return
    
    # 1. CREATE SUBJECTS AND TOS
    print("\n📚 Creating 4 Psychology subjects with TOS...")
    for subj_data in SUBJECTS_DATA:
        # Create subject
        subj_ref = db.collection("subjects").document(subj_data["id"])
        tos_data = create_tos_for_subject(subj_data["id"], subj_data["name"])
        
        subj_ref.set({
            "id": subj_data["id"],
            "subject_id": subj_data["id"],
            "subject_name": subj_data["name"],
            "pqf_level": subj_data["pqf_level"],
            "active_tos_id": tos_data["id"],
            "deleted": False
        })
        
        # Create TOS
        tos_ref = db.collection("tos").document(tos_data["id"])
        tos_ref.set(tos_data)
        
        # Create Diagnostic Assessment
        diag_data = generate_diagnostic_assessment(subj_data["id"], subj_data["name"], tos_data)
        diag_ref = db.collection("diagnostic_assessments").document(diag_data["id"])
        diag_ref.set(diag_data)
        
        print(f"  ✅ {subj_data['name']}")
        print(f"     - TOS: {tos_data['id']}")
        print(f"     - Diagnostic: {diag_data['id']} ({diag_data['total_items']} questions)")
    
    # 2. CREATE STUDENTS
    print(f"\n👥 Creating {len(STUDENT_PERSONAS)} realistic students...")
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        
        db.collection("user_profiles").document(student_id).set({
            "id": student_id,
            "email": student["email"],
            "first_name": student["name"].split()[0],
            "last_name": student["name"].split()[1],
            "role_id": student_role_id,
            "pre_assessment_score": None,  # Will be set after diagnostic
            "progress": {},
            "created_at": get_iso_time(),
            "deleted": False
        })
        
        print(f"  ✅ {student['name']} ({student['persona']})")
    
    # 3. GENERATE DIAGNOSTIC RESULTS FOR ALL STUDENTS
    print("\n🧪 Generating diagnostic test results...")
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        persona = student["persona"]
        
        # Take diagnostic for first 2 subjects (to simulate realistic progress)
        for subj_data in SUBJECTS_DATA[:2]:
            diag_id = f"{TEST_PREFIX}diag_{subj_data['id'].split('_')[-1]}"
            
            # Fetch the diagnostic assessment
            diag_doc = db.collection("diagnostic_assessments").document(diag_id).get()
            if not diag_doc.exists:
                continue
            
            diag = diag_doc.to_dict()
            
            # Calculate TOS performance
            tos_performance = []
            all_scores = []
            
            # Group questions by TOS topic
            from collections import defaultdict
            topic_questions = defaultdict(lambda: {"questions": [], "bloom_breakdown": defaultdict(list)})
            
            for q in diag["questions"]:
                topic_questions[q["tos_topic_title"]]["questions"].append(q)
                
            # Calculate performance for each topic
            for topic_title, data in topic_questions.items():
                topic_correct = 0
                topic_total = len(data["questions"])
                
                bloom_scores = defaultdict(lambda: {"correct": 0, "total": 0})
                
                for q in data["questions"]:
                    bloom = q["bloom_level"]
                    score = generate_realistic_diagnostic_score(persona, bloom, topic_title)
                    
                    # Simulate correct/incorrect (score > 60 = correct)
                    if score > 60:
                        topic_correct += 1
                        bloom_scores[bloom]["correct"] += 1
                    
                    bloom_scores[bloom]["total"] += 1
                    data["bloom_breakdown"][bloom].append(score)
                
                topic_score = (topic_correct / topic_total) * 100
                all_scores.append(topic_score)
                
                # Calculate bloom breakdown
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
            result_id = f"{TEST_PREFIX}result_{student_id.split('_')[-1]}_{subj_data['id'].split('_')[-1]}"
            db.collection("diagnostic_results").document(result_id).set({
                "id": result_id,
                "user_id": student_id,
                "assessment_id": diag_id,
                "subject_id": subj_data["id"],
                "overall_score": overall_score,
                "passing_status": passing_status,
                "time_taken_seconds": random.randint(2400, 3600),
                "tos_performance": tos_performance,
                "timestamp": get_iso_time(),
                "created_at": get_iso_time(),
                "deleted": False
            })
            
            print(f"  ✅ {student['name']}: {subj_data['name']} - {overall_score}% ({passing_status})")
    
    print("\n" + "=" * 60)
    print("🎉 REALISTIC DATA POPULATION COMPLETE!")
    print("\n📊 Summary:")
    print(f"  - {len(SUBJECTS_DATA)} Subjects")
    print(f"  - {len(SUBJECTS_DATA)} TOS Documents")
    print(f"  - {len(SUBJECTS_DATA)} Diagnostic Assessments")
    print(f"  - {len(STUDENT_PERSONAS)} Students")
    print(f"  - {len(STUDENT_PERSONAS) * 2} Diagnostic Results")
    print("\n✨ Ready for demo!")

if __name__ == "__main__":
    asyncio.run(populate_realistic_data())