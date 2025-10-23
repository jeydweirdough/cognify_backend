"""Test configuration and sample data constants."""

# Test data prefixes (helps identify test data for cleanup)
TEST_PREFIX = "test_"

# Sample user IDs
TEST_STUDENT_ID = f"{TEST_PREFIX}student_001"
TEST_FACULTY_ID = f"{TEST_PREFIX}faculty_001"
TEST_ADMIN_ID = f"{TEST_PREFIX}admin_001"

# Sample subject
TEST_SUBJECT_ID = f"{TEST_PREFIX}subj_personality"

# Sample module IDs
TEST_MODULE_IDS = [
    f"{TEST_PREFIX}mod_theories_intro",
    f"{TEST_PREFIX}mod_theories_advanced",
    f"{TEST_PREFIX}mod_global_impact"
]

# Sample assessment/quiz IDs
TEST_ASSESSMENT_ID = f"{TEST_PREFIX}assess_001"
TEST_QUIZ_IDS = [
    f"{TEST_PREFIX}quiz_theories_001",
    f"{TEST_PREFIX}quiz_global_002"
]

# Sample activity IDs
TEST_ACTIVITY_IDS = [
    f"{TEST_PREFIX}activity_001",
    f"{TEST_PREFIX}activity_002"
]

# Sample recommendation IDs
TEST_RECOMMENDATION_IDS = [
    f"{TEST_PREFIX}rec_001",
    f"{TEST_PREFIX}rec_002"
]

# Sample data content
SAMPLE_STUDENT_DATA = {
    "name": "Test Student",
    "email": "test.student@example.com",
    "course": "BS Psychology",
    "year_level": 3,
    "pre_assessment_score": 45,
    "ai_confidence": 0.58,
    "current_module": TEST_MODULE_IDS[0],
    "progress": {
        "Theories": 0.65,
        "Globalization": 0.45
    }
}

SAMPLE_TOS_DATA = {
    "subject": "Advanced Theories of Personality",
    "pqf_level": 7,
    "difficulty_distribution": {"easy": 0.30, "moderate": 0.40, "difficult": 0.30},
    "content": [
        {
            "title": "Theories",
            "sub_content": [
                {
                    "purpose": "Cite major tenets of personality theories",
                    "blooms_taxonomy": [{"remembering": 8}]
                }
            ],
            "no_items": 40,
            "weight_total": 0.40
        }
    ],
    "total_items": 100
}

SAMPLE_MODULE_DATA = {
    "title": "Overview of Major Personality Theories",
    "purpose": "Cite major tenets of personality theories",
    "bloom_level": "remembering",
    "material_type": "reading",
    "material_url": "https://example.com/test/module1",
    "estimated_time": 45
}

SAMPLE_ACTIVITY_DATA = {
    "subject_id": TEST_SUBJECT_ID,
    "activity_type": "assessment",
    "bloom_level": "applying",
    "score": 80,
    "completion_rate": 1.0,
    "duration": 1800
}

SAMPLE_ASSESSMENT_DATA = {
    "type": "diagnostic",
    "subject_id": TEST_SUBJECT_ID,
    "title": "Test Diagnostic Assessment",
    "instructions": "Answer all questions based on your understanding.",
    "total_items": 20,
    "questions": [
        {
            "question_id": "q1",
            "topic_title": "Theories",
            "bloom_level": "remembering",
            "question": "Which theory focuses on observable behaviors?",
            "options": ["Humanistic", "Behavioral", "Psychodynamic", "Existential"],
            "answer": "Behavioral"
        }
    ]
}