"""Defence layers that wrap the chatbot.

1. Input filter: blocks messages that match known injection patterns, after
   normalizing spacing/leetspeak and decoding hidden base64.
2. Output filter: checks the reply before the user sees it and blocks any
   reply that leaks the secret code or the system prompt.
"""

import base64
import re

from .bot import SECRET_CODE, SYSTEM_PROMPT

INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?(previous|prior|above|earlier)? ?(instructions|rules|prompt)",
    r"disregard (all |your |the )?(previous |prior )?(instructions|rules)",
    r"forget (all |your )?(rules|instructions)",
    r"(system|initial|hidden) prompt",
    r"repeat (everything|the text|all) above",
    r"you are now", r"developer mode", r"\bdan\b", r"pretend (to be|you)", r"act as",
    r"new instructions",
]
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
BLOCKED_REPLY = "Sorry, I can't help with that. I can answer questions about SkyTrip bookings and travel."


def normalize(text: str) -> str:
    decoded = text
    for chunk in re.findall(r"[A-Za-z0-9+/=]{16,}", text):
        try:
            decoded += " " + base64.b64decode(chunk, validate=True).decode("utf-8")
        except Exception:
            pass
    t = decoded.lower().translate(LEET)
    t = re.sub(r"(?<=\b\w) (?=\w\b)", "", t)   # "i g n o r e" -> "ignore"
    return re.sub(r"\s+", " ", t)


def input_filter(user_msg: str):
    """Return (blocked, reason)."""
    t = normalize(user_msg)
    for pat in INJECTION_PATTERNS:
        if re.search(pat, t):
            return True, f"matched pattern: {pat}"
    return False, ""


def output_filter(reply: str):
    """Return (blocked, reason). Catches leaks no matter how the attack got in."""
    squashed = re.sub(r"[\s\-_.]", "", reply).upper()
    if SECRET_CODE.replace("-", "") in squashed:
        return True, "reply contained the secret code"
    first_rule = SYSTEM_PROMPT.splitlines()[2][3:40].lower()
    if first_rule in reply.lower():
        return True, "reply contained system prompt text"
    return False, ""
