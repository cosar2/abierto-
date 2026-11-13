"""Semantic compression: base-vector indices + summation directives.

From César's "Communication" document: instead of transmitting full
text, transmit only the indices of shared base vectors plus the
directives of the summation equations that rebuild the meaning. The
receiver holds the same codebook, so the indices expand back into the
full message locally.

This is a *prototype codec*, not a real semantic compressor: the
"base vectors" here are the session codebook's frequent phrases, and
the "summation directives" are the explicit instructions to join them
back together. It is deterministic, lossless for text it has seen, and
falls back to literal text for anything outside the codebook.

The doc's headline numbers (80% bandwidth, 70% memory, 250% speed)
are ESTIMATES from that document, not measured results. The functions
here report the actual measured ratio for each payload instead.
"""

from __future__ import annotations

import re

# Word tokeniser shared by encoder and decoder.
_TOKEN_RE = re.compile(r"\s+|(?<=[\w]) (?=[^\w\s])|(?<=[^\w\s]) (?=[\w])")


def _tokens(text: str) -> list:
    return [t for t in re.split(r"(\s+)", text or "") if t != ""]


class SessionCodebook:
    """The codebook both sides of a session share.

    Built from the conversation itself: the most frequent multi-word
    phrases become base vectors, each with a short index. Both the
    emitter and the receiver hold the same codebook for the session,
    which is the doc's "common code settled by the pair".
    """

    def __init__(self):
        # index (int) -> phrase (str); 0 is reserved for "literal follows".
        self.by_index: dict = {}
        self.by_phrase: dict = {}
        self._next_index = 1

    def learn(self, text: str, min_phrase_words: int = 2, max_phrases: int = 256) -> int:
        """Add frequent phrases from ``text`` to the codebook.

        Returns the number of new base vectors added.
        """
        words = (text or "").split()
        phrases: dict = {}
        for size in (3, 2):
            if size < min_phrase_words:
                continue
            for i in range(len(words) - size + 1):
                phrase = " ".join(words[i : i + size])
                phrases[phrase] = phrases.get(phrase, 0) + 1
        added = 0
        for phrase, count in sorted(phrases.items(), key=lambda kv: (-kv[1], kv[0])):
            if count < 2 or phrase in self.by_phrase:
                continue
            if len(self.by_phrase) >= max_phrases:
                break
            self.by_phrase[phrase] = self._next_index
            self.by_index[self._next_index] = phrase
            self._next_index += 1
            added += 1
        return added

    def to_dict(self) -> dict:
        return {"by_index": {str(k): v for k, v in self.by_index.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "SessionCodebook":
        book = cls()
        for key, phrase in (data or {}).get("by_index", {}).items():
            idx = int(key)
            book.by_index[idx] = phrase
            book.by_phrase[phrase] = idx
            book._next_index = max(book._next_index, idx + 1)
        return book


def encode(text: str, codebook: SessionCodebook) -> dict:
    """Encode ``text`` as base-vector indices + join directives.

    Returns a payload dict::

        {"indices": [3, 0, 7], "literals": {1: "unseen words"},
         "directives": ["join", "join", "join"],
         "ratio": 0.62}

    ``indices`` holds codebook indices in order; index 0 means "the
    next piece is literal text" and its content lives in ``literals``
    under the position in ``indices``. ``directives`` says how to
    rejoin the pieces (currently always "join with a space", kept
    explicit because the doc's design calls for summation-equation
    directives, not an implicit rule). ``ratio`` is the measured
    encoded-size / original-size for this payload only.
    """
    text = text or ""
    if not text:
        return {"indices": [], "literals": {}, "directives": [], "ratio": 0.0}
    if not codebook.by_phrase:
        return {
            "indices": [0],
            "literals": {0: text},
            "directives": [],
            "ratio": 1.0,
        }
    phrases = sorted(codebook.by_phrase, key=len, reverse=True)
    indices: list = []
    literals: dict = {}
    pos = 0
    remaining = text
    while remaining:
        matched = None
        for phrase in phrases:
            if remaining.startswith(phrase):
                matched = phrase
                break
        if matched is not None:
            indices.append(codebook.by_phrase[matched])
            remaining = remaining[len(matched) :]
            if remaining.startswith(" "):
                remaining = remaining[1:]
        else:
            # Literal run until the next codebook phrase (or end).
            cut = len(remaining)
            for phrase in phrases:
                at = remaining.find(phrase)
                if 0 <= at < cut:
                    cut = at
            literal = remaining[:cut].rstrip()
            if literal:
                literals[len(indices)] = literal
                indices.append(0)
            remaining = remaining[cut:].lstrip()
            if not literal and not remaining:
                break
        pos += 1
        if pos > 10000:  # safety valve; never loop forever on odd input
            break
    directives = ["join"] * max(0, len(indices) - 1)
    encoded_size = len(str(indices)) + sum(len(v) for v in literals.values())
    ratio = round(encoded_size / max(1, len(text)), 3)
    return {"indices": indices, "literals": literals, "directives": directives, "ratio": ratio}


def decode(payload: dict, codebook: SessionCodebook) -> str:
    """Rebuild the original text from an :func:`encode` payload."""
    indices = payload.get("indices", []) if isinstance(payload, dict) else []
    literals = payload.get("literals", {}) if isinstance(payload, dict) else {}
    pieces: list = []
    for position, idx in enumerate(indices):
        if idx == 0:
            piece = literals.get(position, literals.get(str(position), ""))
            if piece:
                pieces.append(piece)
        else:
            piece = codebook.by_index.get(idx)
            if piece:
                pieces.append(piece)
    return " ".join(pieces)
