# database/models.py
from pydantic import (
    BaseModel, 
    Field, 
    RootModel, 
    field_validator, 
    model_validator
)
from pydantic.generics import GenericModel
from typing import Optional, List, Dict, Any, Generic, TypeVar, Literal
import datetime
from datetime import timezone
import math

# ========== Pagination Model (Unchanged) ===========
T = TypeVar("T")
class PaginatedResponse(GenericModel, Generic[T]):
    items: List[T]
    last_doc_id: Optional[str] = Field(None, description="The ID of the last document in the list, used for 'start_after' in the next request.")

# ========== Root Models ===========
class StudentProgress(RootModel):
    root: Dict[str, float]
    @field_validator("root")
    @classmethod
    def validate_progress_range(cls, v: Dict[str, float]) -> Dict[str, float]:
        for topic, progress in v.items():
            if not (0.0 <= progress <= 1.0):
                raise ValueError(f"Progress for '{topic}' ({progress}) must be between 0.0 and 1.0")
        return v
    def get_average_progress(self) -> float:
        if not self.root: return 0.0
        return sum(self.root.values()) / len(self.root)

class BloomEntry(RootModel):
    root: Dict[str, int]
    @field_validator("root")
    @classmethod
    def validate_bloom_entry(cls, v: Dict[str, int]) -> Dict[str, int]:
        if len(v) != 1: raise ValueError(f"BloomEntry must contain exactly one key-value pair. Found: {len(v)}")
        valid_levels = {"remembering", "understanding", "applying", "analyzing", "evaluating", "creating"}
        key = next(iter(v))
        if key not in valid_levels: raise ValueError(f"'{key}' is not a valid Bloom's Taxonomy level. Must be one of: {valid_levels}")
        if v[key] <= 0: raise ValueError(f"Item count for '{key}' must be positive. Found: {v[key]}")
        return v

def get_current_iso_time() -> str:
    return datetime.datetime.now(timezone.utc).isoformat()   

# ========== TimeStamp Model (Unchanged) =========
class TimestampModel(BaseModel):
    created_at: str = Field(default_factory=get_current_iso_time)
    updated_at: Optional[str] = Field(default=None)
    deleted_at: Optional[str] = Field(default=None)
    deleted: bool = Field(default=False)

# ========== Auth & User Models (Unchanged) ==========
class SignUpSchema(BaseModel):
    email: str
    password: str

class LoginSchema(BaseModel):
    email: str
    password: str

class UserProfileBase(BaseModel):
    email: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    role_id: Optional[str] = None
    pre_assessment_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    current_module: Optional[str] = None
    progress: Optional[StudentProgress] = None
    fcm_token: Optional[str] = Field(default=None, description="Firebase Cloud Messaging device token for push notifications")
    @field_validator("ai_confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0): raise ValueError("ai_confidence must be between 0.0 and 1.0")
        return v

class UserProfileModel(UserProfileBase, TimestampModel):
    id: str
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'progress' in data and data.get('progress') is not None: data['progress'] = self.progress.root
        return data

#========== Database Models (Unchanged up to Module) ==========
class ActivityBase(BaseModel):
    user_id: str
    subject_id: Optional[str] = None
    activity_type: Optional[str] = None
    activity_ref: Optional[str] = None
    bloom_level: Optional[str] = None
    score: Optional[float] = None
    completion_rate: Optional[float] = None
    duration: Optional[int] = None
    timestamp: Optional[str] = None
    @field_validator("score")
    @classmethod
    def validate_score(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0: raise ValueError("score cannot be negative")
        return v
    @field_validator("completion_rate")
    @classmethod
    def validate_completion_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 1.0): raise ValueError("completion_rate must be between 0.0 and 1.0")
        return v
class Activity(ActivityBase, TimestampModel):
    id: str
    def to_dict(self): return self.model_dump(exclude_none=True)

class BaseQuestion(BaseModel):
    topic_title: Optional[str] = None
    bloom_level: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None

class Question(BaseQuestion):
    question_id: str

class AssessmentBase(BaseModel):
    type: Optional[str] = None
    subject_id: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    total_items: Optional[int] = None
    questions: Optional[List[Question]] = None

class Assessment(AssessmentBase, TimestampModel):
    id: str
    def to_dict(self): return self.model_dump(exclude_none=True)

# --- Module ---
class ModuleBase(BaseModel):
    subject_id: Optional[str] = None
    title: Optional[str] = None
    purpose: Optional[str] = None
    bloom_level: Optional[str] = None
    material_type: Optional[str] = None
    material_url: Optional[str] = None
    estimated_time: Optional[int] = None
    generated_summary_id: Optional[str] = None
    generated_quiz_id: Optional[str] = None
    generated_flashcards_id: Optional[str] = None
class Module(ModuleBase, TimestampModel):
    id: str
    def to_dict(self): return self.model_dump(exclude_none=True)

# --- (Quiz) ---
class QuizBase(BaseQuestion):
    subject_id: Optional[str] = None
class Quiz(QuizBase, TimestampModel):
    id: str
    def to_dict(self): return self.model_dump(exclude_none=True)


# --- (Old Recommendation model removed) ---


# --- AI-Generated Content Models ---

# --- Generated Summary ---
class GeneratedSummaryBase(BaseModel):
    module_id: str
    subject_id: str
    summary_text: str
    source_url: str
    source_char_count: int
    # --- NEW: TOS Alignment ---
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None
    
class GeneratedSummary(GeneratedSummaryBase, TimestampModel):
    id: str
    def to_dict(self): return self.model_dump(exclude_none=True)

# --- Generated Quiz ---
class GeneratedQuestion(BaseModel):
    question: str
    options: List[str]
    answer: str
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

class GeneratedQuizBase(BaseModel):
    module_id: str
    subject_id: str
    questions: List[GeneratedQuestion]
    source_url: str
    source_char_count: int
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

class GeneratedQuiz(GeneratedQuizBase, TimestampModel):
    id: str
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'questions' in data and data.get('questions') is not None:
            data['questions'] = [q.model_dump(exclude_none=True) for q in self.questions]
        return data

# --- Generated Flashcards ---
class GeneratedFlashcard(BaseModel):
    question: str
    answer: str
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

class GeneratedFlashcardsBase(BaseModel):
    module_id: str
    subject_id: str
    flashcards: List[GeneratedFlashcard]
    source_url: str
    source_char_count: int
    # --- NEW: TOS Alignment ---
    tos_topic_title: Optional[str] = None
    aligned_bloom_level: Optional[str] = None

class GeneratedFlashcards(GeneratedFlashcardsBase, TimestampModel):
    id: str
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'flashcards' in data and data.get('flashcards') is not None:
            data['flashcards'] = [card.model_dump(exclude_none=True) for card in self.flashcards]
        return data


# --- TOS & Subject Models ---
class SubjectBase(BaseModel):
    subject_name: str
    pqf_level: Optional[int] = None
    active_tos_id: Optional[str] = None 
class Subject(SubjectBase):
    subject_id: str
    def to_dict(self): return self.model_dump(exclude_none=True)

class SubContent(BaseModel):
    purpose: Optional[str] = None
    blooms_taxonomy: Optional[List[BloomEntry]] = None
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'blooms_taxonomy' in data and data.get('blooms_taxonomy') is not None:
            data['blooms_taxonomy'] = [entry.root for entry in self.blooms_taxonomy]
        return data

class ContentSection(BaseModel):
    title: Optional[str] = None
    sub_content: Optional[List[SubContent]] = None
    no_items: Optional[int] = None
    weight_total: Optional[float] = None
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'sub_content' in data and data.get('sub_content') is not None:
            data['sub_content'] = [sc.to_dict() for sc in self.sub_content]
        return data

class TOSBase(BaseModel):
    subject_name: Optional[str] = None
    pqf_level: Optional[int] = None
    difficulty_distribution: Optional[Dict[str, float]] = None
    content: Optional[List[ContentSection]] = None
    total_items: Optional[int] = None
    @model_validator(mode='after')
    def validate_difficulty_distribution_sum(self) -> 'TOSBase':
        if self.difficulty_distribution:
            total_sum = sum(self.difficulty_distribution.values())
            if not math.isclose(total_sum, 1.0):
                 raise ValueError(f"Difficulty distribution values must sum to 1.0. Current sum: {total_sum}")
        return self
    
class TOS(TOSBase, TimestampModel):
    id: str
    def to_dict(self):
        data = self.model_dump(exclude_none=True)
        if 'content' in data and data.get('content') is not None:
            data['content'] = [c.to_dict() for c in self.content]
        return data

# ============================================================
# DIAGNOSTIC ASSESSMENT MODELS
# ============================================================

class DiagnosticQuestion(BaseQuestion):
    """Question specifically for diagnostic assessments"""
    tos_topic_title: str  # Required: Must map to TOS
    cognitive_weight: Optional[float] = Field(default=1.0, description="Weight for scoring")

class DiagnosticAssessmentBase(BaseModel):
    subject_id: str
    title: str
    instructions: Optional[str] = None
    total_items: int
    questions: List[DiagnosticQuestion]
    passing_score: Optional[float] = Field(default=75.0, description="Minimum score to pass")
    time_limit_minutes: Optional[int] = Field(default=60, description="Time limit in minutes")

class DiagnosticAssessment(DiagnosticAssessmentBase, TimestampModel):
    id: str
    def to_dict(self): 
        data = self.model_dump(exclude_none=True)
        if 'questions' in data:
            data['questions'] = [q.model_dump(exclude_none=True) for q in self.questions]
        return data


# ============================================================
# DIAGNOSTIC RESULT MODELS
# ============================================================

class TOSPerformance(BaseModel):
    """Performance breakdown by TOS topic"""
    topic_title: str
    total_questions: int
    correct_answers: int
    score_percentage: float
    bloom_breakdown: Dict[str, float]  # {"remembering": 85.0, "applying": 60.0}

class DiagnosticResultBase(BaseModel):
    user_id: str
    assessment_id: str
    subject_id: str
    overall_score: float
    passing_status: Literal["passed", "failed", "pending"]
    time_taken_seconds: int
    tos_performance: List[TOSPerformance]  # Breakdown by TOS topics
    answers: Optional[Dict[str, Any]] = None  # Store student's answers
    timestamp: Optional[str] = None

class DiagnosticResult(DiagnosticResultBase, TimestampModel):
    id: str
    def to_dict(self): 
        data = self.model_dump(exclude_none=True)
        if 'tos_performance' in data:
            data['tos_performance'] = [perf.model_dump() for perf in self.tos_performance]
        return data


# ============================================================
# CONTENT VERIFICATION MODELS
# ============================================================

class ContentVerificationBase(BaseModel):
    content_id: str  # Reference to module/quiz/assessment
    content_type: Literal["module", "quiz", "assessment", "generated_content"]
    verified_by: str  # Faculty user_id
    verification_status: Literal["pending", "approved", "rejected", "needs_revision"]
    tos_alignment_confirmed: bool = False
    bloom_level_confirmed: bool = False
    feedback: Optional[str] = None
    revision_notes: Optional[str] = None

class ContentVerification(ContentVerificationBase, TimestampModel):
    id: str
    def to_dict(self): 
        return self.model_dump(exclude_none=True)


# ============================================================
# RECOMMENDATION MODEL (Replaced Enhanced)
# ============================================================

class RecommendationBase(BaseModel):
    """Updated recommendation model that considers diagnostic results"""
    user_id: str
    subject_id: str
    recommended_topic: str  # TOS topic title
    recommended_modules: List[str]  # List of module IDs
    recommended_quizzes: List[str]  # List of quiz IDs
    bloom_focus: str
    priority: Literal["high", "medium", "low"]  # Based on diagnostic weakness
    reason: str
    diagnostic_result_id: Optional[str] = None  # Link to diagnostic that triggered this
    confidence: float
    timestamp: Optional[str] = None

class Recommendation(RecommendationBase, TimestampModel):
    id: str
    def to_dict(self): 
        return self.model_dump(exclude_none=True)


# ============================================================
# STUDY SESSION MODEL (For realistic tracking)
# ============================================================

class StudySessionBase(BaseModel):
    """Groups multiple activities into a single study session"""
    user_id: str
    subject_id: str
    session_type: Literal["diagnostic", "review", "practice", "mock_exam"]
    activity_ids: List[str]  # References to activities completed in this session
    duration_seconds: int
    avg_score: Optional[float] = None
    completion_status: Literal["completed", "in_progress", "abandoned"]
    timestamp: Optional[str] = None

class StudySession(StudySessionBase, TimestampModel):
    id: str
    def to_dict(self): 
        return self.model_dump(exclude_none=True)