from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.utils.rbac import require_roles

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _latest_assessment_subquery(db: Session):
    """Get the most recent RiskAssessment per personnel_code."""
    all_assessments = db.query(models.RiskAssessment).order_by(
        models.RiskAssessment.personnel_code, models.RiskAssessment.assessed_at.desc()
    ).all()
    latest = {}
    for a in all_assessments:
        if a.personnel_code not in latest:
            latest[a.personnel_code] = a
    return list(latest.values())


@router.get("/dashboard", response_model=schemas.DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    total_personnel = db.query(models.PersonnelProfile).count()
    latest = _latest_assessment_subquery(db)

    level_counts = Counter(a.risk_level.value for a in latest)
    trend_counts = Counter(a.trend.value for a in latest)
    avg_risk = round(sum(a.risk_score for a in latest) / len(latest), 1) if latest else 0.0
    anomaly_count = sum(1 for a in latest if a.is_anomaly)

    pending = db.query(models.WelfareCase).filter(
        models.WelfareCase.status.notin_([models.CaseStatusEnum.resolved])
    ).count()

    case_status_counts = Counter(
        c.status.value for c in db.query(models.WelfareCase).all()
    )

    def dominant_trend():
        if not trend_counts:
            return "Stable"
        return trend_counts.most_common(1)[0][0]

    return schemas.DashboardSummary(
        total_personnel=total_personnel,
        high_risk_count=level_counts.get("High", 0),
        critical_risk_count=level_counts.get("Critical", 0),
        pending_interventions=pending,
        average_risk_score=avg_risk,
        stress_trend=dominant_trend(),
        burnout_trend=dominant_trend(),
        workload_trend=dominant_trend(),
        risk_distribution={
            "Low": level_counts.get("Low", 0),
            "Moderate": level_counts.get("Moderate", 0),
            "High": level_counts.get("High", 0),
            "Critical": level_counts.get("Critical", 0),
        },
        intervention_status_counts=dict(case_status_counts),
        anomaly_alert_count=anomaly_count,
    )


@router.get("/model-performance")
def model_performance(
    user: models.User = Depends(require_roles("administrator")),
):
    """Surfaces the offline evaluation metrics.json produced by ml/train_models.py."""
    import json
    from pathlib import Path

    metrics_path = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "models" / "metrics.json"
    if not metrics_path.exists():
        return {"available": False, "message": "Run ml/train_models.py to generate metrics."}
    with open(metrics_path) as f:
        data = json.load(f)
    data["available"] = True
    return data


@router.get("/trend/{personnel_code}")
def personnel_trend(
    personnel_code: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("welfare_officer", "administrator")),
):
    rows = (
        db.query(models.RiskAssessment)
        .filter_by(personnel_code=personnel_code)
        .order_by(models.RiskAssessment.assessed_at.asc())
        .all()
    )
    return [
        {
            "assessed_at": r.assessed_at.isoformat(),
            "risk_score": r.risk_score,
            "burnout_risk": r.burnout_risk,
            "fatigue_risk": r.fatigue_risk,
        }
        for r in rows
    ]
