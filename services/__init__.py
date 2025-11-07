# services/__init__.py
from .generic_service import FirestoreModelService
from database.models import (
    Activity, Module, Quiz, Recommendation, Assessment, TOS, UserProfileModel,
    GeneratedSummary, GeneratedQuiz, GeneratedFlashcards  # --- NEW ---
)

# --- Create one service instance for each model ---

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

# --- Standalone flashcard_service REMOVED ---

recommendation_service = FirestoreModelService(
    collection_name="recommendations", 
    model=Recommendation
)

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

# --- NEW: Services for AI-generated content ---

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