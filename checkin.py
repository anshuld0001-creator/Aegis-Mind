from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.utils.rbac import get_current_user, require_roles, write_audit_log

router = APIRouter(prefix="/api/checkin", tags=["wellness check-in"])


@router.post("", response_model=schemas.CheckinOut, status_code=201)
def submit_checkin(
    payload: schemas.CheckinCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("personnel")),
):
    """Voluntary personnel wellness check-in. Requires prior consent on file."""
    profile = db.query(models.PersonnelProfile).filter_by(personnel_code=user.personnel_code).first()
    if not profile:
        raise HTTPException(status_code=400, detail="No personnel profile linked to this account.")
    if not profile.consent_wellness_data:
        raise HTTPException(status_code=403, detail="Wellness data consent not on file.")

    checkin = models.WellnessCheckin(
        personnel_code=user.personnel_code,
        stress_level=payload.stress_level,
        mood=payload.mood,
        sleep_quality=payload.sleep_quality,
        fatigue_level=payload.fatigue_level,
        perceived_workload=payload.perceived_workload,
        questionnaire_json=payload.questionnaire_json,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    write_audit_log(db, user.id, "submit_checkin", "wellness_checkins", checkin.personnel_code)
    return checkin


@router.get("/history", response_model=List[schemas.CheckinOut])
def my_history(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("personnel")),
):
    rows = (
        db.query(models.WellnessCheckin)
        .filter_by(personnel_code=user.personnel_code)
        .order_by(models.WellnessCheckin.submitted_at.desc())
        .limit(50)
        .all()
    )
    return rows


@router.get("/history/{personnel_code}", response_model=List[schemas.CheckinOut])
def personnel_history_for_officer(
    personnel_code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    """Authorized welfare staff may view a specific pseudonymous personnel_code's history."""
    rows = (
        db.query(models.WellnessCheckin)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.WellnessCheckin.submitted_at.desc())
        .limit(50)
        .all()
    )
    write_audit_log(db, user.id, "view_checkin_history", "wellness_checkins", personnel_code)
    return rows
