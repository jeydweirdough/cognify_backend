from .generic_service import FirestoreModelService
from database.models import (
    Activity, Module, Quiz, Recommendation, Assessment, TOS, UserProfileModel,
    GeneratedSummary, GeneratedQuiz, GeneratedFlashcards,
    DiagnosticAssessment, DiagnosticResult,
    ContentVerification, StudySession
)

# Core content services
activity_service = FirestoreModelService(
    collection_name="activities", 
    model=Activity
)

module_service = FirestoreModelService(
    collection_name="modules", 
    model=Module
)

quiz_service = FirestoreModelService(
    collection_name="quizzes", 
    model=Quiz
)

# --- FIX: Point the main recommendation_service to the new model ---
recommendation_service = FirestoreModelService(
    collection_name="recommendations", 
    model=Recommendation
)
# --- END FIX ---

assessment_service = FirestoreModelService(
    collection_name="assessments", 
    model=Assessment
)

tos_service = FirestoreModelService(
    collection_name="tos", 
    model=TOS
)

profile_service = FirestoreModelService(
    collection_name="user_profiles",
    model=UserProfileModel
)

# AI-generated content services
generated_summary_service = FirestoreModelService(
    collection_name="generated_summaries",
    model=GeneratedSummary
)

generated_quiz_service = FirestoreModelService(
    collection_name="generated_quizzes",
    model=GeneratedQuiz
)

generated_flashcards_service = FirestoreModelService(
    collection_name="generated_flashcards",
    model=GeneratedFlashcards
)

# Diagnostic assessment services
diagnostic_service = FirestoreModelService(
    collection_name="diagnostic_assessments",
    model=DiagnosticAssessment
)

diagnostic_result_service = FirestoreModelService(
    collection_name="diagnostic_results",
    model=DiagnosticResult
)

# --- FIX: Removed the enhanced_recommendation_service ---
# (The main service above now handles this)

# Content verification service
content_verification_service = FirestoreModelService(
    collection_name="content_verifications",
    model=ContentVerification
)

# Study session service
study_session_service = FirestoreModelService(
    collection_name="study_sessions",
    model=StudySession
)