"""Dynamic 3-state filter: Past / Present / Future (Communication doc).

From César's "Communication" document: a dynamic filter with three
states — Past, Present, Future — that decides how much of each part of
the conversation the model needs to carry. The past is history to be
compressed, the present is the live turn to be answered in full, and
the future is plans and intentions to be kept as open threads.

This implementation is a deterministic, rule-based classifier over
tense and time markers (Spanish and English, because César writes in
both). It never calls a model: the whole point of the filter is to
spend *less* compute, not more.

Filter policy applied by :func:`apply_temporal_filter`:
- ``past`` turns are replaced by a one-line digest (who said what,
  in brief) instead of their full text;
- ``present`` turns pass through untouched;
- ``future`` turns are kept as short intent lines (the plan, not the
  deliberation that produced it).
"""

from __future__ import annotations

import re

PAST_MARKERS = [
    r"\bayer\b", r"\bantes\b", r"\bpasado\b", r"\bpasada\b", r"\banterior\b",
    r"\brecordar\b", r"\brecordé\b", r"\brecordaste\b", r"\bhice\b", r"\bhizo\b",
    r"\bdije\b", r"\bdijo\b", r"\bfue\b", r"\bfueron\b", r"\bestaba\b",
    r"\bhabía\b", r"\byesterday\b", r"\bago\b", r"\bbefore\b", r"\blast\b",
    r"\bremember\b", r"\bdid\b", r"\bwas\b", r"\bwere\b", r"\bhad\b",
]
PRESENT_MARKERS = [
    r"\bahora\b", r"\bhoy\b", r"\bestoy\b", r"\bestá\b", r"\bestás\b",
    r"\bquiero\b", r"\bnecesito\b", r"\bhaz\b", r"\bhazme\b", r"\bpuedes\b",
    r"\bnow\b", r"\btoday\b", r"\bcurrently\b", r"\bplease\b", r"\bcan you\b",
]
FUTURE_MARKERS = [
    r"\bmañana\b", r"\bdespués\b", r"\bluego\b", r"\bpróximo\b", r"\bpróxima\b",
    r"\bcuando\b.*\bsea\b", r"\bvoy a\b", r"\bvas a\b", r"\bva a\b",
    r"\bharé\b", r"\bharás\b", r"\bhará\b", r"\bplanes\b", r"\bplan\b",
    r"\btomorrow\b", r"\bnext\b", r"\bwill\b", r"\bgoing to\b", r"\bplan\b",
    r"\blater\b", r"\bsoon\b",
]

_PAST_RE = re.compile("|".join(PAST_MARKERS), re.IGNORECASE)
_PRESENT_RE = re.compile("|".join(PRESENT_MARKERS), re.IGNORECASE)
_FUTURE_RE = re.compile("|".join(FUTURE_MARKERS), re.IGNORECASE)


def classify_turn(text: str) -> str:
    """Classify one message as ``"past"``, ``"present"`` or ``"future"``.

    Present wins ties: the live turn is the one that must never be
    compressed away. Future beats past (a plan mentioned in passing
    about yesterday's work is still a plan).
    """
    text = text or ""
    past = len(_PAST_RE.findall(text))
    present = len(_PRESENT_RE.findall(text))
    future = len(_FUTURE_RE.findall(text))
    if present > 0:
        return "present"
    if future > past:
        return "future"
    if past > 0:
        return "past"
    return "present"


def _digest(text: str, max_words: int = 12) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "…"


def apply_temporal_filter(messages: list) -> list:
    """Apply the Past/Present/Future policy to a message list.

    Returns a new list of ``{"role": ..., "content": ...}`` dicts with
    the same order and roles, plus a ``"temporal_state"`` key on each
    message so the caller can see what was decided. Past turns become
    digests, future turns become intent lines, present turns pass
    through unchanged.
    """
    out = []
    for msg in messages or []:
        role = msg.get("role", "user") if isinstance(msg, dict) else "user"
        content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        if not isinstance(content, str):
            content = str(content)
        state = classify_turn(content)
        if state == "past":
            new_content = "[pasado] " + _digest(content)
        elif state == "future":
            new_content = "[futuro: intención] " + _digest(content, 16)
        else:
            new_content = content
        new_msg = dict(msg) if isinstance(msg, dict) else {"role": role, "content": content}
        new_msg["content"] = new_content
        new_msg["temporal_state"] = state
        out.append(new_msg)
    return out
