"""
REALISTIC test data population for Cognify Backend.
Based on the manuscript requirements with authentic learning patterns.

UPDATED: This script now populates data for ALL major routes:
- Subjects, TOS, DiagnosticAssessments, Modules
- Students, DiagnosticResults
- Quizzes (Manual)
- Generated_Content (Summaries, Quizzes, Flashcards)
- Recommendations (from diagnostics)
- StudySessions (grouping activities)
- ContentVerifications (for modules/quizzes)
"""

import asyncio
from datetime import datetime, timedelta, timezone
import random
import sys
from pathlib import Path
from collections import defaultdict

# --- Add base directory to path ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
# ----------------------------------

from core.firebase import db
from database.models import get_current_iso_time
from services.role_service import get_role_id_by_designation
from firebase_admin import auth
from .config import (
    TEST_PREFIX, SUBJECTS_DATA, STUDENT_PERSONAS, PERSONA_BASE_SCORES
)

# --- Global counters for summary ---
summary_counters = defaultdict(int)

def get_iso_time():
    return datetime.now(timezone.utc).isoformat()


def create_tos_for_subject(subject_id: str, subject_name: str):
    """Creates a realistic TOS document"""
    summary_counters["TOS"] += 1
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
                
                # Create a few sample questions
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
    
    summary_counters["DiagnosticAssessments"] += 1
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
    """
    base_scores = PERSONA_BASE_SCORES.get(persona, {})
    base_score = base_scores.get(bloom_level, 70)
    
    var = random.uniform(-variation, variation)
    final_score = max(0, min(100, base_score + var))
    
    return round(final_score, 1)

def create_quizzes_for_subject(subject_id: str, subject_name: str, modules: list):
    """Create sample manual quizzes for a subject"""
    quizzes = []
    for i, module in enumerate(modules):
        if i % 2 == 0:  # Create a quiz for every other module
            quiz_id = f"{TEST_PREFIX}quiz_{subject_id.split('_')[-1]}_{i+1}"
            quizzes.append({
                "id": quiz_id,
                "subject_id": subject_id,
                "topic_title": module["title"],
                "bloom_level": module["bloom_level"],
                "question": f"What is a key concept from '{module['title']}'?",
                "options": ["Correct Answer", "Wrong Answer 1", "Wrong Answer 2", "Wrong Answer 3"],
                "answer": "Correct Answer",
                "created_at": get_iso_time(),
                "deleted": False
            })
    
    for quiz in quizzes:
        db.collection("quizzes").document(quiz["id"]).set(quiz)
        summary_counters["Quizzes"] += 1
    return quizzes

def create_mock_generated_content(module_id: str, subject_id: str, title: str, bloom: str, url: str):
    """Creates mock AI summary, quiz, and flashcards for a module"""
    
    # 1. Create Summary
    summary_id = f"{TEST_PREFIX}summary_{module_id.split('_')[-1]}"
    summary = {
        "id": summary_id,
        "module_id": module_id,
        "subject_id": subject_id,
        "summary_text": f"This is an AI-generated summary for the module '{title}'. It focuses on {bloom} concepts.",
        "source_url": url,
        "source_char_count": random.randint(5000, 10000),
        "tos_topic_title": "Fundamental Concepts", # Mock alignment
        "aligned_bloom_level": bloom,
        "created_at": get_iso_time(),
        "deleted": False
    }
    db.collection("generated_summaries").document(summary_id).set(summary)
    summary_counters["GeneratedSummaries"] += 1

    # 2. Create AI Quiz
    quiz_id = f"{TEST_PREFIX}genquiz_{module_id.split('_')[-1]}"
    ai_quiz = {
        "id": quiz_id,
        "module_id": module_id,
        "subject_id": subject_id,
        "questions": [
            {
                "question": f"AI Question 1 for '{title}' ({bloom})?",
                "options": ["AI Option A", "AI Option B", "AI Option C", "AI Option D"],
                "answer": "AI Option A",
                "tos_topic_title": "Fundamental Concepts",
                "aligned_bloom_level": bloom
            },
            {
                "question": f"AI Question 2 for '{title}' ({bloom})?",
                "options": ["AI Option 1", "AI Option 2", "AI Option 3", "AI Option 4"],
                "answer": "AI Option 2",
                "tos_topic_title": "Application and Analysis",
                "aligned_bloom_level": bloom
            }
        ],
        "source_url": url,
        "source_char_count": random.randint(5000, 10000),
        "tos_topic_title": "Fundamental Concepts",
        "aligned_bloom_level": bloom,
        "created_at": get_iso_time(),
        "deleted": False
    }
    db.collection("generated_quizzes").document(quiz_id).set(ai_quiz)
    summary_counters["GeneratedQuizzes"] += 1
    
    # 3. Create AI Flashcards
    flashcards_id = f"{TEST_PREFIX}flash_{module_id.split('_')[-1]}"
    flashcards = {
        "id": flashcards_id,
        "module_id": module_id,
        "subject_id": subject_id,
        "flashcards": [
            {
                "question": f"AI Flashcard Q1: What is {title}?",
                "answer": f"AI Flashcard A1: It's about {bloom}.",
                "tos_topic_title": "Fundamental Concepts",
                "aligned_bloom_level": bloom
            },
            {
                "question": f"AI Flashcard Q2: Define a key term from {title}.",
                "answer": f"AI Flashcard A2: A key term is...",
                "tos_topic_title": "Fundamental Concepts",
                "aligned_bloom_level": "remembering"
            }
        ],
        "source_url": url,
        "source_char_count": random.randint(5000, 10000),
        "tos_topic_title": "Fundamental Concepts",
        "aligned_bloom_level": bloom,
        "created_at": get_iso_time(),
        "deleted": False
    }
    db.collection("generated_flashcards").document(flashcards_id).set(flashcards)
    summary_counters["GeneratedFlashcards"] += 1

    return summary_id, quiz_id, flashcards_id

def create_verification_tasks(content_list: list, content_type: str):
    """Creates 'pending' verification tasks for modules or quizzes"""
    for i, content in enumerate(content_list):
        if i % 3 == 0: # Create a task for every 3rd item
            task_id = f"{TEST_PREFIX}verify_{content_type}_{content['id'].split('_')[-1]}"
            task = {
                "id": task_id,
                "content_id": content["id"],
                "content_type": content_type,
                "verified_by": "pending", # Unassigned
                "verification_status": "pending",
                "tos_alignment_confirmed": False,
                "bloom_level_confirmed": False,
                "feedback": None,
                "revision_notes": None,
                "created_at": get_iso_time(),
                "deleted": False
            }
            db.collection("content_verifications").document(task_id).set(task)
            summary_counters["ContentVerifications"] += 1

def create_modules_for_subject(subject_id: str, subject_name: str):
    """Create sample modules for a subject"""
    bloom_levels = ["remembering", "understanding", "applying", "analyzing", "evaluating", "creating"]
    modules = []
    
    for i, bloom in enumerate(bloom_levels, 1):
        module_id = f"{TEST_PREFIX}mod_{subject_id.split('_')[-1]}_{bloom[:3]}_{i}"
        
        # --- Create mock AI content ---
        (sum_id, qz_id, fl_id) = create_mock_generated_content(
            module_id, subject_id, f"{subject_name}: {bloom.capitalize()} Module {i}",
            bloom, "https://example.com/module.pdf"
        )
        
        module_data = {
            "id": module_id,
            "subject_id": subject_id,
            "title": f"{subject_name}: {bloom.capitalize()} Module {i}",
            "purpose": f"Master {bloom} level concepts",
            "bloom_level": bloom,
            "material_type": "reading",
            "material_url": "https://example.com/module.pdf",
            "generated_summary_id": sum_id,   # --- Link to AI content
            "generated_quiz_id": qz_id,     # --- Link to AI content
            "generated_flashcards_id": fl_id, # --- Link to AI content
            "created_at": get_iso_time(),
            "deleted": False
        }
        modules.append(module_data)
        db.collection("modules").document(module_id).set(module_data)
        summary_counters["Modules"] += 1
    
    return modules

def create_study_sessions_for_student(student_id: str, persona: str, subject_id: str, modules: list, quizzes: list, num_sessions: int = 5):
    """Create realistic study sessions, each with multiple activities"""
    now = datetime.now(timezone.utc)
    
    for i in range(num_sessions):
        session_id = f"{TEST_PREFIX}session_{student_id.split('_')[-1]}_{i+1}"
        session_type = random.choice(["review", "practice"])
        activities_in_session = []
        session_scores = []
        session_duration = 0
        
        # Create 2-4 activities per session
        num_activities = random.randint(2, 4)
        for j in range(num_activities):
            # 70% chance of module, 30% chance of quiz
            if random.random() < 0.7:
                content = random.choice(modules)
                activity_type = "module"
                activity_ref = content["id"]
            else:
                if not quizzes: continue # Skip if no quizzes
                content = random.choice(quizzes)
                activity_type = "quiz"
                activity_ref = content["id"]
            
            bloom_level = content["bloom_level"]
            score = generate_realistic_score(persona, bloom_level)
            duration = random.randint(600, 1800) # 10-30 mins
            
            activity_id = f"{TEST_PREFIX}act_{session_id.split('_')[-1]}_{j+1}"
            timestamp = (now - timedelta(days=num_sessions - i, hours=j)).isoformat()
            
            activity = {
                "id": activity_id,
                "user_id": student_id,
                "subject_id": subject_id,
                "activity_type": activity_type,
                "activity_ref": activity_ref,
                "bloom_level": bloom_level,
                "score": score,
                "completion_rate": random.uniform(0.85, 1.0) if score > 50 else random.uniform(0.5, 0.85),
                "duration": duration,
                "timestamp": timestamp,
                "created_at": timestamp,
                "deleted": False
            }
            db.collection("activities").document(activity_id).set(activity)
            summary_counters["Activities"] += 1
            
            activities_in_session.append(activity_id)
            session_scores.append(score)
            session_duration += duration

        if not activities_in_session:
            continue

        session_timestamp = (now - timedelta(days=num_sessions - i)).isoformat()
        study_session = {
            "id": session_id,
            "user_id": student_id,
            "subject_id": subject_id,
            "session_type": session_type,
            "activity_ids": activities_in_session,
            "duration_seconds": session_duration,
            "avg_score": round(sum(session_scores) / len(session_scores), 2) if session_scores else 0.0,
            "completion_status": "completed",
            "timestamp": session_timestamp,
            "created_at": session_timestamp,
            "deleted": False
        }
        db.collection("study_sessions").document(session_id).set(study_session)
        summary_counters["StudySessions"] += 1

def create_recommendations_for_student(result: dict, modules: list, quizzes: list):
    """Generates Recommendations based on diagnostic results"""
    
    for tos_perf in result.get("tos_performance", []):
        # Recommend if score is below 75%
        if tos_perf.get("score_percentage", 100.0) < 75.0:
            topic_title = tos_perf["topic_title"]
            
            # Find weakest Bloom's level
            bloom_breakdown = tos_perf.get("bloom_breakdown", {})
            if not bloom_breakdown: continue
            
            weakest_bloom = min(bloom_breakdown.items(), key=lambda x: x[1])
            bloom_level = weakest_bloom[0]
            bloom_score = weakest_bloom[1]
            
            # Find matching modules/quizzes
            rec_modules = [m["id"] for m in modules if m["bloom_level"] == bloom_level][:2]
            rec_quizzes = [q["id"] for q in quizzes if q["bloom_level"] == bloom_level][:1]
            
            if not rec_modules and not rec_quizzes:
                continue # No relevant content found
                
            priority = "high" if bloom_score < 50 else "medium"
            
            rec_id = f"{TEST_PREFIX}rec_{result['user_id'].split('_')[-1]}_{result['subject_id'].split('_')[-1]}_{bloom_level[:3]}"
            recommendation = {
                "id": rec_id,
                "user_id": result["user_id"],
                "subject_id": result["subject_id"],
                "recommended_topic": topic_title,
                "recommended_modules": rec_modules,
                "recommended_quizzes": rec_quizzes,
                "bloom_focus": bloom_level,
                "priority": priority,
                "reason": (
                    f"Diagnostic score in '{topic_title}' was {tos_perf['score_percentage']}%. "
                    f"Weakest area: '{bloom_level}' ({bloom_score}%)."
                ),
                "diagnostic_result_id": result["id"],
                "confidence": 0.90,
                "timestamp": get_iso_time(),
                "created_at": get_iso_time(),
                "deleted": False
            }
            # --- FIX: Save to 'recommendations' collection ---
            db.collection("recommendations").document(rec_id).set(recommendation)
            summary_counters["Recommendations"] += 1


async def populate_test_data():
    """Populate Firestore with realistic test data"""
    print("🚀 Starting REALISTIC test data population...")
    print("=" * 60)
    
    global summary_counters
    summary_counters = defaultdict(int)
    
    student_role_id = await get_role_id_by_designation("student")
    if not student_role_id:
        print("❌ CRITICAL: 'student' role not found!")
        return
    
    print(f"✅ Found 'student' role. Using ID: {student_role_id}\n")
    
    # 1. CREATE SUBJECTS, TOS, DIAGNOSTICS, MODULES, QUIZZES
    print(f"📚 Creating {len(SUBJECTS_DATA)} Psychology subjects and all related content...")
    all_subject_content = {}
    
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
        summary_counters["Subjects"] += 1
        
        # Create Diagnostic Assessment
        diag_data = generate_diagnostic_assessment(subject_id, subj_data["name"], tos_data)
        diag_ref = db.collection("diagnostic_assessments").document(diag_data["id"])
        diag_ref.set(diag_data)
        
        # Create Modules (which also creates AI content)
        modules = create_modules_for_subject(subject_id, subj_data["name"])
        
        # Create Manual Quizzes
        quizzes = create_quizzes_for_subject(subject_id, subj_data["name"], modules)
        
        # Create Verification Tasks
        create_verification_tasks(modules, "module")
        create_verification_tasks(quizzes, "quiz")
        
        all_subject_content[subject_id] = {"modules": modules, "quizzes": quizzes}
        
        print(f"  ✅ {subj_data['name']}")
        print(f"     - TOS, Diagnostic, {len(modules)} Modules, {len(quizzes)} Quizzes")
        print(f"     - Mock AI Content & Verification Tasks")
    
    # 2. CREATE STUDENTS
    print(f"\n👥 Creating {len(STUDENT_PERSONAS)} realistic students...")
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        email = student["email"]
        password = "demo123"  # Default password for all demo students
        
        # Create Firebase Auth user
        try:
            auth.create_user(uid=student_id, email=email, password=password)
            # print(f"  ✅ Created auth user: {email} (UID: {student_id})")
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
            "deleted": False,
            "status": "offline", # Default status
            "last_seen": get_iso_time()
        })
        summary_counters["Students"] += 1
        print(f"  ✅ {student['name']} ({student['persona']})")
    
    # 3. GENERATE DIAGNOSTIC RESULTS, RECOMMENDATIONS, AND STUDY SESSIONS
    print("\n🧪 Generating student diagnostic results, recommendations, and study sessions...")
    
    for i, student in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        persona = student["persona"]
        
        # Take diagnostic for first 2 subjects
        for subj_data in SUBJECTS_DATA[:2]:
            subject_id = subj_data["id"]
            diag_id = f"{TEST_PREFIX}diag_{subject_id.split('_')[-1]}"
            
            diag_doc = db.collection("diagnostic_assessments").document(diag_id).get()
            if not diag_doc.exists:
                continue
            
            diag = diag_doc.to_dict()
            
            # --- Calculate TOS performance ---
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
                    if score > 60: topic_correct += 1
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
            
            # --- Save diagnostic result ---
            result_id = f"{TEST_PREFIX}result_{student_id.split('_')[-1]}_{subject_id.split('_')[-1]}"
            result_data = {
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
            }
            db.collection("diagnostic_results").document(result_id).set(result_data)
            summary_counters["DiagnosticResults"] += 1
            
            # --- Create Recommendations from this result ---
            content = all_subject_content[subject_id]
            create_recommendations_for_student(result_data, content["modules"], content["quizzes"])
            
            # --- Create Study Sessions & Activities for this subject ---
            create_study_sessions_for_student(
                student_id, persona, subject_id, 
                content["modules"], content["quizzes"], num_sessions=5
            )
            
            print(f"  ✅ {student['name']}: {subj_data['name']} - {overall_score}% ({passing_status})")
            print(f"     - Generated recommendations and 5 study sessions.")
    
    print("\n" + "=" * 60)
    print("🎉 REALISTIC DATA POPULATION COMPLETE!")
    print("\n📊 Summary:")
    for key, value in summary_counters.items():
        print(f"  - {value} {key}")
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