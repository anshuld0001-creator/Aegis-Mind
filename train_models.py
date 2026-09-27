"""
AEGIS MIND - ML Training Pipeline

Data Collection -> Validation -> Feature Engineering -> Stress/Burnout Prediction
-> Anomaly Detection -> Explainability -> Model Monitoring artifacts

Trains on SYNTHETIC data only (see generate_synthetic_data.py). All reported
metrics are prototype/simulated results, not real-world performance claims.

Run: python train_models.py
Outputs (./models/):
  - stress_risk_model.joblib
  - anomaly_model.joblib
  - scaler.joblib
  - shap_explainer.joblib
  - feature_list.json
  - metrics.json
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR.parent / "data" / "synthetic_personnel_data.csv"
MODEL_DIR = BASE_DIR / "models"

FEATURES = [
    "weekly_duty_hours",
    "consecutive_duty_days",
    "leave_days_last_90",
    "night_shift_ratio",
    "deployment_months_last_year",
    "transfer_count_last_2yr",
    "training_load_hours",
    "stress_level",
    "mood",
    "sleep_quality",
    "fatigue_level",
    "perceived_workload",
]


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run generate_synthetic_data.py first."
        )
    df = pd.read_csv(DATA_PATH)
    # Basic validation
    df = df.dropna(subset=FEATURES + ["stress_label"])
    return df


def train():
    MODEL_DIR.mkdir(exist_ok=True)
    df = load_data()

    X = df[FEATURES].copy()
    y = df["stress_label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # --- Stress/Burnout risk classifier ---
    clf = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric="logloss",
        random_state=42,
    )
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    y_proba = clf.predict_proba(X_test_scaled)[:, 1]

    metrics = {
        "note": "PROTOTYPE / SIMULATED RESULTS on synthetic data. Not a real-world accuracy claim.",
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }

    # False positive / false negative breakdown
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    metrics["false_positive_rate"] = round(fp / (fp + tn), 4) if (fp + tn) else None
    metrics["false_negative_rate"] = round(fn / (fn + tp), 4) if (fn + tp) else None

    # Feature importance (model-level, complements SHAP per-prediction explanations)
    importances = clf.feature_importances_
    metrics["feature_importance"] = {
        f: round(float(i), 4) for f, i in sorted(
            zip(FEATURES, importances), key=lambda t: -t[1]
        )
    }

    # --- Anomaly detection (Isolation Forest) over organizational + wellness signals ---
    iso = IsolationForest(
        n_estimators=200, contamination=0.06, random_state=42
    )
    iso.fit(X_train_scaled)

    # --- SHAP explainer for per-case explainability ---
    explainer = shap.TreeExplainer(clf)

    # --- Persist artifacts ---
    joblib.dump(clf, MODEL_DIR / "stress_risk_model.joblib")
    joblib.dump(iso, MODEL_DIR / "anomaly_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    joblib.dump(explainer, MODEL_DIR / "shap_explainer.joblib")
    with open(MODEL_DIR / "feature_list.json", "w") as f:
        json.dump(FEATURES, f, indent=2)
    with open(MODEL_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("Training complete (SYNTHETIC DATA).")
    print(json.dumps({k: v for k, v in metrics.items() if k != "feature_importance"}, indent=2))
    return metrics


if __name__ == "__main__":
    train()
