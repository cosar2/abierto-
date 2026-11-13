"""User seed + execution compiler + session-crystallizing memory.

From César's "La oportunidad de meta actualmente es una en un millón":
- The user holds an **individual seed**: small, portable, fits in a
  txt / on paper / on the phone. It holds the critical points, not
  the raw history. The cheap version is a file the user owns with
  ~20 critical points, each with a counter, a relevance % and a last
  activation.
- The company holds a **standard execution compiler**: identical for
  everyone, saves nothing, only executes.
- When seed + compiler meet, **memory crystallizes for that session
  and dissolves when the session ends**. The user has the seed, the
  company has the compiler. "Do not explain how it works" (keep the
  magic) — so this module exposes the mechanism but no marketing
  copy about it.

Design rules enforced here:
- The seed file is *portable JSON* the user owns; nothing in this
  module ever uploads it anywhere.
- Session memory lives only in RAM (:class:`SessionMemory`). There is
  no disk write for the crystallized memory, and :meth:`SessionMemory.dissolve`
  wipes it. The compiler (:class:`SeedCompiler`) holds no state at all.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field


@dataclass
class SeedPoint:
    """One critical point in the user's seed registry."""

    key: str
    note: str = ""
    counter: int = 0
    relevance: float = 0.5  # 0..1, the "relevance %" of the doc
    last_activation: float = 0.0  # epoch seconds; 0 = never

    def touch(self, relevance: float | None = None) -> None:
        self.counter += 1
        self.last_activation = time.time()
        if relevance is not None:
            self.relevance = max(0.0, min(1.0, float(relevance)))

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "note": self.note,
            "counter": self.counter,
            "relevance": self.relevance,
            "last_activation": self.last_activation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SeedPoint":
        return cls(
            key=str(data.get("key", "")),
            note=str(data.get("note", "")),
            counter=int(data.get("counter", 0)),
            relevance=float(data.get("relevance", 0.5)),
            last_activation=float(data.get("last_activation", 0.0)),
        )


@dataclass
class UserSeed:
    """The user's portable seed: at most ``max_points`` critical points."""

    points: list = field(default_factory=list)
    max_points: int = 20

    def add(self, key: str, note: str = "", relevance: float = 0.5) -> bool:
        """Add a point. Returns False when the registry is full."""
        if any(p.key == key for p in self.points):
            return True
        if len(self.points) >= self.max_points:
            return False
        self.points.append(
            SeedPoint(key=key, note=note, relevance=relevance)
        )
        return True

    def activate(self, key: str, relevance: float | None = None) -> bool:
        """Mark a point as used in this session (counter + timestamp)."""
        for point in self.points:
            if point.key == key:
                point.touch(relevance)
                return True
        return False

    def to_dict(self) -> dict:
        return {"max_points": self.max_points, "points": [p.to_dict() for p in self.points]}

    @classmethod
    def from_dict(cls, data: dict) -> "UserSeed":
        seed = cls(max_points=int(data.get("max_points", 20)))
        for raw in data.get("points", []) or []:
            seed.points.append(SeedPoint.from_dict(raw))
        return seed

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "UserSeed":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


class SeedCompiler:
    """The standard execution compiler: identical for everyone.

    It saves nothing and only executes. It holds no state, writes no
    files, and keeps no history. Given a seed and the current turn, it
    produces the working context for the session (the "crystallized"
    memory) without ever persisting it.
    """

    def compile(self, seed: UserSeed, turn_text: str) -> dict:
        """Build the session working context from seed + current turn."""
        active = [
            p for p in seed.points if p.key.lower() in (turn_text or "").lower()
        ]
        for point in active:
            point.touch()
        return {
            "active_points": [p.key for p in active],
            "point_count": len(seed.points),
            "compiled_at": time.time(),
        }


class SessionMemory:
    """Memory that crystallizes when seed and compiler meet, and
    dissolves when the session ends. RAM only, by design."""

    def __init__(self):
        self._crystallized: dict | None = None
        self.entries: list = []

    def crystallize(self, compiled: dict, seed: UserSeed) -> None:
        """Freeze the session working memory from seed + compiler output."""
        self._crystallized = {
            "active_points": list(compiled.get("active_points", [])),
            "point_count": compiled.get("point_count", len(seed.points)),
            "compiled_at": compiled.get("compiled_at", time.time()),
        }
        self.entries = []

    def add(self, role: str, content: str) -> None:
        if self._crystallized is None:
            return
        self.entries.append({"role": role, "content": content})

    def snapshot(self) -> dict | None:
        if self._crystallized is None:
            return None
        return {"crystallized": dict(self._crystallized), "entries": list(self.entries)}

    def dissolve(self) -> None:
        """End of session: the crystallized memory dissolves. Nothing remains."""
        self._crystallized = None
        self.entries = []

    @property
    def is_crystallized(self) -> bool:
        return self._crystallized is not None
