from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    personnel_code: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "personnel"
    personnel_code: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Wellness check-in ----------
class CheckinCreate(BaseModel):
    stress_level: int = Field(ge=1, le=5)
    mood: int = Field(ge=1, le=5)
    sleep_quality: int = Field(ge=1, le=5)
    fatigue_level: int = Field(ge=1, le=5)
    perceived_workload: int = Field(ge=1, le=5)
    questionnaire_json: Optional[dict] = None


class CheckinOut(CheckinCreate):
    id: int
    personnel_code: str
    submitted_at: datetime

    class Config:
        from_attributes = True


# ---------- Risk ----------
class ContributingFactor(BaseModel):
    feature: str
    impact: float  # SHAP-style signed contribution
    direction: str  # "increases_risk" | "decreases_risk"


class RiskAssessmentOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    personnel_code: str
    assessed_at: datetime
    risk_score: float
    confidence: float
    risk_level: str
    burnout_risk: float
    fatigue_risk: float
    trend: str
    contributing_factors: List[ContributingFactor]
    is_anomaly: bool
    anomaly_score: Optional[float]
    model_version: str


class RiskRunRequest(BaseModel):
    personnel_code: Optional[str] = None  # if None, run for all (admin/batch)


# ---------- Cases ----------
class CaseOut(BaseModel):
    id: int
    personnel_code: str
    status: str
    priority: int
    recommended_action: Optional[str]
    created_at: datetime
    updated_at: datetime
    follow_up_due_at: Optional[datetime]
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    trend: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class CaseStatusUpdate(BaseModel):
    status: str
    recommended_action: Optional[str] = None
    follow_up_due_at: Optional[datetime] = None


class InterventionCreate(BaseModel):
    action_taken: str
    notes: Optional[str] = None
    outcome: Optional[str] = None


class InterventionOut(InterventionCreate):
    id: int
    case_id: int
    logged_by_user_id: int
    logged_at: datetime

    class Config:
        from_attributes = True


# ---------- Analytics ----------
class DashboardSummary(BaseModel):
    total_personnel: int
    high_risk_count: int
    critical_risk_count: int
    pending_interventions: int
    average_risk_score: float
    stress_trend: str
    burnout_trend: str
    workload_trend: str
    risk_distribution: dict
    intervention_status_counts: dict
    anomaly_alert_count: int
