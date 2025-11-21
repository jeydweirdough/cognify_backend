# test/config.py - ENHANCED VERSION

TEST_PREFIX = "demo_"

# ============================================================
# REALISTIC SUBJECT DATA (matching mobile UI requirements)
# ============================================================
SUBJECTS_DATA = [
    {
        "id": f"{TEST_PREFIX}subj_psych_assessment",
        "name": "Psychological Assessment",
        "pqf_level": 7,
        "description": "Understanding and using psychological tests to measure behavior and mental processes.",
        "icon_name": "clipboard-list",
        "icon_color": "#D8C713",
        "icon_bg_color": "#F0F5D5",
        "card_bg_color": "#FDFFB8"
    },
    {
        "id": f"{TEST_PREFIX}subj_dev_psych",
        "name": "Developmental Psychology",
        "pqf_level": 7,
        "description": "Study of human growth and changes from childhood to adulthood.",
        "icon_name": "users",
        "icon_color": "#4C609B",
        "icon_bg_color": "#E2E6F2",
        "card_bg_color": "#FFE8CD"
    },
    {
        "id": f"{TEST_PREFIX}subj_abnormal_psych",
        "name": "Abnormal Psychology",
        "pqf_level": 7,
        "description": "Study of psychological disorders, their causes, and treatments.",
        "icon_name": "brain",
        "icon_color": "#30C49F",
        "icon_bg_color": "#FCF5EE",
        "card_bg_color": "#FCF5EE"
    },
    {
        "id": f"{TEST_PREFIX}subj_io_psych",
        "name": "Industrial/Organizational Psychology",
        "pqf_level": 7,
        "description": "Application of psychology to workplace behavior and performance.",
        "icon_name": "briefcase",
        "icon_color": "#D38A4D",
        "icon_bg_color": "#F9ECE3",
        "card_bg_color": "#F4F8D3"
    },
]

# ============================================================
# REALISTIC MODULE DATA (matching mobile book covers)
# ============================================================
MODULES_DATA = [
    {
        "id": f"{TEST_PREFIX}mod_io_intro",
        "title": "Introduction to Industrial and Organizational Psychology",
        "author": "Ronald E. Riggo",
        "subject_id": f"{TEST_PREFIX}subj_io_psych",
        "cover_image_url": "https://covers.openlibrary.org/b/id/8235112-L.jpg",
        "short_description": "Comprehensive introduction to I/O Psychology principles and workplace applications.",
        "material_type": "reading",
        "bloom_level": "understanding",
        "estimated_time": 120
    },
    {
        "id": f"{TEST_PREFIX}mod_org_theory",
        "title": "Organizational Theory, Design and Change. Seventh Edition",
        "author": "Gareth R. Jones",
        "subject_id": f"{TEST_PREFIX}subj_io_psych",
        "cover_image_url": "https://covers.openlibrary.org/b/id/12547189-L.jpg",
        "short_description": "Advanced organizational structures and change management strategies.",
        "material_type": "reading",
        "bloom_level": "applying",
        "estimated_time": 180
    },
    {
        "id": f"{TEST_PREFIX}mod_io_workspace",
        "title": "Industrial Organizational Psychology. Understanding the Workspace",
        "author": "Paul E. Levy",
        "subject_id": f"{TEST_PREFIX}subj_io_psych",
        "cover_image_url": "https://covers.openlibrary.org/b/id/10603687-L.jpg",
        "short_description": "Practical guide to applying psychology in modern workplaces.",
        "material_type": "reading",
        "bloom_level": "applying",
        "estimated_time": 150
    },
    {
        "id": f"{TEST_PREFIX}mod_scientist_practitioner",
        "title": "A Scientist Practitioner Approach. Organizational Psychology",
        "author": "Ronald E. Riggo",
        "subject_id": f"{TEST_PREFIX}subj_io_psych",
        "cover_image_url": "https://covers.openlibrary.org/b/id/8259445-L.jpg",
        "short_description": "Evidence-based approach to organizational psychology research and practice.",
        "material_type": "reading",
        "bloom_level": "analyzing",
        "estimated_time": 200
    },
]

# ============================================================
# REALISTIC STUDENT PERSONAS (15 Students with varied performance)
# ============================================================
STUDENT_PERSONAS = [
    # Top Performers (5) - 85-95% scores
    {
        "name": "Maria Santos",
        "persona": "diligent_achiever",
        "email": "maria.santos@student.edu",
        "profile_picture": None  # Can add URL later
    },
    {
        "name": "Juan Reyes",
        "persona": "consistent_performer",
        "email": "juan.reyes@student.edu",
        "profile_picture": None
    },
    {
        "name": "Ana Cruz",
        "persona": "fast_learner",
        "email": "ana.cruz@student.edu",
        "profile_picture": None
    },
    {
        "name": "Carlos Mendoza",
        "persona": "methodical_student",
        "email": "carlos.mendoza@student.edu",
        "profile_picture": None
    },
    {
        "name": "Sofia Rodriguez",
        "persona": "high_achiever",
        "email": "sofia.rodriguez@student.edu",
        "profile_picture": None
    },
    
    # Mid-Level Students (5) - 65-80% scores
    {
        "name": "Miguel Torres",
        "persona": "improving_student",
        "email": "miguel.torres@student.edu",
        "profile_picture": None
    },
    {
        "name": "Elena Ramirez",
        "persona": "inconsistent_performer",
        "email": "elena.ramirez@student.edu",
        "profile_picture": None
    },
    {
        "name": "Diego Flores",
        "persona": "late_bloomer",
        "email": "diego.flores@student.edu",
        "profile_picture": None
    },
    {
        "name": "Isabel Garcia",
        "persona": "average_student",
        "email": "isabel.garcia@student.edu",
        "profile_picture": None
    },
    {
        "name": "Roberto Diaz",
        "persona": "slow_but_steady",
        "email": "roberto.diaz@student.edu",
        "profile_picture": None
    },
    
    # Struggling Students (5) - 45-60% scores
    {
        "name": "Patricia Luna",
        "persona": "struggling_student",
        "email": "patricia.luna@student.edu",
        "profile_picture": None
    },
    {
        "name": "Fernando Castillo",
        "persona": "procrastinator",
        "email": "fernando.castillo@student.edu",
        "profile_picture": None
    },
    {
        "name": "Carmen Morales",
        "persona": "overwhelmed_student",
        "email": "carmen.morales@student.edu",
        "profile_picture": None
    },
    {
        "name": "Luis Alvarez",
        "persona": "unmotivated_student",
        "email": "luis.alvarez@student.edu",
        "profile_picture": None
    },
    {
        "name": "Rosa Jimenez",
        "persona": "conceptual_struggler",
        "email": "rosa.jimenez@student.edu",
        "profile_picture": None
    },
]

# Performance patterns for realistic activity generation
PERSONA_BASE_SCORES = {
    # Top performers - consistent high scores across all Bloom levels
    "diligent_achiever": {
        "remembering": 95, "understanding": 92, "applying": 88,
        "analyzing": 85, "evaluating": 82, "creating": 80
    },
    "consistent_performer": {
        "remembering": 90, "understanding": 88, "applying": 85,
        "analyzing": 82, "evaluating": 80, "creating": 78
    },
    "fast_learner": {
        "remembering": 92, "understanding": 95, "applying": 90,
        "analyzing": 88, "evaluating": 85, "creating": 82
    },
    "methodical_student": {
        "remembering": 88, "understanding": 90, "applying": 92,
        "analyzing": 90, "evaluating": 88, "creating": 85
    },
    "high_achiever": {
        "remembering": 98, "understanding": 95, "applying": 92,
        "analyzing": 90, "evaluating": 88, "creating": 85
    },
    
    # Mid-level - mixed performance
    "improving_student": {
        "remembering": 75, "understanding": 72, "applying": 78,
        "analyzing": 75, "evaluating": 72, "creating": 70
    },
    "inconsistent_performer": {
        "remembering": 85, "understanding": 70, "applying": 75,
        "analyzing": 68, "evaluating": 72, "creating": 65
    },
    "late_bloomer": {
        "remembering": 70, "understanding": 72, "applying": 75,
        "analyzing": 78, "evaluating": 80, "creating": 75
    },
    "average_student": {
        "remembering": 75, "understanding": 75, "applying": 75,
        "analyzing": 75, "evaluating": 75, "creating": 75
    },
    "slow_but_steady": {
        "remembering": 78, "understanding": 75, "applying": 72,
        "analyzing": 70, "evaluating": 68, "creating": 65
    },
    
    # Struggling - low scores, especially on higher-order thinking
    "struggling_student": {
        "remembering": 65, "understanding": 62, "applying": 58,
        "analyzing": 55, "evaluating": 52, "creating": 50
    },
    "procrastinator": {
        "remembering": 60, "understanding": 58, "applying": 55,
        "analyzing": 52, "evaluating": 50, "creating": 48
    },
    "overwhelmed_student": {
        "remembering": 68, "understanding": 65, "applying": 60,
        "analyzing": 58, "evaluating": 55, "creating": 52
    },
    "unmotivated_student": {
        "remembering": 62, "understanding": 60, "applying": 58,
        "analyzing": 55, "evaluating": 52, "creating": 50
    },
    "conceptual_struggler": {
        "remembering": 75, "understanding": 60, "applying": 55,
        "analyzing": 50, "evaluating": 48, "creating": 45
    },
}