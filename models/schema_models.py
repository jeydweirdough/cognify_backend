from pydantic import BaseModel, RootModel
from typing import Optional, List, Dict, Any


class Activity(BaseModel):
    activity_id: str
    student_id: str
    subject_id: Optional[str] = None
    activity_type: Optional[str] = None
    activity_ref: Optional[str] = None
    bloom_level: Optional[str] = None
    score: Optional[float] = None
    completion_rate: Optional[float] = None
    duration: Optional[int] = None
    timestamp: Optional[str] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class Question(BaseModel):
    question_id: str
    topic_title: Optional[str] = None
    bloom_level: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None


class Assessment(BaseModel):
    assessment_id: str
    type: Optional[str] = None
    subject_id: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    total_items: Optional[int] = None
    questions: Optional[List[Question]] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class Module(BaseModel):
    module_id: str
    subject_id: Optional[str] = None
    title: Optional[str] = None
    purpose: Optional[str] = None
    bloom_level: Optional[str] = None
    material_type: Optional[str] = None
    material_url: Optional[str] = None
    estimated_time: Optional[int] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class Quiz(BaseModel):
    quiz_id: str
    subject_id: Optional[str] = None
    topic_title: Optional[str] = None
    bloom_level: Optional[str] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[Any] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class Recommendation(BaseModel):
    recommendation_id: str
    student_id: str
    subject_id: Optional[str] = None
    recommended_topic: Optional[str] = None
    recommended_module: Optional[str] = None
    bloom_focus: Optional[str] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: Optional[str] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class StudentProgress(RootModel):
    # generic progress mapping topic -> progress float
    root: Dict[str, float]


class Student(BaseModel):
    student_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    pre_assessment_score: Optional[float] = None
    ai_confidence: Optional[float] = None
    current_module: Optional[str] = None
    progress: Optional[Dict[str, float]] = None

    def to_dict(self):
        return self.dict(exclude_none=True)


class BloomEntry(RootModel):
    # each item is a mapping like {"remembering": 8}
    root: Dict[str, int]


class SubContent(BaseModel):
    purpose: Optional[str] = None
    blooms_taxonomy: Optional[List[Dict[str, int]]] = None


class ContentSection(BaseModel):
    title: Optional[str] = None
    sub_content: Optional[List[SubContent]] = None
    no_items: Optional[int] = None
    weight_total: Optional[float] = None


class TOS(BaseModel):
    id: str
    subject: Optional[str] = None
    pqf_level: Optional[int] = None
    difficulty_distribution: Optional[Dict[str, float]] = None
    content: Optional[List[ContentSection]] = None
    total_items: Optional[int] = None

    def to_dict(self):
        return self.dict(exclude_none=True)
