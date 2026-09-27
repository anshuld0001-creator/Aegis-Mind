"""
AI MITRA — lightweight extraction of wellness signals from free text.

No external LLM is required for this: it's a transparent, deterministic
keyword/regex layer (English + Hindi + Hinglish) that turns what the user
says into 0-100 style signal contributions per dimension. This keeps the
whole engine explainable and able to run with zero external API cost.
"""
import re

# ---- severity words -> 0-100 "intensity" contribution ----
_INTENSITY_WORDS = [
    (95, [r"extremely", r"severely", r"bahut zyada", r"bohot zyada", r"bilkul"]),
    (80, [r"very", r"really", r"bahut", r"bohot", r"kaafi", r"kafi"]),
    (60, [r"quite", r"fairly", r"thoda zyada", r"kuch zyada"]),
    (40, [r"a bit", r"a little", r"thoda", r"thora", r"slightly"]),
    (20, [r"barely", r"not much", r"kam", r"nahi zyada"]),
]


def _intensity_multiplier(text: str) -> float:
    """Returns 0.5-1.15 scaling based on intensity qualifiers found in text."""
    t = text.lower()
    for score, patterns in _INTENSITY_WORDS:
        for p in patterns:
            if re.search(p, t):
                return 0.5 + (score / 100) * 0.65
    return 0.85  # neutral default


# ---- direction words per dimension (base 0-100 before intensity scaling) ----
# For stress/fatigue: higher = worse. For energy/mood/sleep_quality/focus: higher = better.

_STRESS_HIGH = [r"stress", r"stressed", r"overwhelm", r"pressure", r"tension", r"pareshan", r"anxious"]
_STRESS_LOW = [r"relaxed", r"calm", r"chill", r"aaram"]

_FATIGUE_HIGH = [r"tired", r"exhaust", r"fatigue", r"drained", r"thak", r"thaka", r"thaki", r"burn ?out"]
_FATIGUE_LOW = [r"fresh", r"energetic", r"active"]

_ENERGY_LOW = [r"low energy", r"no energy", r"energy.*(low|kam)", r"sust", r"lethargic"]
_ENERGY_HIGH = [r"high energy", r"energetic", r"active", r"energy.*(high|acha|good)"]

_MOOD_LOW = [r"sad", r"low mood", r"down", r"udaas", r"upset", r"irritable", r"irritated", r"gussa", r"angry"]
_MOOD_HIGH = [r"happy", r"good mood", r"khush", r"cheerful", r"motivated"]

_FOCUS_LOW = [r"can'?t focus", r"can'?t concentrate", r"distracted", r"forgetful",
              r"unfocused", r"dhyan nahi", r"hard to focus", r"difficult to focus",
              r"trouble focusing", r"trouble concentrating", r"low focus"]
_FOCUS_HIGH = [r"focused", r"productive", r"sharp", r"concentrat"]

_SLEEP_POOR = [r"couldn'?t sleep", r"bad sleep", r"disturbed sleep", r"interrupted sleep", r"neend nahi", r"insomnia"]
_SLEEP_GOOD = [r"slept well", r"good sleep", r"acchi neend", r"neend acchi"]

_HOURS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*(?:hours?|hrs?|ghante|ghanta|ghanta)", re.IGNORECASE)


def extract_sleep_hours(text: str):
    m = _HOURS_RE.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _match_any(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def extract_signals(text: str) -> dict:
    """
    Scan free text for dimension-relevant signals.
    Returns a dict of dimension -> {"direction": "high"|"low", "value": 0-100}
    for whichever dimensions were actually mentioned. Dimensions not
    mentioned are simply absent from the result.
    """
    signals = {}
    mult = _intensity_multiplier(text)

    def add(dim, direction, base):
        val = max(5, min(100, round(base * mult)))
        signals[dim] = {"direction": direction, "value": val}

    if _match_any(_STRESS_HIGH, text):
        add("stress", "high", 80)
    elif _match_any(_STRESS_LOW, text):
        add("stress", "low", 20)

    if _match_any(_FATIGUE_HIGH, text):
        add("fatigue", "high", 80)
    elif _match_any(_FATIGUE_LOW, text):
        add("fatigue", "low", 20)

    if _match_any(_ENERGY_LOW, text):
        add("energy", "low", 25)
    elif _match_any(_ENERGY_HIGH, text):
        add("energy", "high", 80)

    if _match_any(_MOOD_LOW, text):
        add("mood", "low", 30)
    elif _match_any(_MOOD_HIGH, text):
        add("mood", "high", 80)

    if _match_any(_FOCUS_LOW, text):
        add("focus", "low", 30)
    elif _match_any(_FOCUS_HIGH, text):
        add("focus", "high", 80)

    hours = extract_sleep_hours(text)
    if hours is not None:
        # 7-9h -> good; below/above tapers off
        if 7 <= hours <= 9:
            sleep_score = 85
        elif hours < 7:
            sleep_score = max(10, 85 - (7 - hours) * 18)
        else:
            sleep_score = max(40, 85 - (hours - 9) * 10)
        signals["sleep"] = {"direction": "score", "value": round(sleep_score)}
    elif _match_any(_SLEEP_POOR, text):
        add("sleep", "low", 30)
    elif _match_any(_SLEEP_GOOD, text):
        add("sleep", "high", 85)

    return signals


# ---- source-of-stress classification (for adaptive follow-up) ----
_STRESS_SOURCES = {
    "work": [r"work", r"job", r"office", r"boss", r"deadline", r"kaam"],
    "study": [r"study", r"studies", r"exam", r"college", r"school", r"padhai"],
    "relationship": [r"relationship", r"family", r"friend", r"partner", r"ghar"],
    "health": [r"health", r"sick", r"pain", r"tabiyat"],
}


def classify_stress_source(text: str):
    for source, patterns in _STRESS_SOURCES.items():
        if _match_any(patterns, text):
            return source
    return None


_YES_RE = re.compile(r"\b(yes|yeah|yep|haan|han|ha)\b", re.IGNORECASE)
_NO_RE = re.compile(r"\b(no|nahi|nahin|nope)\b", re.IGNORECASE)


def parse_yes_no(text: str):
    if _YES_RE.search(text):
        return True
    if _NO_RE.search(text):
        return False
    return None
