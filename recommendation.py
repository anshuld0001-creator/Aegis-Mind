"""
Welfare Recommendation Engine

Produces a NON-PUNITIVE suggested next action based on risk level and
contributing factors. This is advisory only — every recommendation is
routed to a human welfare officer for review and final decision
(see WelfareCase workflow). The engine never issues disciplinary actions.
"""

RECOMMENDATIONS = {
    "Low": "Routine wellness check-in; no action required.",
    "Moderate": "Recommend voluntary wellness check-in and workload review.",
    "High": "Recommend welfare officer review, rest/recovery period, and "
            "counselling/support resource referral.",
    "Critical": "Immediate welfare review recommended; refer to counselling/"
                "support resources; schedule close follow-up.",
}


def recommend(risk_level: str, top_factors: list, is_anomaly: bool = False) -> str:
    base = RECOMMENDATIONS.get(risk_level, RECOMMENDATIONS["Moderate"])
    if is_anomaly:
        base += " Anomaly detected relative to historical pattern — flag for closer review."
    return base


def default_priority(risk_level: str) -> int:
    """1 = highest priority ... 5 = lowest, used for the Risk Priority Board."""
    return {"Critical": 1, "High": 2, "Moderate": 3, "Low": 5}.get(risk_level, 4)
