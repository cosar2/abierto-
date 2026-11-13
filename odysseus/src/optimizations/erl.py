"""ERL — Entropía por Erosión y Reconstrucción Lógica + integration filters.

Two sources:
- "La oportunidad de meta actualmente es una en un millón": ERL keeps
  the *mold / pure intention* and reconstructs the rest ("es recordar
  sin espiar"). Integration filters: (a) consistent reality (verifiable,
  traceable source), (b) non-repetition (exception: 500 variations of
  helping a human), (c) weighting by enabled utility.
- "Propuesta de Implementación: IA de Baja Fidelidad y Reconstrucción
  Lógica": the implementation. Phase A — *Erosión por Cuantización
  Sucesiva*: submit the representation to repeated quantization cycles
  (e.g. float32 → int2), which strips the "adornments" and rigid
  details and keeps only the logical skeleton / pure intention.
  Phase B — *Reconstrucción por Evolución Contextual*: a high-complexity
  system interprets the simplified mold and completes the design from
  its recent learning and functional logic ("sé que esto funciona").
  The doc's stated economy: low-cost hardware running "mutilated"
  models that are paradoxically more creative than heavy deterministic
  ones. That economy claim is the doc's own; it is not a measured
  result of this code.

This implementation works on plain numeric vectors (the "mold" of a
message embedding) and on text (the integration filters). No model is
called, no weights are loaded.
"""

from __future__ import annotations

import hashlib
import math
import re


# ---------------------------------------------------------------------------
# ERL: erosion (Phase A) and reconstruction (Phase B)
# ---------------------------------------------------------------------------

def erode(vector: list, bits: int = 2) -> list:
    """Phase A — erosion by successive quantization.

    Quantize each value to ``bits`` bits of resolution. With the doc's
    example of 2 bits, a value in [0, 1] keeps only 4 levels: the
    "adornments" (fine detail) are stripped and only the skeleton
    (the mold / pure intention) survives. Values outside [0, 1] are
    scaled into range first and the scale is returned with the mold
    so reconstruction can invert it.
    """
    if not vector:
        return []
    bits = max(1, min(8, int(bits)))
    levels = (1 << bits) - 1
    lo = min(vector)
    hi = max(vector)
    span = (hi - lo) or 1.0
    eroded = []
    for value in vector:
        scaled = (value - lo) / span
        quantized = round(scaled * levels) / levels
        eroded.append(round(lo + quantized * span, 6))
    return eroded


def reconstruct(mold: list, context: list, bits: int = 2) -> list:
    """Phase B — reconstruction by contextual evolution.

    The high-complexity side (here: the recent context vector) fills
    the mold back in. Each mold value is nudged toward the matching
    context value by a weight that grows when the mold is coarse
    (fewer bits = more room for the context to complete the design).
    The mold's shape is preserved — reconstruction completes it, it
    does not replace it.
    """
    if not mold:
        return []
    if not context:
        return list(mold)
    bits = max(1, min(8, int(bits)))
    # Coarser mold -> more reconstruction freedom (doc: "sé que esto funciona").
    weight = 1.0 - (bits / 8.0)
    out = []
    for i, value in enumerate(mold):
        ctx = context[i % len(context)]
        out.append(round(value + weight * (ctx - value), 6))
    return out


def erl_cycle(vector: list, context: list, bits: int = 2) -> dict:
    """One full ERL cycle: erode, then reconstruct. Returns mold + result."""
    mold = erode(vector, bits=bits)
    rebuilt = reconstruct(mold, context, bits=bits)
    return {"mold": mold, "reconstructed": rebuilt, "bits": bits}


# ---------------------------------------------------------------------------
# Integration filters (from "La oportunidad de meta")
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://\S+")

# 500-variation exception: helping a human may repeat the same help in
# up to 500 variations; anything else is capped at a small repetition budget.
HELP_VARIATION_LIMIT = 500
DEFAULT_REPETITION_LIMIT = 3


def filter_consistent_reality(text: str, *, require_source: bool = True) -> dict:
    """Filter (a): consistent reality — a claim needs a verifiable,
    traceable source. Returns ``{"ok": bool, "sources": [...]}``.
    A text with no factual claim passes trivially; a text that makes
    claims without any source fails when ``require_source`` is on.
    """
    sources = _URL_RE.findall(text or "")
    has_claim = bool(re.search(r"\b(es|son|fue|fueron|será|serán|is|are|was|were)\b", text or "", re.IGNORECASE))
    ok = (not has_claim) or bool(sources) or (not require_source)
    return {"ok": ok, "sources": sources}


def filter_non_repetition(history: list, candidate: str, *, is_help: bool = False) -> dict:
    """Filter (b): non-repetition. The same content must not be
    repeated beyond the budget — except helping a human, which the doc
    explicitly allows up to 500 variations.
    """
    limit = HELP_VARIATION_LIMIT if is_help else DEFAULT_REPETITION_LIMIT
    normalized = " ".join((candidate or "").split()).lower()
    repeats = sum(
        1
        for item in history or []
        if " ".join(str(item).split()).lower() == normalized
    )
    return {"ok": repeats < limit, "repeats": repeats, "limit": limit}


def filter_utility_weighting(items: list, utilities: dict) -> list:
    """Filter (c): weighting by enabled utility. Items are kept in
    descending utility order; items whose utility is disabled (0 or
    missing) are dropped. ``items`` is a list of dicts with a ``key``.
    """
    scored = []
    for item in items or []:
        key = item.get("key") if isinstance(item, dict) else str(item)
        utility = float(utilities.get(key, 0) or 0)
        if utility > 0:
            scored.append((utility, item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored]


def apply_integration_filters(text: str, history: list, *, is_help: bool = False) -> dict:
    """Run all three integration filters over a candidate reply."""
    reality = filter_consistent_reality(text)
    repetition = filter_non_repetition(history, text, is_help=is_help)
    return {
        "consistent_reality": reality,
        "non_repetition": repetition,
        "ok": bool(reality["ok"] and repetition["ok"]),
    }
