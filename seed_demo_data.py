"""
AEGIS MIND - Demo data seeder.

Populates the (SQLite, by default) database with:
  1. Three demo login accounts, one per role.
  2. A subset of the synthetic organizational + wellness dataset
     (see ../ml/generate_synthetic_data.py) loaded as PersonnelProfile /
     OrganizationalRecord / WellnessCheckin rows.
  3. An initial batch risk assessment run so the dashboards aren't empty
     on first login.

Run AFTER:
  python ../ml/generate_synthetic_data.py
  python ../ml/train_models.py

Usage (from backend/):
  python seed_demo_data.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import Base, engine, SessionLocal
from app import models
from app.utils.security import hash_password

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_personnel_data.csv"
N_SEED_PERSONNEL = 60  # keep the demo dataset small enough to browse comfortably

DEMO_ACCOUNTS = [
    # username, password, role, personnel_code
    ("personnel1", "Personnel@123", models.RoleEnum.personnel, "PID-00001"),
    ("officer1", "Officer@123", models.RoleEnum.welfare_officer, None),
    ("admin1", "Admin@123", models.RoleEnum.administrator, None),
]


def get_or_create_profile(db, personnel_code, unit_code=None, consent=True):
    profile = db.query(models.PersonnelProfile).filter_by(personnel_code=personnel_code).first()
    if not profile:
        profile = models.PersonnelProfile(
            personnel_code=personnel_code, unit_code=unit_code, consent_wellness_data=consent
        )
        db.add(profile)
        db.commit()
    return profile


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found.")
        print("Run: python ml/generate_synthetic_data.py   (from the repo root) first.")
        return

    df = pd.read_csv(DATA_PATH).head(N_SEED_PERSONNEL)

    print(f"Seeding {len(df)} synthetic personnel records into the database...")
    for _, row in df.iterrows():
        profile = get_or_create_profile(db, row["personnel_code"], row["unit_code"], consent=True)

        org = models.OrganizationalRecord(
            personnel_code=profile.personnel_code,
            weekly_duty_hours=row["weekly_duty_hours"],
            consecutive_duty_days=int(row["consecutive_duty_days"]),
            leave_days_last_90=int(row["leave_days_last_90"]),
            night_shift_ratio=row["night_shift_ratio"],
            deployment_months_last_year=row["deployment_months_last_year"],
            transfer_count_last_2yr=int(row["transfer_count_last_2yr"]),
            training_load_hours=row["training_load_hours"],
            overdue_leave_flag=bool(row["overdue_leave_flag"]),
        )
        db.add(org)

        checkin = models.WellnessCheckin(
            personnel_code=profile.personnel_code,
            stress_level=int(row["stress_level"]),
            mood=int(row["mood"]),
            sleep_quality=int(row["sleep_quality"]),
            fatigue_level=int(row["fatigue_level"]),
            perceived_workload=int(row["perceived_workload"]),
        )
        db.add(checkin)
    db.commit()

    print("Creating demo login accounts (personnel1 / officer1 / admin1)...")
    for username, password, role, personnel_code in DEMO_ACCOUNTS:
        existing = db.query(models.User).filter_by(username=username).first()
        if existing:
            continue
        if personnel_code:
            get_or_create_profile(db, personnel_code)
        user = models.User(
            username=username,
            hashed_password=hash_password(password),
            role=role,
            personnel_code=personnel_code,
        )
        db.add(user)
    db.commit()

    print("Running an initial batch risk assessment so dashboards have data...")
    from app.routers.risk import run_assessment_for
    from fastapi import HTTPException

    codes = [p.personnel_code for p in db.query(models.PersonnelProfile).all()]
    ran, skipped = 0, 0
    for code in codes:
        try:
            run_assessment_for(db, code)
            ran += 1
        except HTTPException:
            skipped += 1
    print(f"Batch assessment complete: {ran} scored, {skipped} skipped.")

    db.close()
    print("\nSeed complete. Demo credentials:")
    for username, password, role, _ in DEMO_ACCOUNTS:
        print(f"  {role.value:<18} username={username:<12} password={password}")


if __name__ == "__main__":
    seed()
