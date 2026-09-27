"""
AEGIS MIND - Database models.

Privacy notes:
- Personnel are identified by a pseudonymous `personnel_code` (e.g. "PID-04831"),
  never by name, in any table used by ML/risk/analytics flows.
- The `User` table (login identity) is kept separate from `PersonnelProfile`
  (welfare data subject) so identity and welfare data are not conflated
  beyond what is strictly required for authorized access.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    personnel = "personnel"
    welfare_officer = "welfare_officer"
    administrator = "administrator"


class RiskLevelEnum(str, enum.Enum):
    low = "Low"
    moderate = "Moderate"
    high = "High"
    critical = "Critical"


class TrendEnum(str, enum.Enum):
    increasing = "Increasing"
    stable = "Stable"
    decreasing = "Decreasing"


class CaseStatusEnum(str, enum.Enum):
    new = "New"
    under_review = "Under Review"
    recommendation_made = "Recommendation Made"
    intervention_completed = "Intervention Completed"
    follow_up_due = "Follow-up Due"
    resolved = "Resolved"


class User(Base):
    """Login identity. Minimal PII: username + hashed password only."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.personnel)
    is_active = Column(Boolean, default=True)
    personnel_code = Column(String, ForeignKey("personnel_profiles.personnel_code"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    personnel_profile = relationship("PersonnelProfile", back_populates="user", uselist=False)


class PersonnelProfile(Base):
    """
    Pseudonymous welfare-data subject. No name/rank identifiers stored here
    beyond an anonymized unit code, by design (data minimization).
    """
    __tablename__ = "personnel_profiles"

    personnel_code = Column(String, primary_key=True, index=True)  # e.g. PID-04831
    unit_code = Column(String, index=True, nullable=True)          # anonymized unit/group
    consent_wellness_data = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="personnel_profile", uselist=False)
    checkins = relationship("WellnessCheckin", back_populates="personnel")
    org_records = relationship("OrganizationalRecord", back_populates="personnel")
    risk_assessments = relationship("RiskAssessment", back_populates="personnel")


class OrganizationalRecord(Base):
    """Non-voluntary organizational indicators used as model features."""
    __tablename__ = "organizational_records"

    id = Column(Integer, primary_key=True, index=True)
    personnel_code = Column(String, ForeignKey("personnel_profiles.personnel_code"))
    record_date = Column(DateTime, default=datetime.utcnow)

    weekly_duty_hours = Column(Float)
    consecutive_duty_days = Column(Integer)
    leave_days_last_90 = Column(Integer)
    night_shift_ratio = Column(Float)          # 0-1
    deployment_months_last_year = Column(Float)
    transfer_count_last_2yr = Column(Integer)
    training_load_hours = Column(Float)
    overdue_leave_flag = Column(Boolean, default=False)

    personnel = relationship("PersonnelProfile", back_populates="org_records")


class WellnessCheckin(Base):
    """Voluntary personnel-submitted wellness data. Requires consent."""
    __tablename__ = "wellness_checkins"

    id = Column(Integer, primary_key=True, index=True)
    personnel_code = Column(String, ForeignKey("personnel_profiles.personnel_code"))
    submitted_at = Column(DateTime, default=datetime.utcnow)

    stress_level = Column(Integer)       # 1-5
    mood = Column(Integer)               # 1-5
    sleep_quality = Column(Integer)      # 1-5
    fatigue_level = Column(Integer)      # 1-5
    perceived_workload = Column(Integer) # 1-5
    questionnaire_json = Column(JSON, nullable=True)  # free-form extended answers

    personnel = relationship("PersonnelProfile", back_populates="checkins")


class RiskAssessment(Base):
    """Output of the Aegis Risk Engine for one personnel_code at a point in time."""
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    personnel_code = Column(String, ForeignKey("personnel_profiles.personnel_code"))
    assessed_at = Column(DateTime, default=datetime.utcnow)

    risk_score = Column(Float)                 # 0-100
    confidence = Column(Float)                 # 0-1
    risk_level = Column(Enum(RiskLevelEnum))
    burnout_risk = Column(Float)                # 0-100
    fatigue_risk = Column(Float)                # 0-100
    trend = Column(Enum(TrendEnum), default=TrendEnum.stable)
    contributing_factors = Column(JSON)         # list[{feature, impact}]
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    model_version = Column(String, default="v1-synthetic")

    personnel = relationship("PersonnelProfile", back_populates="risk_assessments")
    case = relationship("WelfareCase", back_populates="risk_assessment", uselist=False)


class WelfareCase(Base):
    """Intervention workflow tracker: Risk Detected -> ... -> Resolved."""
    __tablename__ = "welfare_cases"

    id = Column(Integer, primary_key=True, index=True)
    personnel_code = Column(String, ForeignKey("personnel_profiles.personnel_code"))
    risk_assessment_id = Column(Integer, ForeignKey("risk_assessments.id"))
    status = Column(Enum(CaseStatusEnum), default=CaseStatusEnum.new)
    priority = Column(Integer, default=3)  # 1 highest .. 5 lowest
    recommended_action = Column(String, nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    follow_up_due_at = Column(DateTime, nullable=True)

    risk_assessment = relationship("RiskAssessment", back_populates="case")
    interventions = relationship("InterventionLog", back_populates="case")


class InterventionLog(Base):
    """Human-recorded intervention + outcome, feeding the feedback loop."""
    __tablename__ = "intervention_logs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("welfare_cases.id"))
    logged_by_user_id = Column(Integer, ForeignKey("users.id"))
    action_taken = Column(String)
    notes = Column(Text, nullable=True)
    outcome = Column(String, nullable=True)   # e.g. improved / no_change / worsened
    logged_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("WelfareCase", back_populates="interventions")


class AuditLog(Base):
    """Immutable-by-convention audit trail for authorized-access actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    resource = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String, nullable=True)


# =====================================================================
# AI MITRA — personal AI wellness & fatigue consultant
#
# This is deliberately a SEPARATE data model from WellnessCheckin /
# RiskAssessment above: those feed the organizational Aegis Risk Engine
# (CRPF welfare oversight), while AI Mitra is a private, personal
# self-reflection companion available to any logged-in user. Keeping
# them apart means a person's casual chat with Mitra is never silently
# folded into their organizational risk score.
# =====================================================================

class MitraSeverityEnum(str, enum.Enum):
    low = "Low"
    moderate = "Moderate"
    high = "High"
    very_high = "Very High"


class MitraConversation(Base):
    """One chat session with AI Mitra."""
    __tablename__ = "mitra_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, unique=True, index=True, nullable=False)
    mode = Column(String, default="chat")  # "chat" | "wellness_check"
    state_json = Column(JSON, nullable=True)  # adaptive-engine working memory
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("MitraMessage", back_populates="conversation", order_by="MitraMessage.id")


class MitraMessage(Base):
    """One turn in a Mitra conversation."""
    __tablename__ = "mitra_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("mitra_conversations.id"), nullable=False)
    role = Column(String)  # "user" | "ai"
    message = Column(Text)
    detected_language = Column(String, nullable=True)  # en | hi | hinglish
    safety_flag = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("MitraConversation", back_populates="messages")


class MitraWellnessCheck(Base):
    """Result of one completed AI Mitra wellness check (personal, not organizational)."""
    __tablename__ = "mitra_wellness_checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("mitra_conversations.id"), nullable=True)

    stress_score = Column(Float)
    fatigue_score = Column(Float)
    energy_score = Column(Float)
    sleep_score = Column(Float)
    mood_score = Column(Float)
    focus_score = Column(Float)
    wellness_score = Column(Float)

    stress_level = Column(Enum(MitraSeverityEnum), nullable=True)
    fatigue_level = Column(Enum(MitraSeverityEnum), nullable=True)

    answers_json = Column(JSON, nullable=True)      # raw adaptive-check answers
    recommendations_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MitraImageAnalysis(Base):
    """Reference + heuristic analysis note for an image the user shared with Mitra."""
    __tablename__ = "mitra_image_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("mitra_conversations.id"), nullable=True)
    image_reference = Column(String)   # stored filename/path, never raw bytes in DB
    analysis = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class MitraHeartRateReading(Base):
    """
    A single camera-based (PPG) heart-rate estimate the user chose to take.

    This is a self-measured, non-clinical estimate captured via the phone
    camera + flash in the browser (see frontend HeartRateCheck.jsx) — never
    a medical-grade reading. It supplements, but never overrides, the
    self-reported wellness scores above.
    """
    __tablename__ = "mitra_heart_rate_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("mitra_conversations.id"), nullable=True)

    bpm = Column(Float, nullable=False)
    signal_quality = Column(String, nullable=True)  # "good" | "fair" | "poor" (client-estimated)
    measured_at = Column(DateTime, default=datetime.utcnow)


class MitraConsultantRequest(Base):
    """A user's request to escalate from AI Mitra to a human consultant."""
    __tablename__ = "mitra_consultant_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("mitra_conversations.id"), nullable=True)
    reason = Column(String)             # "user_requested" | "safety_flag" | "persistent_high_stress"
    status = Column(String, default="Pending")  # Pending | Contacted | Resolved
    consultant_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
