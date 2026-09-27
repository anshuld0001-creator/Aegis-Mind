from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ml.risk_engine import risk_engine
from app.ml.recommendation import recommend, default_priority
from app.utils.rbac import get_current_user, require_roles, write_audit_log

router = APIRouter(prefix="/api/risk", tags=["risk engine"])


def _latest_feature_row(db: Session, personnel_code: str) -> Optional[dict]:
    org = (
        db.query(models.OrganizationalRecord)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.OrganizationalRecord.record_date.desc())
        .first()
    )
    checkin = (
        db.query(models.WellnessCheckin)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.WellnessCheckin.submitted_at.desc())
        .first()
    )
    if not org and not checkin:
        return None

    return {
        "weekly_duty_hours": org.weekly_duty_hours if org else 50,
        "consecutive_duty_days": org.consecutive_duty_days if org else 5,
        "leave_days_last_90": org.leave_days_last_90 if org else 9,
        "night_shift_ratio": org.night_shift_ratio if org else 0.3,
        "deployment_months_last_year": org.deployment_months_last_year if org else 4,
        "transfer_count_last_2yr": org.transfer_count_last_2yr if org else 1,
        "training_load_hours": org.training_load_hours if org else 20,
        "stress_level": checkin.stress_level if checkin else 3,
        "mood": checkin.mood if checkin else 3,
        "sleep_quality": checkin.sleep_quality if checkin else 3,
        "fatigue_level": checkin.fatigue_level if checkin else 3,
        "perceived_workload": checkin.perceived_workload if checkin else 3,
    }


def run_assessment_for(db: Session, personnel_code: str) -> models.RiskAssessment:
    features = _latest_feature_row(db, personnel_code)
    if features is None:
        raise HTTPException(status_code=400, detail="No data available for this personnel_code yet.")

    prev = (
        db.query(models.RiskAssessment)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.RiskAssessment.assessed_at.desc())
        .first()
    )
    prev_score = prev.risk_score if prev else None

    result = risk_engine.assess(features, previous_score=prev_score)

    assessment = models.RiskAssessment(
        personnel_code=personnel_code,
        risk_score=result["risk_score"],
        confidence=result["confidence"],
        risk_level=models.RiskLevelEnum(result["risk_level"]),
        burnout_risk=result["burnout_risk"],
        fatigue_risk=result["fatigue_risk"],
        trend=models.TrendEnum(result["trend"]),
        contributing_factors=result["contributing_factors"],
        is_anomaly=result["is_anomaly"],
        anomaly_score=result["anomaly_score"],
        model_version=result["model_version"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    # Early warning: auto-open/update a welfare case when risk crosses Moderate+
    if result["risk_level"] in ("Moderate", "High", "Critical"):
        existing_open_case = (
            db.query(models.WelfareCase)
            .filter(
                models.WelfareCase.personnel_code == personnel_code,
                models.WelfareCase.status.notin_([
                    models.CaseStatusEnum.resolved,
                ]),
            )
            .order_by(models.WelfareCase.created_at.desc())
            .first()
        )
        action = recommend(result["risk_level"], result["contributing_factors"], result["is_anomaly"])
        if existing_open_case:
            existing_open_case.risk_assessment_id = assessment.id
            existing_open_case.recommended_action = action
            existing_open_case.priority = default_priority(result["risk_level"])
        else:
            case = models.WelfareCase(
                personnel_code=personnel_code,
                risk_assessment_id=assessment.id,
                status=models.CaseStatusEnum.new,
                priority=default_priority(result["risk_level"]),
                recommended_action=action,
            )
            db.add(case)
        db.commit()

    return assessment


@router.post("/run/{personnel_code}", response_model=schemas.RiskAssessmentOut)
def run_assessment(
    personnel_code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator", "personnel")),
):
    if user.role.value == "personnel" and user.personnel_code != personnel_code:
        raise HTTPException(status_code=403, detail="Personnel may only trigger their own assessment.")
    assessment = run_assessment_for(db, personnel_code)
    write_audit_log(db, user.id, "run_risk_assessment", "risk_assessments", personnel_code)
    return assessment


@router.post("/run-batch")
def run_batch(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("administrator")),
):
    """Administrator-triggered batch scoring across all personnel with data on file."""
    codes = [p.personnel_code for p in db.query(models.PersonnelProfile).all()]
    ran, skipped = 0, 0
    for code in codes:
        try:
            run_assessment_for(db, code)
            ran += 1
        except HTTPException:
            skipped += 1
    write_audit_log(db, user.id, "run_batch_assessment", "risk_assessments", f"ran={ran} skipped={skipped}")
    return {"ran": ran, "skipped": skipped}


@router.get("/latest/{personnel_code}", response_model=schemas.RiskAssessmentOut)
def latest_assessment(
    personnel_code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role.value == "personnel" and user.personnel_code != personnel_code:
        raise HTTPException(status_code=403, detail="Not authorized to view this record.")
    assessment = (
        db.query(models.RiskAssessment)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.RiskAssessment.assessed_at.desc())
        .first()
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="No assessment found yet.")
    return assessment


@router.get("/history/{personnel_code}", response_model=List[schemas.RiskAssessmentOut])
def assessment_history(
    personnel_code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role.value == "personnel" and user.personnel_code != personnel_code:
        raise HTTPException(status_code=403, detail="Not authorized to view this record.")
    rows = (
        db.query(models.RiskAssessment)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.RiskAssessment.assessed_at.asc())
        .all()
    )
    return rows
