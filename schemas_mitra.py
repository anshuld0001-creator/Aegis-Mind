from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: str
    safety_flag: bool
    suggest_wellness_check: bool


class WellnessCheckStartResponse(BaseModel):
    session_id: str
    reply: str


class WellnessCheckAnswer(BaseModel):
    session_id: str
    message: str


class WellnessCheckResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    wellness_score: float
    sleep_score: float
    energy_score: float
    stress_score: float
    mood_score: float
    fatigue_score: float
    focus_score: float
    stress_level: str
    fatigue_level: str
    sleep_level: str
    energy_level: str
    mood_level: str
    focus_level: str
    headline: str
    recommendations: List[str]


class WellnessCheckStepResponse(BaseModel):
    reply: str
    done: bool
    result: Optional[WellnessCheckResult] = None
    safety_flag: bool = False


class QuickStressCheckIn(BaseModel):
    """A short, voluntary self-report; values are deliberately simple 1–5 scales."""
    stress_level: int
    sleep_quality: int
    fatigue_level: int
    perceived_workload: int
    mood: int


class QuickStressCheckOut(BaseModel):
    wellness_score: float
    stress_score: float
    stress_level: str
    fatigue_score: float
    headline: str
    recommendations: List[str]
    needs_human_follow_up: bool = False


class ConsultantRequestIn(BaseModel):
    session_id: Optional[str] = None


class ConsultantRequestOut(BaseModel):
    id: int
    status: str
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True


class ImageAnalysisOut(BaseModel):
    id: int
    analysis: str
    created_at: datetime

    class Config:
        from_attributes = True


class HeartRateIn(BaseModel):
    session_id: Optional[str] = None
    bpm: float
    signal_quality: Optional[str] = None  # "good" | "fair" | "poor"


class HeartRateOut(BaseModel):
    id: int
    bpm: float
    band: str
    note: str
    measured_at: datetime

    class Config:
        from_attributes = True
