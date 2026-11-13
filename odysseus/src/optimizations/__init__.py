"""César's optimization parameters, embedded in Odysseus.

Pure-stdlib package (no app dependencies) so it can be imported by
``src/llm_core.py`` without dragging in the whole app, and tested
without a model, network or weights.

Everything defaults to OFF — see :mod:`src.optimizations.config`.
"""

from .cache import ProbabilityCache
from .compression import SessionCodebook, decode, encode
from .config import DEFAULT_YT_KEYWORDS, OptimizationConfig
from .erl import apply_integration_filters, erl_cycle, erode, reconstruct
from .locks import check_locks
from .pipeline import OptimizationPipeline, apply_outgoing_optimizations
from .seed import SeedCompiler, SessionMemory, SeedPoint, UserSeed
from .temporal_filter import apply_temporal_filter, classify_turn
from .youtube_updates import admit_update, check_youtube_updates, feed_url, filter_entries, parse_feed

__all__ = [
    "DEFAULT_YT_KEYWORDS",
    "OptimizationConfig",
    "OptimizationPipeline",
    "ProbabilityCache",
    "SessionCodebook",
    "SeedCompiler",
    "SeedPoint",
    "SessionMemory",
    "UserSeed",
    "admit_update",
    "apply_integration_filters",
    "apply_outgoing_optimizations",
    "apply_temporal_filter",
    "check_locks",
    "check_youtube_updates",
    "classify_turn",
    "decode",
    "encode",
    "erl_cycle",
    "erode",
    "feed_url",
    "filter_entries",
    "parse_feed",
    "reconstruct",
]
