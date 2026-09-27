from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.utils.rbac import require_roles, write_audit_log

router = APIRouter(prefix="/api/cases", tags=["welfare cases"])


def _to_case_out(case: models.WelfareCase) -> schemas.CaseOut:
    ra = case.risk_assessment
    return schemas.CaseOut(
        id=case.id,
        personnel_code=case.personnel_code,
        status=case.status.value,
        priority=case.priority,
        recommended_action=case.recommended_action,
        created_at=case.created_at,
        updated_at=case.updated_at,
        follow_up_due_at=case.follow_up_due_at,
        risk_score=ra.risk_score if ra else None,
        risk_level=ra.risk_level.value if ra else None,
        trend=ra.trend.value if ra else None,
        confidence=ra.confidence if ra else None,
    )


@router.get("", response_model=List[schemas.CaseOut])
def list_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    """Risk Priority Board — authorized-only. Never exposes a public ranking."""
    q = db.query(models.WelfareCase)
    if status_filter:
        q = q.filter(models.WelfareCase.status == models.CaseStatusEnum(status_filter))
    cases = q.order_by(models.WelfareCase.priority.asc(), models.WelfareCase.updated_at.desc()).all()
    return [_to_case_out(c) for c in cases]


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    case = db.query(models.WelfareCase).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return _to_case_out(case)


@router.patch("/{case_id}/status", response_model=schemas.CaseOut)
def update_case_status(
    case_id: int,
    payload: schemas.CaseStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    """Human-in-the-loop status transition. AI never sets this automatically past 'New'."""
    case = db.query(models.WelfareCase).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case.status = models.CaseStatusEnum(payload.status)
    if payload.recommended_action:
        case.recommended_action = payload.recommended_action
    if payload.follow_up_due_at:
        case.follow_up_due_at = payload.follow_up_due_at
    case.reviewed_by_user_id = user.id
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    write_audit_log(db, user.id, "update_case_status", "welfare_cases", f"case={case_id} -> {payload.status}")
    return _to_case_out(case)


@router.post("/{case_id}/interventions", response_model=schemas.InterventionOut, status_code=201)
def log_intervention(
    case_id: int,
    payload: schemas.InterventionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    case = db.query(models.WelfareCase).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    log = models.InterventionLog(
        case_id=case_id,
        logged_by_user_id=user.id,
        action_taken=payload.action_taken,
        notes=payload.notes,
        outcome=payload.outcome,
    )
    db.add(log)
    if case.status in (models.CaseStatusEnum.new, models.CaseStatusEnum.under_review, models.CaseStatusEnum.recommendation_made):
        case.status = models.CaseStatusEnum.intervention_completed
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    write_audit_log(db, user.id, "log_intervention", "intervention_logs", f"case={case_id}")
    return log


@router.get("/{case_id}/interventions", response_model=List[schemas.InterventionOut])
def list_interventions(
    case_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    rows = db.query(models.InterventionLog).filter_by(case_id=case_id).order_by(models.InterventionLog.logged_at.desc()).all()
    return rows
