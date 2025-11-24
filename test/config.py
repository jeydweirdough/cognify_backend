# test/config.py
"""
Configuration for generating realistic test data.
"""

TEST_PREFIX = "demo_"

# ============================================================
# 1. SUBJECTS (Psychometrician Board Exam Core Subjects)
# ============================================================
SUBJECTS_DATA = [
    {
        "id": f"{TEST_PREFIX}subj_psych_assessment",
        "subject_name": "Psychological Assessment",
        "pqf_level": 7,
        "description": "Principles, methods, and tools for psychological evaluation and measurement.",
        "icon_name": "clipboard-list",
        "icon_color": "#D8C713",
        "icon_bg_color": "#F0F5D5",
        "card_bg_color": "#FDFFB8"
    },
    {
        "id": f"{TEST_PREFIX}subj_abnormal_psych",
        "subject_name": "Abnormal Psychology",
        "pqf_level": 7,
        "description": "Study of psychological disorders, maladaptive behaviors, and their classification.",
        "icon_name": "brain",
        "icon_color": "#30C49F",
        "icon_bg_color": "#E6F7F3",
        "card_bg_color": "#E6F7F3"
    },
    {
        "id": f"{TEST_PREFIX}subj_dev_psych",
        "subject_name": "Developmental Psychology",
        "pqf_level": 7,
        "description": "Human growth and changes across the lifespan from conception to death.",
        "icon_name": "baby-carriage",
        "icon_color": "#4C609B",
        "icon_bg_color": "#E2E6F2",
        "card_bg_color": "#E2E6F2"
    },
    {
        "id": f"{TEST_PREFIX}subj_io_psych",
        "subject_name": "Industrial/Organizational Psychology",
        "pqf_level": 7,
        "description": "Application of psychological theories to workplace behavior and organizational settings.",
        "icon_name": "briefcase",
        "icon_color": "#D38A4D",
        "icon_bg_color": "#F9ECE3",
        "card_bg_color": "#F9ECE3"
    },
]

# ============================================================
# 2. MODULES (Specific Content for each Subject)
# ============================================================
# Structure matches ModuleBase fields
MODULES_DATA = {
    f"{TEST_PREFIX}subj_psych_assessment": [
        {"title": "Introduction to Psychological Testing", "bloom_level": "remembering", "material_type": "reading", "estimated_time": 60, "purpose": "Define basic concepts"},
        {"title": "Reliability and Validity", "bloom_level": "understanding", "material_type": "reading", "estimated_time": 90, "purpose": "Explain psychometric properties"},
        {"title": "Norms and Test Standardization", "bloom_level": "analyzing", "material_type": "reading", "estimated_time": 120, "purpose": "Analyze test data"},
        {"title": "Assessment Interviewing", "bloom_level": "applying", "material_type": "reading", "estimated_time": 45, "purpose": "Apply interviewing techniques"},
    ],
    f"{TEST_PREFIX}subj_abnormal_psych": [
        {"title": "Models of Abnormality", "bloom_level": "understanding", "material_type": "reading", "estimated_time": 60, "purpose": "Understand theoretical frameworks"},
        {"title": "Anxiety and Phobias", "bloom_level": "analyzing", "material_type": "reading", "estimated_time": 90, "purpose": "Analyze anxiety disorders"},
        {"title": "Mood Disorders: Depression & Bipolar", "bloom_level": "evaluating", "material_type": "reading", "estimated_time": 120, "purpose": "Evaluate mood symptoms"},
        {"title": "Personality Disorders", "bloom_level": "remembering", "material_type": "reading", "estimated_time": 80, "purpose": "Recall personality clusters"},
    ],
    f"{TEST_PREFIX}subj_dev_psych": [
        {"title": "Prenatal Development", "bloom_level": "remembering", "material_type": "reading", "estimated_time": 45, "purpose": "Recall prenatal stages"},
        {"title": "Piaget's Stages of Cognitive Development", "bloom_level": "understanding", "material_type": "reading", "estimated_time": 90, "purpose": "Explain cognitive growth"},
        {"title": "Erikson's Psychosocial Stages", "bloom_level": "analyzing", "material_type": "reading", "estimated_time": 90, "purpose": "Analyze psychosocial crises"},
        {"title": "Adolescence and Emerging Adulthood", "bloom_level": "evaluating", "material_type": "reading", "estimated_time": 60, "purpose": "Evaluate developmental tasks"},
    ],
    f"{TEST_PREFIX}subj_io_psych": [
        {"title": "Job Analysis and Selection", "bloom_level": "applying", "material_type": "reading", "estimated_time": 120, "purpose": "Apply selection methods"},
        {"title": "Performance Appraisal Systems", "bloom_level": "analyzing", "material_type": "reading", "estimated_time": 90, "purpose": "Analyze performance metrics"},
        {"title": "Motivation in the Workplace", "bloom_level": "understanding", "material_type": "reading", "estimated_time": 60, "purpose": "Understand motivation theories"},
        {"title": "Organizational Culture", "bloom_level": "evaluating", "material_type": "reading", "estimated_time": 75, "purpose": "Evaluate culture impact"},
    ]
}

# ============================================================
# 3. STUDENT PERSONAS (For realistic score generation)
# ============================================================
STUDENT_PERSONAS = [
    # Top Performers
    {"name": "Maria Santos", "persona": "diligent_achiever", "email": "maria.santos@student.edu", "img": "https://i.pravatar.cc/150?img=1"},
    {"name": "Juan Reyes", "persona": "consistent_performer", "email": "juan.reyes@student.edu", "img": "https://i.pravatar.cc/150?img=12"},
    {"name": "Ana Cruz", "persona": "fast_learner", "email": "ana.cruz@student.edu", "img": "https://i.pravatar.cc/150?img=5"},
    {"name": "Carlos Mendoza", "persona": "methodical_student", "email": "carlos.mendoza@student.edu", "img": "https://i.pravatar.cc/150?img=11"},
    {"name": "Sofia Rodriguez", "persona": "high_achiever", "email": "sofia.rodriguez@student.edu", "img": "https://i.pravatar.cc/150?img=9"},
    
    # Mid-Level Students
    {"name": "Miguel Torres", "persona": "improving_student", "email": "miguel.torres@student.edu", "img": "https://i.pravatar.cc/150?img=3"},
    {"name": "Elena Ramirez", "persona": "inconsistent_performer", "email": "elena.ramirez@student.edu", "img": "https://i.pravatar.cc/150?img=10"},
    {"name": "Diego Flores", "persona": "late_bloomer", "email": "diego.flores@student.edu", "img": "https://i.pravatar.cc/150?img=8"},
    {"name": "Isabel Garcia", "persona": "average_student", "email": "isabel.garcia@student.edu", "img": "https://i.pravatar.cc/150?img=4"},
    {"name": "Roberto Diaz", "persona": "slow_but_steady", "email": "roberto.diaz@student.edu", "img": "https://i.pravatar.cc/150?img=7"},
    
    # Struggling Students
    {"name": "Patricia Luna", "persona": "struggling_student", "email": "patricia.luna@student.edu", "img": "https://i.pravatar.cc/150?img=2"},
    {"name": "Fernando Castillo", "persona": "procrastinator", "email": "fernando.castillo@student.edu", "img": "https://i.pravatar.cc/150?img=6"},
    {"name": "Carmen Morales", "persona": "overwhelmed_student", "email": "carmen.morales@student.edu", "img": "https://i.pravatar.cc/150?img=24"},
    {"name": "Luis Alvarez", "persona": "unmotivated_student", "email": "luis.alvarez@student.edu", "img": "https://i.pravatar.cc/150?img=15"},
    {"name": "Rosa Jimenez", "persona": "conceptual_struggler", "email": "rosa.jimenez@student.edu", "img": "https://i.pravatar.cc/150?img=20"},
]

PERSONA_BASE_SCORES = {
    "diligent_achiever": {"default": 92, "min": 85, "max": 100},
    "consistent_performer": {"default": 88, "min": 82, "max": 94},
    "fast_learner": {"default": 85, "min": 75, "max": 98},
    "methodical_student": {"default": 86, "min": 80, "max": 92},
    "high_achiever": {"default": 95, "min": 90, "max": 100},
    
    "improving_student": {"default": 78, "min": 70, "max": 85},
    "inconsistent_performer": {"default": 75, "min": 60, "max": 90},
    "late_bloomer": {"default": 72, "min": 65, "max": 80},
    "average_student": {"default": 75, "min": 70, "max": 80},
    "slow_but_steady": {"default": 74, "min": 70, "max": 78},
    
    "struggling_student": {"default": 60, "min": 50, "max": 70},
    "procrastinator": {"default": 55, "min": 40, "max": 75},
    "overwhelmed_student": {"default": 58, "min": 45, "max": 65},
    "unmotivated_student": {"default": 50, "min": 30, "max": 60},
    "conceptual_struggler": {"default": 52, "min": 40, "max": 65},
}