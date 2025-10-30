# services/__init__.py
from .generic_service import FirestoreModelService
from database.models import (
    Activity, Module, Quiz, Recommendation, Assessment, TOS, UserProfileModel
)

# --- Create one service instance for each model ---
# No 'id_field' needed, as the service assumes 'id'

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

# UserProfileModel uses 'id' as its key (the Auth UID), so it works perfectly.
profile_service = FirestoreModelService(
    collection_name="user_profiles",
    model=UserProfileModel
)