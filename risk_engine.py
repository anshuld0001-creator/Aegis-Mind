"""
Aegis Risk Engine

Combines the stress/burnout classifier, Isolation Forest anomaly detector,
and a SHAP explainer into a single transparent welfare risk assessment.

This module NEVER outputs a mental-illness diagnosis or a lie-detection
signal. It outputs a risk score + confidence + explanation only, intended
to route cases to a human welfare officer for review.
"""
import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from app.config import settings

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "ml_models_link"
# Resolve the real ml/models directory relative to the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REAL_MODEL_DIR = REPO_ROOT / "ml" / "models"


class RiskEngine:
    def __init__(self):
        self.loaded = False
        self.clf = None
        self.iso = None
        self.scaler = None
        self.explainer = None
        self.features = []
        self._try_load()

    def _try_load(self):
        try:
            self.clf = joblib.load(REAL_MODEL_DIR / "stress_risk_model.joblib")
            self.iso = joblib.load(REAL_MODEL_DIR / "anomaly_model.joblib")
            self.scaler = joblib.load(REAL_MODEL_DIR / "scaler.joblib")
            self.explainer = joblib.load(REAL_MODEL_DIR / "shap_explainer.joblib")
            with open(REAL_MODEL_DIR / "feature_list.json") as f:
                self.features = json.load(f)
            self.loaded = True
        except FileNotFoundError:
            self.loaded = False

    def is_ready(self) -> bool:
        return self.loaded

    def assess(self, feature_row: dict, previous_score: Optional[float] = None) -> dict:
        """
        feature_row: dict with keys matching self.features
        Returns a dict matching the RiskAssessmentOut shape (minus DB fields).
        """
        if not self.loaded:
            raise RuntimeError(
                "Risk models not found. Run `python ml/generate_synthetic_data.py` "
                "and `python ml/train_models.py` before starting the API."
            )

        x = pd.DataFrame([[feature_row.get(f, 0) for f in self.features]], columns=self.features)
        x_scaled = self.scaler.transform(x)

        proba = float(self.clf.predict_proba(x_scaled)[0, 1])
        risk_score = round(proba * 100, 1)
        confidence = round(0.55 + abs(proba - 0.5) * 0.9, 3)  # heuristic confidence, capped below
        confidence = min(confidence, 0.97)

        # Burnout / fatigue sub-scores (transparent, non-diagnostic heuristics
        # derived from the same inputs, separate from the classifier's raw output).
        fatigue_level = feature_row.get("fatigue_level", 3)
        sleep_quality = feature_row.get("sleep_quality", 3)
        workload = feature_row.get("perceived_workload", 3)
        duty_hours = feature_row.get("weekly_duty_hours", 50)

        burnout_risk = round(
            min(100, max(0,
                (fatigue_level / 5) * 45 + (1 - sleep_quality / 5) * 30 + (workload / 5) * 25
            )), 1
        )
        fatigue_risk = round(
            min(100, max(0,
                (fatigue_level / 5) * 55 + min(duty_hours / 96, 1) * 45
            )), 1
        )

        # Risk level via configurable thresholds
        if risk_score >= settings.RISK_THRESHOLD_CRITICAL:
            level = "Critical"
        elif risk_score >= settings.RISK_THRESHOLD_HIGH:
            level = "High"
        elif risk_score >= settings.RISK_THRESHOLD_MODERATE:
            level = "Moderate"
        else:
            level = "Low"

        # Trend
        if previous_score is None:
            trend = "Stable"
        elif risk_score - previous_score > 4:
            trend = "Increasing"
        elif previous_score - risk_score > 4:
            trend = "Decreasing"
        else:
            trend = "Stable"

        # Explainability (SHAP)
        shap_values = self.explainer.shap_values(x_scaled)
        sv = shap_values[0] if isinstance(shap_values, list) else shap_values[0]
        contributions = []
        for feat, val in zip(self.features, sv):
            contributions.append({
                "feature": feat,
                "impact": round(float(val), 4),
                "direction": "increases_risk" if val > 0 else "decreases_risk",
            })
        contributions.sort(key=lambda c: -abs(c["impact"]))
        top_factors = contributions[:5]

        # Anomaly detection
        anomaly_raw = self.iso.decision_function(x_scaled)[0]  # higher = more normal
        is_anomaly = bool(self.iso.predict(x_scaled)[0] == -1)
        anomaly_score = round(float(-anomaly_raw), 4)  # flip sign: higher = more anomalous

        return {
            "risk_score": risk_score,
            "confidence": confidence,
            "risk_level": level,
            "burnout_risk": burnout_risk,
            "fatigue_risk": fatigue_risk,
            "trend": trend,
            "contributing_factors": top_factors,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "model_version": "xgb-v1-synthetic",
        }


risk_engine = RiskEngine()
