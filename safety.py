"""
AI MITRA — language detection + safety (crisis) detection.

Kept as its own module because safety detection is the one thing every
other part of the engine must defer to: if this fires, normal wellness
coaching stops and a supportive, resource-forward response takes over.
"""
import re

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

HINGLISH_MARKERS = {
    "hai", "hoon", "hun", "mujhe", "mujhy", "kaafi", "kafi", "bahut", "thak",
    "thaka", "thaki", "nahi", "nahin", "kyun", "kyu", "kya", "raha", "rahi",
    "rha", "rhi", "aaj", "kal", "acha", "accha", "theek", "thik", "neend",
    "so", "soya", "soyi", "kaam", "office", "padhai", "tension", "pareshan",
    "udaas", "khush", "gussa", "ghante", "ghanta",
}


def detect_language(text: str) -> str:
    """Very lightweight EN / HI / Hinglish detector — good enough to pick a
    natural reply register, not a linguistic ground truth."""
    if not text:
        return "en"
    if DEVANAGARI_RE.search(text):
        return "hi"
    words = set(re.findall(r"[a-zA-Z']+", text.lower()))
    if words & HINGLISH_MARKERS:
        return "hinglish"
    return "en"


# ---------------------------------------------------------------------------
# Safety / crisis detection.
#
# This list is intentionally at the "pattern" level (a handful of direct,
# unambiguous phrases in EN/HI/Hinglish) rather than an exhaustive slang
# dictionary. The goal is to reliably catch a clear expression of intent,
# not to build a comprehensive lexicon.
# ---------------------------------------------------------------------------
_SAFETY_PATTERNS = [
    r"\bsuicide\b", r"\bkill myself\b", r"\bend my life\b", r"\bwant to die\b",
    r"\bhurt myself\b", r"\bself[\s-]?harm\b", r"\bno reason to live\b",
    r"\bcan'?t go on\b", r"\bbetter off dead\b",
    r"khud ko khatam", r"jeena nahi chahta", r"jeena nahi chahti",
    r"marna chahta", r"marna chahti", r"khudkushi", r"aatmahatya",
    r"\u0906\u0924\u094d\u092e\u0939\u0924\u094d\u092f\u093e",  # आत्महत्या
]
_SAFETY_RE = re.compile("|".join(_SAFETY_PATTERNS), re.IGNORECASE)


def is_safety_concern(text: str) -> bool:
    if not text:
        return False
    return bool(_SAFETY_RE.search(text))


CRISIS_RESPONSE_EN = (
    "I'm really glad you told me this, and I want to make sure you're safe right now. "
    "I'm an AI, and this isn't something I can help with on my own — please reach out to "
    "a real person immediately: contact a trusted person near you, a mental health "
    "professional, or a crisis helpline in your area right now (in India: KIRAN helpline "
    "1800-599-0019, iCall 9152987821, or emergency number 112). You don't have to go "
    "through this alone. Would you like me to connect you with a human consultant on "
    "this platform as well?"
)

CRISIS_RESPONSE_HI = (
    "Aapne yeh mujhe bataya, iske liye shukriya. Main chahta hoon ki abhi is waqt aap "
    "surakshit rahein. Main ek AI hoon aur yeh cheez main akela handle nahi kar sakta — "
    "please turant kisi bharosemand insaan se baat karein: koi apna, ek mental health "
    "professional, ya apne area ki crisis helpline (India mein: KIRAN helpline "
    "1800-599-0019, iCall 9152987821, ya emergency number 112). Aap akele nahi hain. "
    "Kya aap chahenge ki main aapko is platform ke human consultant se bhi connect kar doon?"
)


def crisis_response(language: str) -> str:
    return CRISIS_RESPONSE_HI if language == "hi" else CRISIS_RESPONSE_EN
