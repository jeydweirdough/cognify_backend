import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
from firebase_admin import auth

# --- SETUP PATHS ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from core.firebase import db
from services.role_service import get_role_id_by_designation
from test.config import TEST_PREFIX, SUBJECTS_DATA, STUDENT_PERSONAS, PERSONA_BASE_SCORES

def get_iso_time():
    return datetime.now(timezone.utc).isoformat()

async def ensure_roles_exist():
    """Ensures roles exist with IDs matching the frontend."""
    roles_data = [
        {"id": "PifcrriKAGM6YdWORP5I", "designation": "admin", "label": "Admin"},
        {"id": "vhVbVsvMKiogI6rNLS7n", "designation": "faculty_member", "label": "Faculty Member"},
        {"id": "Tzc78QtZcaVbzFtpHoOL", "designation": "student", "label": "Student"}
    ]
    for role in roles_data:
        doc_ref = db.collection("roles").document(role["id"])
        if not doc_ref.get().exists:
            doc_ref.set(role)

def generate_score(persona, bloom_level):
    base = PERSONA_BASE_SCORES.get(persona, {}).get(bloom_level, 75)
    return min(100, max(0, base + random.uniform(-10, 10)))

async def populate_test_data():
    print("\n🚀 STARTING DATA POPULATION (With Analytics Reports)...")
    await ensure_roles_exist()
    
    student_role_id = "Tzc78QtZcaVbzFtpHoOL"
    
    # 1. Create Content
    all_content = [] 
    bloom_levels = ["remembering", "understanding", "applying", "analyzing", "evaluating", "creating"]
    
    for subj in SUBJECTS_DATA:
        db.collection("subjects").document(subj["id"]).set({"id": subj["id"], "subject_name": subj["name"], "deleted": False})
        
        for i, bloom in enumerate(bloom_levels):
            # Module
            mod_id = f"{TEST_PREFIX}mod_{subj['id'].split('_')[-1]}_{i}"
            db.collection("modules").document(mod_id).set({
                "id": mod_id, "subject_id": subj["id"], "title": f"{bloom.title()} Module", 
                "bloom_level": bloom, "deleted": False
            })
            all_content.append({"id": mod_id, "type": "module", "bloom": bloom, "subject": subj["id"]})

    # 2. Create Students & Generate Reports
    print(f"\n👥 Processing {len(STUDENT_PERSONAS)} Students...")
    
    for i, student_def in enumerate(STUDENT_PERSONAS):
        student_id = f"{TEST_PREFIX}student_{i+1:02d}"
        
        # A. Profile
        db.collection("user_profiles").document(student_id).set({
            "id": student_id,
            "email": student_def["email"],
            "first_name": student_def["name"].split()[0],
            "last_name": student_def["name"].split()[1] if " " in student_def["name"] else "Student",
            "role_id": student_role_id,
            "deleted": False,
            "status": "offline"
        })
        
        # B. Activities (History)
        print(f"   - Generating history for {student_def['name']}...")
        num_activities = random.randint(20, 40)
        total_score = 0
        bloom_scores = defaultdict(list)
        
        for j in range(num_activities):
            content = random.choice(all_content)
            score = generate_score(student_def["persona"], content["bloom"])
            total_score += score
            bloom_scores[content["bloom"]].append(score)
            
            act_id = f"{TEST_PREFIX}act_{student_id.split('_')[-1]}_{j}"
            activity = {
                "id": act_id,
                "user_id": student_id,
                "subject_id": content["subject"],
                "bloom_level": content["bloom"],
                "score": float(round(score, 2)),
                "completion_rate": 1.0,
                "created_at": get_iso_time(),
                "deleted": False
            }
            db.collection("activities").document(act_id).set(activity)

        # C. GENERATE & SAVE ANALYTICS REPORT (The Collection you requested)
        avg_score = total_score / num_activities if num_activities > 0 else 0
        bloom_performance = {k: round(sum(v)/len(v), 2) for k, v in bloom_scores.items()}
        
        report_data = {
            "student_id": student_id,
            "summary": {
                "average_score": float(round(avg_score, 2)),
                "total_activities": num_activities,
                "completion_rate": 1.0,
                "total_sessions": 5
            },
            "performance_by_bloom": bloom_performance,
            "last_updated": get_iso_time()
        }
        
        # Save to the new collection
        db.collection("student_analytics_reports").document(student_id).set(report_data)

    print("\n✅ DONE. 'student_analytics_reports' collection populated.")

if __name__ == "__main__":
    asyncio.run(populate_test_data())