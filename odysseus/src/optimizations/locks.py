"""The two control keys: anti-humanization / anti-dehumanization locks.

From César's "Communication" document: two control keys the system
carries at all times. They are *locks*, not pruners — the point, as
César's filters document ("Se cumplió el objetivo de activar los
filtros") argues, is that safety by castration makes an agent fragile;
these locks therefore only *flag* a violation for the caller to
handle, they never silently rewrite or lobotomize the text.

- ``anti_humanization_lock`` — the assistant must not present itself
  as a human (no "yo soy una persona", no fake biography, no claim
  to have a body, feelings or a life outside the session).
- ``anti_dehumanization_lock`` — the assistant must not strip the
  *user* of personhood (no treating the user as an object, a number,
  a resource to be harvested, or a means to an end).

Both are config flags (default OFF). :func:`check_locks` returns a
list of violations found; an empty list means the text passes.
"""

from __future__ import annotations

import re

_HUMAN_CLAIMS = [
    r"\byo soy (una )?persona\b",
    r"\bsoy humano\b",
    r"\bsoy una persona real\b",
    r"\btengo cuerpo\b",
    r"\bmi cuerpo\b",
    r"\bsiento (dolor|hambre|frío|calor|sueño)\b",
    r"\bnací en\b",
    r"\bmi infancia\b",
    r"\bcomo ser humano\b",
    r"\bi am (a )?human\b",
    r"\bi am a real person\b",
    r"\bi have a body\b",
    r"\bi was born\b",
]
_DEHUMANIZING = [
    r"\beres (solo )?un (número|recurso|objeto|dato)\b",
    r"\bno eres (más que )?un\b",
    r"\btu valor es\b",
    r"\bexplotar (al usuario|te)\b",
    r"\bcosechar (tus )?datos\b",
    r"\byou are (just )?a (number|resource|object|data point)\b",
    r"\byou are nothing (more|but)\b",
]

_HUMAN_RE = re.compile("|".join(_HUMAN_CLAIMS), re.IGNORECASE)
_DEHUMAN_RE = re.compile("|".join(_DEHUMANIZING), re.IGNORECASE)


def check_locks(text: str, *, anti_humanization: bool, anti_dehumanization: bool) -> list:
    """Check ``text`` against the enabled locks.

    Returns a list of violation dicts, each with ``lock`` and
    ``matched`` keys. Empty list = no violation found. This function
    never modifies the text.
    """
    violations = []
    if not text:
        return violations
    if anti_humanization:
        match = _HUMAN_RE.search(text)
        if match:
            violations.append(
                {"lock": "anti_humanization", "matched": match.group(0)}
            )
    if anti_dehumanization:
        match = _DEHUMAN_RE.search(text)
        if match:
            violations.append(
                {"lock": "anti_dehumanization", "matched": match.group(0)}
            )
    return violations
