"""
AI MITRA — personalized, non-medical recommendation engine.

Recommendations are selected per-dimension based on that dimension's
score, so two people with the same wellness score but different weak
spots get different advice.
"""

_SLEEP_LOW = [
    "Try to keep a consistent sleep and wake time, even on off days.",
    "Reduce screen exposure for 30-45 minutes before bed.",
    "Build a short, relaxing wind-down routine before sleep.",
]
_ENERGY_LOW = [
    "Take a short recovery break rather than pushing through.",
    "Hydrate — low fluid intake often shows up as low energy.",
    "A brief walk or stretch can help more than caffeine right now.",
]
_STRESS_HIGH = [
    "Try a short, slow-breathing exercise (4 seconds in, 6 seconds out).",
    "Break large tasks into smaller, clearly-defined steps.",
    "Identify the single most urgent task and start there — not everything at once.",
]
_MOOD_LOW = [
    "Doing one small, enjoyable thing today can help more than it seems.",
    "Consider talking to someone you trust about how you're feeling.",
    "Be a little extra patient with yourself today.",
]
_FATIGUE_HIGH = [
    "Build in short breaks every 60-90 minutes of focused work.",
    "Check whether today's sleep duration matched what your body needs.",
    "Avoid stacking your day with back-to-back commitments if you can.",
]
_FOCUS_LOW = [
    "Try short focused work sessions (25 minutes) with a clear single task.",
    "Reduce visible distractions — notifications, extra tabs, phone nearby.",
    "Tackle one task at a time rather than switching between several.",
]

_GOOD_GENERIC = [
    "Keep doing what's working — consistency is what compounds here.",
]


def recommendations_for(result: dict) -> list[str]:
    """
    result: output of scoring.summarize(...)
    Returns a de-duplicated, prioritized list of concrete suggestions —
    worst dimensions first, capped so it stays a short, usable checklist.
    """
    picks: list[str] = []

    ranked = sorted(
        ["sleep", "energy", "stress", "mood", "fatigue", "focus"],
        key=lambda d: (
            result[f"{d}_score"] if d in ("stress", "fatigue") else 100 - result[f"{d}_score"]
        ),
        reverse=True,
    )

    bank = {
        "sleep": (_SLEEP_LOW, result["sleep_score"] <= 60),
        "energy": (_ENERGY_LOW, result["energy_score"] <= 60),
        "stress": (_STRESS_HIGH, result["stress_score"] >= 40),
        "mood": (_MOOD_LOW, result["mood_score"] <= 60),
        "fatigue": (_FATIGUE_HIGH, result["fatigue_score"] >= 40),
        "focus": (_FOCUS_LOW, result["focus_score"] <= 60),
    }

    for dim in ranked:
        tips, trigger = bank[dim]
        if trigger:
            picks.extend(tips[:2])
        if len(picks) >= 5:
            break

    if not picks:
        picks = _GOOD_GENERIC

    # de-duplicate, keep order, cap at 5
    seen, final = set(), []
    for p in picks:
        if p not in seen:
            seen.add(p)
            final.append(p)
    return final[:5]
