"""Test configuration and sample data constants."""

# ✅ SINGLE SOURCE OF TRUTH for test data prefix
TEST_PREFIX = "demo_"

# Sample User IDs
TEST_PASS_STUDENT_ID = f"{TEST_PREFIX}user_pass_original"
TEST_FAIL_STUDENT_ID = f"{TEST_PREFIX}user_fail_original"
TEST_FACULTY_ID = f"{TEST_PREFIX}user_faculty_001"
TEST_ADMIN_ID = f"{TEST_PREFIX}user_admin_001"

# Sample Document IDs
TEST_SUBJECT_ID = f"{TEST_PREFIX}subj_personality"
TEST_TOS_ID = f"{TEST_PREFIX}tos_personality_v1"

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

# Base scores for personas (used for generating realistic data)
PERSONA_BASE_SCORES = {
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