"""
AI MITRA — personal AI wellness & fatigue consultant.

Available to any authenticated user (not just `personnel` role) since this
is a private, personal companion feature — separate from the organizational
Aegis Risk Engine used elsewhere in the app.
"""
import os
import uuid
import copy
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.utils.rbac import get_current_user, require_roles, write_audit_log
from app import models
from app.mitra import engine, safety, scoring
from app.schemas_mitra import (
    ChatRequest, ChatResponse, WellnessCheckAnswer, WellnessCheckStartResponse,
    WellnessCheckStepResponse, WellnessCheckResult, ConsultantRequestIn,
    ConsultantRequestOut, ImageAnalysisOut, HeartRateIn, HeartRateOut,
    QuickStressCheckIn, QuickStressCheckOut,
)

router = APIRouter(prefix="/api/mitra", tags=["ai-mitra"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "mitra")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


def _get_or_create_conversation(db: Session, user_id: int, session_id: str, mode: str) -> models.MitraConversation:
    conv = db.query(models.MitraConversation).filter_by(session_id=session_id, user_id=user_id).first()
    if not conv:
        conv = models.MitraConversation(user_id=user_id, session_id=session_id, mode=mode, state_json={})
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


def _save_message(db: Session, conversation_id: int, role: str, message: str, lang: str = None, safety_flag: bool = False):
    db.add(models.MitraMessage(
        conversation_id=conversation_id, role=role, message=message,
        detected_language=lang, safety_flag=safety_flag,
    ))
    db.commit()


def _maybe_escalate(db: Session, user_id: int, conversation_id: int, reason: str):
    existing = db.query(models.MitraConsultantRequest).filter_by(
        user_id=user_id, conversation_id=conversation_id, reason=reason, status="Pending"
    ).first()
    if existing:
        return existing
    req = models.MitraConsultantRequest(user_id=user_id, conversation_id=conversation_id, reason=reason)
    db.add(req)
    db.commit()
    write_audit_log(db, user_id, "mitra_safety_escalation", resource=f"conversation:{conversation_id}")
    return req


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session_id = payload.session_id or f"mitra-{uuid.uuid4().hex[:12]}"
    conv = _get_or_create_conversation(db, user.id, session_id, "chat")

    state = copy.deepcopy(conv.state_json) if conv.state_json else engine.new_state()
    _save_message(db, conv.id, "user", payload.message)

    result = engine.handle_chat_message(state, payload.message)

    conv.state_json = result["state"]
    flag_modified(conv, "state_json")
    conv.updated_at = datetime.utcnow()
    db.commit()

    _save_message(db, conv.id, "ai", result["reply"], lang=result["language"], safety_flag=result["safety_flag"])

    if result["safety_flag"]:
        _maybe_escalate(db, user.id, conv.id, "safety_flag")

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        language=result["language"],
        safety_flag=result["safety_flag"],
        suggest_wellness_check=result["suggest_wellness_check"],
    )


# ---------------------------------------------------------------------------
# Structured wellness check
# ---------------------------------------------------------------------------
@router.post("/wellness-check/start", response_model=WellnessCheckStartResponse)
def start_check(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    session_id = f"mitra-check-{uuid.uuid4().hex[:12]}"
    conv = _get_or_create_conversation(db, user.id, session_id, "wellness_check")

    result = engine.start_wellness_check("en")
    conv.state_json = result["state"]
    flag_modified(conv, "state_json")
    db.commit()
    _save_message(db, conv.id, "ai", result["reply"])

    return WellnessCheckStartResponse(session_id=session_id, reply=result["reply"])


@router.post("/wellness-check/answer", response_model=WellnessCheckStepResponse)
def answer_check(payload: WellnessCheckAnswer, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(models.MitraConversation).filter_by(session_id=payload.session_id, user_id=user.id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Wellness check session not found.")

    _save_message(db, conv.id, "user", payload.message)
    outcome = engine.continue_wellness_check(copy.deepcopy(conv.state_json) or {}, payload.message)

    conv.state_json = outcome["state"]
    flag_modified(conv, "state_json")
    conv.updated_at = datetime.utcnow()
    db.commit()

    _save_message(db, conv.id, "ai", outcome["reply"], safety_flag=outcome.get("safety_flag", False))

    if outcome.get("safety_flag"):
        _maybe_escalate(db, user.id, conv.id, "safety_flag")
        return WellnessCheckStepResponse(reply=outcome["reply"], done=False, result=None, safety_flag=True)

    result_out = None
    if outcome["done"]:
        r = outcome["result"]
        check = models.MitraWellnessCheck(
            user_id=user.id, conversation_id=conv.id,
            stress_score=r["stress_score"], fatigue_score=r["fatigue_score"],
            energy_score=r["energy_score"], sleep_score=r["sleep_score"],
            mood_score=r["mood_score"], focus_score=r["focus_score"],
            wellness_score=r["wellness_score"],
            stress_level=r["stress_level"], fatigue_level=r["fatigue_level"],
            answers_json=conv.state_json.get("answers", {}),
            recommendations_json=r["recommendations"],
        )
        db.add(check)
        db.commit()
        result_out = WellnessCheckResult(**r)

        # Persistent high stress/fatigue -> offer human consultant proactively
        if r["stress_score"] >= 80 or r["fatigue_score"] >= 80:
            _maybe_escalate(db, user.id, conv.id, "persistent_high_stress")

    return WellnessCheckStepResponse(reply=outcome["reply"], done=outcome["done"], result=result_out, safety_flag=False)


# ---------------------------------------------------------------------------
# Quick stress dashboard
# ---------------------------------------------------------------------------
@router.post("/quick-stress-check", response_model=QuickStressCheckOut)
def quick_stress_check(payload: QuickStressCheckIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return an immediate, non-diagnostic result from a five-question check-in."""
    answers = payload.model_dump()
    if any(value < 1 or value > 5 for value in answers.values()):
        raise HTTPException(status_code=422, detail="Each check-in answer must be between 1 and 5.")

    # Stress, fatigue and workload increase risk; sleep and mood are protective.
    stress = min(100, max(0, round((answers["stress_level"] * 14) + (answers["perceived_workload"] * 5) + (answers["fatigue_level"] * 3) - (answers["sleep_quality"] * 2))))
    scores = {
        "stress": stress,
        "fatigue": answers["fatigue_level"] * 20,
        "sleep": answers["sleep_quality"] * 20,
        "energy": max(0, 100 - answers["fatigue_level"] * 16),
        "mood": answers["mood"] * 20,
        "focus": max(0, 100 - answers["perceived_workload"] * 12),
    }
    result = scoring.summarize(scores)
    result["headline"] = scoring.headline_explanation(result)
    result["recommendations"] = [
        "Take a short pause: water, slow breathing, or a brief walk can help reset your next hour.",
        "Choose one manageable next task and defer anything non-urgent if possible.",
    ]
    needs_follow_up = result["stress_score"] >= 80 or result["fatigue_score"] >= 80
    if needs_follow_up:
        result["recommendations"].append("You can request a confidential human follow-up whenever you want.")

    db.add(models.MitraWellnessCheck(
        user_id=user.id, stress_score=result["stress_score"], fatigue_score=result["fatigue_score"],
        energy_score=result["energy_score"], sleep_score=result["sleep_score"], mood_score=result["mood_score"],
        focus_score=result["focus_score"], wellness_score=result["wellness_score"],
        stress_level=result["stress_level"], fatigue_level=result["fatigue_level"],
        answers_json=answers, recommendations_json=result["recommendations"],
    ))
    db.commit()
    return QuickStressCheckOut(**result, needs_human_follow_up=needs_follow_up)


# ---------------------------------------------------------------------------
# Image analysis (heuristic — see module docstring in app/mitra/engine.py
# for why this isn't a real vision model call in this deployment)
# ---------------------------------------------------------------------------
@router.post("/image-analyze", response_model=ImageAnalysisOut)
async def analyze_image(
    file: UploadFile = File(...),
    session_id: str = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use PNG, JPEG, or WEBP.")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large (max 8MB).")

    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[file.content_type]
    filename = f"{user.id}-{uuid.uuid4().hex[:10]}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    # Heuristic, non-diagnostic note. A real vision-LLM call would slot in
    # here (see AI_PROVIDER_API_KEY in app/config.py) behind this same
    # response shape.
    analysis = (
        "Thanks for sharing this. I can't reliably analyze image content in this "
        "deployment yet, and either way I can't determine anyone's health or "
        "mental state from an image. If this is a schedule or workload document, "
        "a good general habit is to make sure it includes short recovery breaks "
        "between long stretches of work."
    )

    conv_id = None
    if session_id:
        conv = db.query(models.MitraConversation).filter_by(session_id=session_id, user_id=user.id).first()
        conv_id = conv.id if conv else None

    record = models.MitraImageAnalysis(
        user_id=user.id, conversation_id=conv_id, image_reference=filename, analysis=analysis,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ImageAnalysisOut(id=record.id, analysis=record.analysis, created_at=record.created_at)


# ---------------------------------------------------------------------------
# Heart rate (camera/flash PPG self-measurement)
#
# The estimate itself is computed entirely client-side (browser camera +
# flash, see frontend HeartRateCheck.jsx) — the server never receives raw
# video. This endpoint only logs the final bpm figure the client computed
# and returns a plain-language, non-diagnostic reference band for it.
# ---------------------------------------------------------------------------
@router.post("/heart-rate", response_model=HeartRateOut)
def log_heart_rate(payload: HeartRateIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.bpm < 25 or payload.bpm > 240:
        raise HTTPException(status_code=400, detail="That reading looks out of range — please try measuring again.")

    conv_id = None
    if payload.session_id:
        conv = db.query(models.MitraConversation).filter_by(session_id=payload.session_id, user_id=user.id).first()
        conv_id = conv.id if conv else None

    record = models.MitraHeartRateReading(
        user_id=user.id, conversation_id=conv_id, bpm=payload.bpm, signal_quality=payload.signal_quality,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    band, note = scoring.heart_rate_band(payload.bpm)
    return HeartRateOut(id=record.id, bpm=record.bpm, band=band, note=note, measured_at=record.measured_at)


@router.get("/heart-rate/history")
def heart_rate_history(days: int = 14, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    readings = (
        db.query(models.MitraHeartRateReading)
        .filter(models.MitraHeartRateReading.user_id == user.id, models.MitraHeartRateReading.measured_at >= since)
        .order_by(models.MitraHeartRateReading.measured_at.asc())
        .all()
    )
    return [{"bpm": r.bpm, "measured_at": r.measured_at} for r in readings]


# ---------------------------------------------------------------------------
# History / reports
# ---------------------------------------------------------------------------
@router.get("/today")
def today(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=24)
    check = (
        db.query(models.MitraWellnessCheck)
        .filter(models.MitraWellnessCheck.user_id == user.id, models.MitraWellnessCheck.created_at >= since)
        .order_by(models.MitraWellnessCheck.created_at.desc())
        .first()
    )
    if not check:
        return {"available": False, "message": "No wellness check completed in the last 24 hours yet."}
    return {
        "available": True,
        "wellness_score": check.wellness_score,
        "stress_score": check.stress_score, "stress_level": check.stress_level,
        "fatigue_score": check.fatigue_score, "fatigue_level": check.fatigue_level,
        "energy_score": check.energy_score,
        "sleep_score": check.sleep_score,
        "mood_score": check.mood_score,
        "focus_score": check.focus_score,
        "recommendations": check.recommendations_json,
        "created_at": check.created_at,
    }


@router.get("/history")
def history(days: int = 30, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    checks = (
        db.query(models.MitraWellnessCheck)
        .filter(models.MitraWellnessCheck.user_id == user.id, models.MitraWellnessCheck.created_at >= since)
        .order_by(models.MitraWellnessCheck.created_at.asc())
        .all()
    )
    return [
        {
            "created_at": c.created_at, "wellness_score": c.wellness_score,
            "stress_score": c.stress_score, "fatigue_score": c.fatigue_score,
            "energy_score": c.energy_score, "sleep_score": c.sleep_score,
            "mood_score": c.mood_score, "focus_score": c.focus_score,
        }
        for c in checks
    ]


@router.get("/weekly-report")
def weekly_report(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)
    checks = (
        db.query(models.MitraWellnessCheck)
        .filter(models.MitraWellnessCheck.user_id == user.id, models.MitraWellnessCheck.created_at >= since)
        .order_by(models.MitraWellnessCheck.created_at.asc())
        .all()
    )
    if not checks:
        return {"available": False, "message": "Not enough check-ins in the last 7 days for a report yet."}

    def avg(attr):
        vals = [getattr(c, attr) for c in checks if getattr(c, attr) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    by_day = {}
    for c in checks:
        day = c.created_at.strftime("%A")
        by_day.setdefault(day, []).append(c.stress_score)
    worst_day = max(by_day, key=lambda d: sum(by_day[d]) / len(by_day[d])) if by_day else None
    best_day = min(
        {c.created_at.strftime("%A"): c.wellness_score for c in checks}.items(),
        key=lambda kv: -kv[1], default=(None, None),
    )[0]

    return {
        "available": True,
        "n_checkins": len(checks),
        "average_wellness_score": avg("wellness_score"),
        "average_stress_score": avg("stress_score"),
        "average_fatigue_score": avg("fatigue_score"),
        "average_energy_score": avg("energy_score"),
        "average_sleep_score": avg("sleep_score"),
        "average_mood_score": avg("mood_score"),
        "most_stressful_day": worst_day,
        "best_wellness_day": best_day,
        "note": "Trends are based on your own self-reported check-ins and are not a clinical assessment.",
    }


# ---------------------------------------------------------------------------
# Human consultant escalation
# ---------------------------------------------------------------------------
@router.post("/consultant-request", response_model=ConsultantRequestOut)
def request_consultant(payload: ConsultantRequestIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_id = None
    if payload.session_id:
        conv = db.query(models.MitraConversation).filter_by(session_id=payload.session_id, user_id=user.id).first()
        conv_id = conv.id if conv else None

    req = models.MitraConsultantRequest(user_id=user.id, conversation_id=conv_id, reason="user_requested")
    db.add(req)
    db.commit()
    db.refresh(req)
    write_audit_log(db, user.id, "mitra_consultant_requested", resource=f"request:{req.id}")
    return ConsultantRequestOut(id=req.id, status=req.status, reason=req.reason, created_at=req.created_at)


@router.get("/consultant/requests")
def list_consultant_requests(
    status: str = None,
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
    db: Session = Depends(get_db),
):
    q = db.query(models.MitraConsultantRequest)
    if status:
        q = q.filter(models.MitraConsultantRequest.status == status)
    reqs = q.order_by(models.MitraConsultantRequest.created_at.desc()).all()
    return [
        {
            "id": r.id, "user_id": r.user_id, "reason": r.reason, "status": r.status,
            "consultant_notes": r.consultant_notes, "created_at": r.created_at,
        }
        for r in reqs
    ]


@router.patch("/consultant/requests/{request_id}")
def update_consultant_request(
    request_id: int,
    status: str,
    notes: str = None,
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
    db: Session = Depends(get_db),
):
    req = db.query(models.MitraConsultantRequest).get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
    req.status = status
    if notes:
        req.consultant_notes = notes
    if status == "Resolved":
        req.resolved_at = datetime.utcnow()
    db.commit()
    write_audit_log(db, user.id, "mitra_consultant_request_updated", resource=f"request:{request_id}", detail=status)
    return {"id": req.id, "status": req.status}


@router.get("/conversations")
def list_conversations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = (
        db.query(models.MitraConversation)
        .filter_by(user_id=user.id)
        .order_by(models.MitraConversation.updated_at.desc())
        .all()
    )
    return [
        {"session_id": c.session_id, "mode": c.mode, "updated_at": c.updated_at, "created_at": c.created_at}
        for c in convs
    ]
