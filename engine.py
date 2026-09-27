"""
AI MITRA — adaptive conversation engine.

This is a transparent, deterministic dialogue manager (keyword/regex based),
not a call out to an external LLM — there is no AI provider configured for
this deployment, and this keeps AI Mitra fully functional offline at zero
per-message cost. The architecture (see `app/mitra/`) is split into
independent stages — safety, extraction, scoring, recommendations — so a
real LLM/vision provider can be dropped in behind this same interface later
(see `app/config.py: AI_PROVIDER_API_KEY`) without changing the API contract.

Persona: calm, empathetic, respectful, non-judgmental, concise, never
diagnostic. See `app/mitra/safety.py` for the one behavior that always
overrides everything else here.
"""
from app.mitra import extraction, safety, scoring, recommendations

WELCOME_EN = (
    "Hello, I'm AI Mitra — your wellness companion. I can help you check your "
    "stress, fatigue, energy, sleep, mood and general wellness. You can type "
    "or speak, in English, Hindi, or Hinglish. How are you feeling today?"
)
WELCOME_HI = (
    "Namaste, main AI Mitra hoon — aapka wellness companion. Main aapke stress, "
    "fatigue, energy, sleep, mood aur overall wellness ko samajhne mein madad kar "
    "sakta hoon. Aap type ya bol sakte hain. Aaj aap kaisa feel kar rahe hain?"
)

_GREETING_WORDS = {"hi", "hello", "hey", "namaste", "namaskar", "hii", "helo"}

# Follow-up question bank, keyed by dimension. Each entry is
# (pending_type, question_en, question_hi)
_FOLLOWUPS = {
    "stress": ("stress_source",
        "I understand. Is this mainly coming from work, studies, relationships, "
        "health, or something else?",
        "Samajh sakta hoon. Yeh mainly kaam, padhai, relationships, health, ya kisi "
        "aur cheez ki wajah se hai?"),
    "sleep": ("sleep_interrupted",
        "Thanks for sharing. Was your sleep interrupted, or did you simply sleep "
        "for that long unbroken?",
        "Shukriya batane ke liye. Kya neend beech mein toot rahi thi, ya bas utni "
        "der so paaye?"),
    "fatigue": ("fatigue_type",
        "Got it. Does that tiredness feel more physical or more mental?",
        "Samajh gaya. Yeh thakaan zyada physical hai ya mental?"),
    "energy": ("energy_time",
        "When is your energy lowest — mornings, afternoons, or by evening?",
        "Energy sabse kam kab feel hoti hai — subah, dopahar, ya shaam ko?"),
    "focus": ("focus_cause",
        "What's mainly pulling your focus away — workload, tiredness, or "
        "distractions around you?",
        "Focus mainly kis wajah se hat raha hai — kaam ka bojh, thakaan, ya "
        "aas-paas ki distractions?"),
    "mood": ("mood_context",
        "Thanks for telling me. Has anything in particular been weighing on you?",
        "Batane ke liye shukriya. Kya kuch particular cheez zehen mein chal rahi hai?"),
}


def _pick(lang, en, hi):
    return hi if lang == "hi" else en


def new_state() -> dict:
    return {"scores": {}, "pending": None, "turns": 0, "asked": []}


def handle_chat_message(state: dict, user_text: str) -> dict:
    """
    Free-form chat turn.
    Returns: {"reply": str, "state": dict, "safety_flag": bool, "language": str,
              "suggest_wellness_check": bool}
    """
    state = dict(state or new_state())
    state["turns"] = state.get("turns", 0) + 1
    lang = safety.detect_language(user_text)

    if safety.is_safety_concern(user_text):
        return {
            "reply": safety.crisis_response(lang),
            "state": state,
            "safety_flag": True,
            "language": lang,
            "suggest_wellness_check": False,
        }

    text_lower = (user_text or "").strip().lower()
    if state["turns"] == 1 and text_lower in _GREETING_WORDS:
        return {
            "reply": _pick(lang, WELCOME_EN, WELCOME_HI),
            "state": state,
            "safety_flag": False,
            "language": lang,
            "suggest_wellness_check": False,
        }

    scores = state.setdefault("scores", {})

    # If we're waiting on a specific follow-up answer, try to parse it first.
    pending = state.get("pending")
    if pending:
        dim, ptype = pending["dimension"], pending["type"]
        if ptype == "stress_source":
            state.setdefault("answers", {})["stress_source"] = extraction.classify_stress_source(user_text)
        elif ptype == "sleep_interrupted":
            yn = extraction.parse_yes_no(user_text)
            if yn is True and dim in scores:
                scores["sleep"] = max(5, scores["sleep"] - 15)
        elif ptype == "fatigue_type":
            state.setdefault("answers", {})["fatigue_type"] = "mental" if "mental" in text_lower else "physical"
        state["pending"] = None

    # Extract any fresh signals from this message.
    new_signals = extraction.extract_signals(user_text)
    for dim, sig in new_signals.items():
        if sig["direction"] == "score":
            scores[dim] = sig["value"]
        elif sig["direction"] == "high":
            scores[dim] = sig["value"]
        elif sig["direction"] == "low":
            scores[dim] = sig["value"]

    # Decide what to say next.
    unasked_dims = [d for d in new_signals if d not in state.get("asked", [])]
    if unasked_dims:
        dim = unasked_dims[0]
        state.setdefault("asked", []).append(dim)
        if dim in _FOLLOWUPS:
            ptype, q_en, q_hi = _FOLLOWUPS[dim]
            state["pending"] = {"dimension": dim, "type": ptype}
            reply = _pick(lang, q_en, q_hi)
        else:
            reply = _pick(
                lang,
                "Thanks for sharing that. Anything else on your mind today?",
                "Batane ke liye shukriya. Aaj aur kuch zehen mein hai?",
            )
        return {
            "reply": reply,
            "state": state,
            "safety_flag": False,
            "language": lang,
            "suggest_wellness_check": len(scores) >= 2,
        }

    if not new_signals and not pending:
        reply = _pick(
            lang,
            "I'm listening. You can tell me how your sleep, energy, stress, mood "
            "or focus has been — or say \"start wellness check\" for a fuller picture.",
            "Main sun raha hoon. Aap apni neend, energy, stress, mood ya focus ke "
            "baare mein bata sakte hain — ya \"start wellness check\" bol kar poora "
            "check bhi kar sakte hain.",
        )
        return {
            "reply": reply, "state": state, "safety_flag": False,
            "language": lang, "suggest_wellness_check": False,
        }

    reply = _pick(
        lang,
        "Thanks for telling me. Would you like a quick full wellness check, or "
        "keep talking?",
        "Batane ke liye shukriya. Kya aap ek quick wellness check karna chahenge, "
        "ya baat jaari rakhein?",
    )
    return {
        "reply": reply, "state": state, "safety_flag": False,
        "language": lang, "suggest_wellness_check": True,
    }


# ---------------------------------------------------------------------------
# Structured "Start Wellness Check" flow
# ---------------------------------------------------------------------------
_CHECK_STEPS = [
    ("sleep", "How many hours did you sleep last night, and was it broken or unbroken sleep?",
     "Kal raat kitne ghante soye, aur neend toot-toot kar aayi ya achi tarah?"),
    ("energy", "How would you describe your energy today — low, okay, or high?",
     "Aaj apni energy ko kaise describe karenge — low, theek-thaak, ya high?"),
    ("stress", "How stressed do you feel right now, and what's mainly behind it — "
     "work, studies, relationships, health, or something else?",
     "Abhi kitna stress feel ho raha hai, aur mainly kis wajah se — kaam, padhai, "
     "relationships, health, ya kuch aur?"),
    ("mood", "How has your mood been today?",
     "Aaj mood kaisa raha?"),
    ("focus", "How is your ability to focus or concentrate today?",
     "Aaj focus ya concentration kaisa raha?"),
    ("fatigue", "Lastly, how physically or mentally tired do you feel right now?",
     "Aakhri sawaal — abhi physically ya mentally kitna thaka hua feel kar rahe hain?"),
]


def start_wellness_check(language: str = "en") -> dict:
    state = {"step": 0, "answers": {}, "scores": {}}
    dim, q_en, q_hi = _CHECK_STEPS[0]
    intro = _pick(
        language,
        "Let's do a quick wellness check. There are no right or wrong answers.",
        "Chaliye ek quick wellness check karte hain. Koi sahi ya galat jawab nahi hota.",
    )
    question = _pick(language, q_en, q_hi)
    return {"reply": f"{intro} {question}", "state": state, "done": False, "result": None}


def continue_wellness_check(state: dict, user_text: str) -> dict:
    lang = safety.detect_language(user_text)

    if safety.is_safety_concern(user_text):
        return {"reply": safety.crisis_response(lang), "state": state, "done": False,
                "result": None, "safety_flag": True}

    step = state.get("step", 0)
    dim = _CHECK_STEPS[step][0]
    scores = state.setdefault("scores", {})
    state.setdefault("answers", {})[dim] = user_text

    signals = extraction.extract_signals(user_text)
    if dim in signals:
        sig = signals[dim]
        scores[dim] = sig["value"]
    elif dim == "sleep":
        hours = extraction.extract_sleep_hours(user_text)
        if hours is not None:
            scores["sleep"] = signals.get("sleep", {}).get("value", 50)

    if dim == "stress":
        source = extraction.classify_stress_source(user_text)
        if source:
            state["answers"]["stress_source"] = source

    step += 1
    state["step"] = step

    if step >= len(_CHECK_STEPS):
        result = scoring.summarize(scores)
        result["headline"] = scoring.headline_explanation(result)
        result["recommendations"] = recommendations.recommendations_for(result)
        closing = _pick(
            lang,
            "Thanks. I've completed your wellness check.",
            "Shukriya. Aapka wellness check complete ho gaya hai.",
        )
        return {"reply": closing, "state": state, "done": True, "result": result, "safety_flag": False}

    next_dim, q_en, q_hi = _CHECK_STEPS[step]
    question = _pick(lang, q_en, q_hi)
    ack = _pick(lang, "Thanks.", "Shukriya.")
    return {"reply": f"{ack} {question}", "state": state, "done": False, "result": None, "safety_flag": False}
