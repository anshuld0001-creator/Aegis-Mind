"""
AI MITRA — scoring engine.

Every score is 0-100. For stress/fatigue, HIGHER = WORSE (a risk-style
scale). For sleep/energy/mood/focus, HIGHER = BETTER (a wellness-style
scale). The overall Wellness Score inverts stress/fatigue before
weighting them in, since both count against overall wellbeing.

Weights are declared as module-level constants so they're easy to move
into an admin-configurable settings table later without touching the
math itself.
"""

# Configurable weights (must sum to 1.0)
WELLNESS_WEIGHTS = {
    "sleep": 0.20,
    "energy": 0.20,
    "stress": 0.20,   # inverted (100 - stress) before weighting
    "mood": 0.15,
    "fatigue": 0.15,  # inverted (100 - fatigue) before weighting
    "focus": 0.10,
}

DEFAULT_SCORE = 50.0  # neutral midpoint used when a dimension has no data yet


def compute_wellness_score(scores: dict) -> float:
    total = 0.0
    for dim, weight in WELLNESS_WEIGHTS.items():
        val = scores.get(dim, DEFAULT_SCORE)
        if dim in ("stress", "fatigue"):
            val = 100 - val
        total += weight * val
    return round(total, 1)


def risk_band(score: float) -> str:
    """For stress/fatigue: higher score = worse standing."""
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Moderate"
    if score <= 80:
        return "High"
    return "Very High"


def wellness_band(score: float) -> str:
    """For sleep/energy/mood/focus: higher score = better standing."""
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Fair"
    if score <= 80:
        return "Good"
    return "Excellent"


def band_for(dimension: str, score: float) -> str:
    return risk_band(score) if dimension in ("stress", "fatigue") else wellness_band(score)


def summarize(scores: dict) -> dict:
    """
    scores: dict with keys among sleep, energy, stress, mood, fatigue, focus
    (any missing dimension defaults to the neutral midpoint).
    Returns the full result payload used by the API / UI.
    """
    filled = {dim: scores.get(dim, DEFAULT_SCORE) for dim in WELLNESS_WEIGHTS}
    wellness = compute_wellness_score(filled)
    return {
        "wellness_score": wellness,
        "sleep_score": filled["sleep"],
        "energy_score": filled["energy"],
        "stress_score": filled["stress"],
        "mood_score": filled["mood"],
        "fatigue_score": filled["fatigue"],
        "focus_score": filled["focus"],
        "stress_level": risk_band(filled["stress"]),
        "fatigue_level": risk_band(filled["fatigue"]),
        "sleep_level": wellness_band(filled["sleep"]),
        "energy_level": wellness_band(filled["energy"]),
        "mood_level": wellness_band(filled["mood"]),
        "focus_level": wellness_band(filled["focus"]),
    }


def headline_explanation(result: dict) -> str:
    """One sentence summarizing what stands out — never just a bare number."""
    dims = ["sleep", "energy", "stress", "mood", "fatigue", "focus"]
    worst_dim, worst_badness = None, -1
    for d in dims:
        score = result[f"{d}_score"]
        badness = score if d in ("stress", "fatigue") else (100 - score)
        if badness > worst_badness:
            worst_badness, worst_dim = badness, d

    w = result["wellness_score"]
    if w >= 75:
        overall = "Your overall wellness indicators look strong right now."
    elif w >= 55:
        overall = "Your overall wellness indicators look fairly stable."
    elif w >= 35:
        overall = "Your overall wellness indicators suggest you could use some recovery."
    else:
        overall = "Your overall wellness indicators are notably low right now — please be gentle with yourself."

    focus_note = {
        "sleep": "your sleep quality looks like the area most worth attention",
        "energy": "your energy levels stand out as the area most worth attention",
        "stress": "your stress level is somewhat elevated",
        "mood": "your mood indicators stand out as worth a closer look",
        "fatigue": "your fatigue level is somewhat elevated",
        "focus": "your concentration indicators stand out as worth a closer look",
    }[worst_dim]

    if worst_badness >= 40:
        return f"{overall} In particular, {focus_note}."
    return overall


# ---------------------------------------------------------------------------
# Heart rate (camera/PPG self-measurement) — reference bands only.
#
# These are generic, widely-published *resting* heart-rate reference ranges
# for adults, shown purely for the user's own context. This is explicitly
# NOT a diagnostic classification: a reading outside these bands can be
# completely normal (e.g. right after activity, for athletes, for many
# individual baselines) and a reading inside them is not a clean bill of
# health. The wording below is written to reflect that.
# ---------------------------------------------------------------------------
def heart_rate_band(bpm: float) -> tuple[str, str]:
    """Returns (band_label, contextual_note) — never a diagnostic claim."""
    if bpm < 50:
        return "Low", (
            "This is below the typical resting range for most adults (60-100 bpm). "
            "This can be normal for well-rested or highly active individuals, but if "
            "it feels unusual for you, consider checking in with a healthcare professional."
        )
    if bpm <= 100:
        return "Typical resting range", (
            "This falls within the commonly cited resting range for adults (60-100 bpm)."
        )
    if bpm <= 120:
        return "Elevated", (
            "This is above the typical resting range. This is common after activity, "
            "caffeine, or stress, and isn't a diagnosis on its own."
        )
    return "High", (
        "This is notably above the typical resting range for adults. If this wasn't "
        "measured right after physical activity and repeats, consider speaking with a "
        "healthcare professional."
    )
