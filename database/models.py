
from pydantic import (
    BaseModel, 
    Field, 
    RootModel, 
    field_validator, 
    model_validator
)
from typing import Optional, List, Dict, Any
import datetime
from datetime import timezone
import math # Used for float comparison

# ========== Root Model ===========
# RootModels are used to add validation and methods to simple types
# like a 'dict' or 'list'.

class StudentProgress(RootModel):
    """
    A RootModel for student progress, mapping topic titles (str) to
    a completion percentage (float between 0.0 and 1.0).
    
    Example:
    {"Theories": 0.65, "Globalization": 0.45}
    """
    root: Dict[str, float]

    @field_validator("root")
    @classmethod
    def validate_progress_range(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validates that all progress values are between 0.0 and 1.0."""
        for topic, progress in v.items():
            if not (0.0 <= progress <= 1.0):
                raise ValueError(
                    f"Progress for '{topic}' ({progress}) must be between 0.0 and 1.0"
                )
        return v

    def get_average_progress(self) -> float:
        """Helper method to calculate average progress."""
        if not self.root:
            return 0.0
        return sum(self.root.values()) / len(self.root)

class BloomEntry(RootModel):
    """
    A RootModel for a single Bloom's Taxonomy entry, mapping one
    level (str) to the number of items (int).
    
    Example:
    {"remembering": 8}
    """
    root: Dict[str, int]

    @field_validator("root")
    @classmethod
    def validate_bloom_entry(cls, v: Dict[str, int]) -> Dict[str, int]:
        """
        Validates the BloomEntry to ensure it:
        1. Contains exactly one key-value pair.
        2. Uses a valid Bloom's Taxonomy level as the key.
        3. Has a positive integer for the item count.
        """
        if len(v) != 1:
            raise ValueError(
                f"BloomEntry must contain exactly one key-value pair. Found: {len(v)}"
            )

        valid_levels = {
            "remembering", 
            "understanding", 
            "applying", 
            "analyzing", 
            "evaluating", 
            "creating"
        }
        key = next(iter(v)) # Get the first (and only) key
        
        if key not in valid_levels:
            raise ValueError(
                f"'{key}' is not a valid Bloom's Taxonomy level. Must be one of: {valid_levels}"
            )
        
        if v[key] <= 0:
            raise ValueError(
                f"Item count for '{key}' must be positive. Found: {v[key]}"
            )
            
        return v

def get_current_iso_time() -> str:
    """Returns the current UTC time in ISO format."""
    # --- FIX: Replaced datetime.utcnow() with datetime.now(timezone.utc) ---
    return datetime.datetime.now(timezone.utc).isoformat()   

# ========== TimeStamp Model =========
class TimestampModel(BaseModel):
    """
    A 'mixin' model that adds database timestamps.
    It's inherited by 'Document' models (e.g., Activity, Module).
    """
    created_at: str = Field(default_factory=get_current_iso_time)
    updated_at: Optional[str] = Field(default=None)
    deleted_at: Optional[str] = Field(default=None)
    deleted: bool = Field(default=False)

# ========== Auth Models ==========
class SignUpSchema(BaseModel):
    """Schema for user registration request body."""
    email: str
    password: str

class LoginSchema(BaseModel):
    """Schema for user login request body."""
    email: str
    password: str

#========== User Models ==========
# We use a 'Base' model for creation (POST/PUT) and a 'Document'
# model for reading (GET).

class UserProfileBase(BaseModel):
    """
    The base user profile data for ALL users (students, faculty, admin).
    """
    email: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    
    # Student-specific fields (will be None for other roles)
    pre_assessment_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    current_module: Optional[str] = None
    progress: Optional[StudentProgress] = None

    # --- NEW: ADD THIS FIELD FOR MOBILE PUSH NOTIFICATIONS ---
    fcm_token: Optional[str] = Field(default=None, description="Firebase Cloud Messaging device token for push notifications")
    # --- END OF NEW FIELD ---

    @field_validator("ai_confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Validates that ai_confidence is between 0.0 and 1.0 if it exists."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("ai_confidence must be between 0.0 and 1.0")
        return v

class UserProfileModel(UserProfileBase, TimestampModel):
    """
    The full User Profile document model.
    The 'id' (Firebase Auth UID) is inherited from TimestampModel.
    """
    id: str  # Make id non-optional
    
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'progress' in data and data.get('progress') is not None:
            # Pydantic v2 stores RootModel data in .root
            data['progress'] = self.progress.root
        return data

#========== Database Models ==========

# --- Activity ---
class ActivityBase(BaseModel):
    """Base model for creating a new Activity."""
    user_id: str
    subject_id: Optional[str] = None
    activity_type: Optional[str] = None # e.g., 'assessment', 'module'
    activity_ref: Optional[str] = None  # e.g., 'assess_adv_personality_mock'
    bloom_level: Optional[str] = None
    score: Optional[float] = None
    completion_rate: Optional[float] = None
    duration: Optional[int] = None      # e.g., in seconds
    timestamp: Optional[str] = None     # ISO format string

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        """Validates that the score is not negative."""
        if v is not None and v < 0:
            raise ValueError("score cannot be negative")
        return v

    @field_validator("completion_rate")
    @classmethod
    def validate_completion_rate(cls, v: Optional[float]) -> Optional[float]:
        """Validates that completion_rate is between 0.0 and 1.0."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("completion_rate must be between 0.0 and 1.0")
        return v

class Activity(ActivityBase, TimestampModel):
    """Document model for reading an Activity (includes ID)."""
    id: str # Use 'id' to match the generic service
    
    def to_dict(self):
        return self.model_dump(exclude_none=True)

# --- Question / Assessment ---
class BaseQuestion(BaseModel):
    """
    A base model containing fields common to all question types
    (both in Assessments and standalone Quizzes).
    """
    topic_title: Optional[str] = None
    bloom_level: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None

class Question(BaseQuestion):
    """A Question embedded within an Assessment."""
    question_id: str

class AssessmentBase(BaseModel):
    """Base model for creating a new Assessment."""
    type: Optional[str] = None # e.g., 'mock', 'pre_assessment'
    subject_id: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    total_items: Optional[int] = None
    questions: Optional[List[Question]] = None

class Assessment(AssessmentBase, TimestampModel):
    """Document model for reading an Assessment (includes ID)."""
    id: str # Use 'id'
    def to_dict(self):
        return self.model_dump(exclude_none=True)

# --- Module ---
class ModuleBase(BaseModel):
    """Base model for creating a new Module."""
    subject_id: Optional[str] = None
    title: Optional[str] = None
    purpose: Optional[str] = None
    bloom_level: Optional[str] = None
    material_type: Optional[str] = None # e.g., 'reading', 'video'
    material_url: Optional[str] = None
    estimated_time: Optional[int] = None # e.g., in minutes

class Module(ModuleBase, TimestampModel):
    """Document model for reading a Module (includes ID)."""
    id: str # Use 'id'
    def to_dict(self):
        return self.model_dump(exclude_none=True)

# --- Quiz ---
class QuizBase(BaseQuestion): # Inherits all fields from BaseQuestion
    """Base model for creating a new Quiz question."""
    subject_id: Optional[str] = None

class Quiz(QuizBase, TimestampModel):
    """Document model for reading a Quiz question (includes ID)."""
    id: str # Use 'id'
    def to_dict(self):
        return self.model_dump(exclude_none=True)

# --- Recommendation ---
class RecommendationBase(BaseModel):
    """Base model for creating a new Recommendation."""
    user_id: str
    subject_id: Optional[str] = None
    recommended_topic: Optional[str] = None
    recommended_module: Optional[str] = None # e.g., 'mod_3'
    bloom_focus: Optional[str] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: Optional[str] = None

class Recommendation(RecommendationBase, TimestampModel):
    """Document model for reading a Recommendation (includes ID)."""
    id: str # Use 'id'
    def to_dict(self):
        return self.model_dump(exclude_none=True)

# --- TOS (Table of Specifications) ---
# These models are for the structure *within* a TOS document.

class SubjectBase(BaseModel):
    """
    Base model for a Subject. The ID is the subject_id.
    """
    subject_name: str
    pqf_level: Optional[int] = None
    
    # This is the "pointer" to the version of the TOS
    # that is currently in use for recommendations.
    active_tos_id: Optional[str] = None 

class Subject(SubjectBase):
    """
    The full Subject document model.
    """
    subject_id: str # The document ID

    def to_dict(self):
        return self.model_dump(exclude_none=True)

class SubContent(BaseModel):
    """Defines the sub-content within a TOS content section."""
    purpose: Optional[str] = None
    
    # This list will be validated by the 'BloomEntry' model
    blooms_taxonomy: Optional[List[BloomEntry]] = None
    
    def to_dict(self):
        """Converts model to dict, handling the RootModel list for Firebase."""
        data = self.model_dump(exclude_none=True)
        # Convert list of BloomEntry back to a plain list of dicts
        if 'blooms_taxonomy' in data and data.get('blooms_taxonomy') is not None:
            # Access .root for each entry
            data['blooms_taxonomy'] = [entry.root for entry in self.blooms_taxonomy]
        return data

class ContentSection(BaseModel):
    """Defines a main content section in a TOS (e.g., 'Theories')."""
    title: Optional[str] = None
    sub_content: Optional[List[SubContent]] = None
    no_items: Optional[int] = None
    weight_total: Optional[float] = None # e.g., 0.40 for 40%
    
    def to_dict(self):
        """Recursively converts nested models to dicts for Firebase."""
        data = self.model_dump(exclude_none=True)
        # Must recursively call to_dict on SubContent
        if 'sub_content' in data and data.get('sub_content') is not None:
            data['sub_content'] = [sc.to_dict() for sc in self.sub_content]
        return data

# --- TOS (Main Model) ---
# The TOS document ID ('subject_id') is known beforehand,
# so we follow the UserProfile pattern (Base + Document).

class TOSBase(BaseModel):
    """Base model for creating or updating a TOS."""
    subject_name: Optional[str] = None
    pqf_level: Optional[int] = None
    difficulty_distribution: Optional[Dict[str, float]] = None
    content: Optional[List[ContentSection]] = None
    total_items: Optional[int] = None

    @model_validator(mode='after')
    def validate_difficulty_distribution_sum(self) -> 'TOSBase':
        """
        Validates that the values in difficulty_distribution sum up to 1.0,
        if the distribution is provided.
        """
        if self.difficulty_distribution:
            total_sum = sum(self.difficulty_distribution.values())
            # Use math.isclose for robust floating point comparison
            if not math.isclose(total_sum, 1.0):
                 raise ValueError(
                     f"Difficulty distribution values must sum to 1.0. Current sum: {total_sum}"
                 )
        return self

class TOS(TOSBase, TimestampModel): # <-- FIX: Inherit from TimestampModel
    """Document model for reading a TOS."""
    id: str  # The 'id'
    
    def to_dict(self):
        """Recursively converts nested models to dicts for Firebase."""
        data = self.model_dump(exclude_none=True)
        # Must recursively call to_dict on ContentSection
        if 'content' in data and data.get('content') is not None:
            data['content'] = [c.to_dict() for c in self.content]
        return data