"""Per-user predictive probability cache (Communication doc).

Idea from César's "Communication" document: the emitter and the
receiver "settle" a common high-speed code for the session. Frequent
continuations are stored as short codes instead of full text, so the
same idea costs fewer tokens to send. The cache is per user (each user
has their own local preference sub-indices) and lives only for the
session — nothing is written to disk by this class.

The doc's headline numbers (80% bandwidth, 70% memory, 250% speed)
are ESTIMATES from that document, not measured results. This class
makes no such claim; :meth:`ProbabilityCache.stats` reports only what
actually happened (hits, misses, entries).
"""

from __future__ import annotations

import time
from collections import OrderedDict


class ProbabilityCache:
    """Bounded per-user cache of prompt-prefix -> likely continuation.

    Keys are normalized prompt prefixes (lowercased, whitespace
    collapsed). Values are the continuations the user (or the pair of
    users in a session) has settled on. Lookup is exact-prefix: the
    cache only answers when the incoming prompt starts with a stored
    prefix, which keeps it deterministic and explainable.
    """

    def __init__(self, max_entries: int = 512):
        self.max_entries = max(1, int(max_entries))
        self._entries: "OrderedDict[str, dict]" = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join((text or "").strip().lower().split())

    def record(self, prompt_prefix: str, continuation: str, relevance: float = 1.0) -> None:
        """Store (or refresh) a prefix -> continuation pair.

        ``relevance`` is the 0..1 weight from the user's profile
        sub-indices; entries with higher relevance survive eviction
        longer because refresh bumps them to the most-recent position.
        """
        key = self._normalize(prompt_prefix)
        if not key or not continuation:
            return
        now = time.time()
        if key in self._entries:
            entry = self._entries.pop(key)
            entry["continuation"] = continuation
            entry["count"] += 1
            entry["relevance"] = max(entry["relevance"], float(relevance))
            entry["last_used"] = now
        else:
            entry = {
                "continuation": continuation,
                "count": 1,
                "relevance": float(relevance),
                "last_used": now,
            }
        self._entries[key] = entry
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def lookup(self, prompt: str) -> str | None:
        """Return the settled continuation for the longest matching prefix.

        Returns ``None`` on a miss. A hit moves the entry to the
        most-recent position (LRU), exactly like the doc's "the pair
        settles a common code and keeps using it".
        """
        text = self._normalize(prompt)
        if not text:
            self.misses += 1
            return None
        best_key = None
        for key in self._entries:
            if text.startswith(key) and (best_key is None or len(key) > len(best_key)):
                best_key = key
        if best_key is None:
            self.misses += 1
            return None
        entry = self._entries.pop(best_key)
        entry["count"] += 1
        entry["last_used"] = time.time()
        self._entries[best_key] = entry
        self.hits += 1
        return entry["continuation"]

    def stats(self) -> dict:
        """Only observed numbers — no estimated savings are claimed here."""
        return {
            "entries": len(self._entries),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
        }
