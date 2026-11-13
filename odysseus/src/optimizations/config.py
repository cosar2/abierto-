"""Configuration for César's optimization parameters (Odysseus mods).

Everything defaults to OFF, following César's "plan configurator" idea
from "La oportunidad de meta": every option off by default, the user
toggles boxes and watches the price move. Nothing in this package does
anything unless its flag is explicitly turned on.

Configuration is read from environment variables (``OPT_*`` prefix) so
the module works without the app's settings machinery, but every value
can also be passed explicitly to :class:`OptimizationConfig` (used by
the tests and by the wiring in ``src/llm_core.py``).

Sources (see ``README.md`` in this package for the full mapping):
- "Communication" — probability cache, semantic compression, Past /
  Present / Future filter, anti-humanization / anti-dehumanization locks.
- "La oportunidad de meta actualmente es una en un millón" — user seed,
  execution compiler, session-crystallizing memory, ERL, filters.
- "Propuesta de Implementación: IA de Baja Fidelidad y Reconstrucción
  Lógica" — ERL implementation (erosion by successive quantization,
  reconstruction by contextual evolution).
- "Protocolo de Eficiencia Sistémica y Gestión de Residuos Monumentales"
  — design doctrine: dense logic beats brute force.
- "Se cumplió el objetivo de activar los filtros" — locks philosophy:
  pruning capabilities makes an agent fragile, not safer.

No model weights, no network calls and no inference happen in this
package. The numbers in César's documents (80% bandwidth, 70% memory,
250% speed) are ESTIMATES from his documents, never measured results;
they are repeated here only as his stated estimates.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_list(name: str, default: list) -> list:
    raw = os.environ.get(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Default keywords used to spot notebook / update videos on the channel.
# Spanish + English, because César publishes in both.
DEFAULT_YT_KEYWORDS = [
    "notebook",
    "actualización",
    "actualizacion",
    "update",
    "nuevo",
    "nueva",
    "repositorio",
    "repository",
    "release",
    "versión",
    "version",
    "comunicación",
    "communication",
    "activo",
    "chakra",
    "circo",
    "feria",
]


@dataclass
class OptimizationConfig:
    """All of César's optimization parameters. Every flag defaults to OFF."""

    # Master switch. When False, the whole pipeline is a no-op.
    enabled: bool = False

    # --- Communication doc ---
    # Per-user predictive probability cache: the emitter and the receiver
    # "settle" a common high-speed code for the session, so frequent
    # continuations are sent as short codes instead of full text.
    probability_cache: bool = False
    probability_cache_size: int = 512
    # Semantic compression: transmit base-vector indices + summation-
    # equation directives instead of full text.
    semantic_compression: bool = False
    # Dynamic 3-state filter: Past / Present / Future.
    temporal_filter: bool = False
    # The two control keys from the Communication doc.
    anti_humanization_lock: bool = False
    anti_dehumanization_lock: bool = False

    # --- "La oportunidad de meta" doc ---
    # Individual user seed: a small portable registry (~20 critical
    # points, each with counter, relevance % and last activation).
    seed_enabled: bool = False
    seed_path: str = ""
    seed_max_points: int = 20
    # Execution compiler: standard, saves nothing, only executes.
    # (Implemented as: session memory lives only in RAM and dissolves.)
    session_memory: bool = False
    # ERL — Entropía por Erosión y Reconstrucción Lógica.
    erl_enabled: bool = False
    erl_quantization_bits: int = 2
    # Integration filters: (a) consistent reality (verifiable, traceable
    # source), (b) non-repetition (500-variation exception for helping a
    # human), (c) weighting by enabled utility.
    integration_filters: bool = False

    # --- YouTube notebook-update check ---
    # RULE (user, 2026-11-10): this check runs ONLY ONCE and ONLY at
    # install/update time. It is NOT a continuous or periodic review.
    # It admits ONLY updates from the OFFICIAL repositories published
    # on César's own YouTube channel (@energiaenergy). It must REJECT
    # any modified copy that is not present on that channel, because
    # the official channel repositories cannot be modified by third
    # parties and are therefore the trusted source.
    youtube_updates_enabled: bool = False
    youtube_channel_handle: str = "@energiaenergy"
    # Channel ID (UC...) — NOT resolved yet: the public channel page
    # and the handle→ID lookups available to this agent did not return
    # it. Fill it in from YouTube Studio → Settings → Channel →
    # Advanced settings, or channel page → …more → Share channel →
    # Copy channel ID. The RSS feed needs this ID; the handle alone
    # cannot build the feed URL.
    youtube_channel_id: str = ""
    youtube_keywords: list = field(default_factory=lambda: list(DEFAULT_YT_KEYWORDS))
    # Directory where the one-time-run marker is stored. Empty means
    # "do not persist a marker" (check runs only when explicitly
    # invoked with force=True, i.e. at install/update time).
    youtube_state_dir: str = ""

    @classmethod
    def from_env(cls) -> "OptimizationConfig":
        """Build a config from ``OPT_*`` environment variables."""
        return cls(
            enabled=_env_bool("OPT_ENABLED", False),
            probability_cache=_env_bool("OPT_PROBABILITY_CACHE", False),
            probability_cache_size=_env_int("OPT_PROBABILITY_CACHE_SIZE", 512),
            semantic_compression=_env_bool("OPT_SEMANTIC_COMPRESSION", False),
            temporal_filter=_env_bool("OPT_TEMPORAL_FILTER", False),
            anti_humanization_lock=_env_bool("OPT_ANTI_HUMANIZATION_LOCK", False),
            anti_dehumanization_lock=_env_bool("OPT_ANTI_DEHUMANIZATION_LOCK", False),
            seed_enabled=_env_bool("OPT_SEED", False),
            seed_path=_env_str("OPT_SEED_PATH", ""),
            seed_max_points=_env_int("OPT_SEED_MAX_POINTS", 20),
            session_memory=_env_bool("OPT_SESSION_MEMORY", False),
            erl_enabled=_env_bool("OPT_ERL", False),
            erl_quantization_bits=_env_int("OPT_ERL_BITS", 2),
            integration_filters=_env_bool("OPT_INTEGRATION_FILTERS", False),
            youtube_updates_enabled=_env_bool("OPT_YT_UPDATES", False),
            youtube_channel_handle=_env_str("OPT_YT_CHANNEL_HANDLE", "@energiaenergy"),
            youtube_channel_id=_env_str("OPT_YT_CHANNEL_ID", ""),
            youtube_keywords=_env_list("OPT_YT_KEYWORDS", DEFAULT_YT_KEYWORDS),
            youtube_state_dir=_env_str("OPT_YT_STATE_DIR", ""),
        )

    def any_enabled(self) -> bool:
        """True if the master switch is on and at least one feature is on."""
        if not self.enabled:
            return False
        return any(
            [
                self.probability_cache,
                self.semantic_compression,
                self.temporal_filter,
                self.anti_humanization_lock,
                self.anti_dehumanization_lock,
                self.seed_enabled,
                self.session_memory,
                self.erl_enabled,
                self.integration_filters,
            ]
        )
