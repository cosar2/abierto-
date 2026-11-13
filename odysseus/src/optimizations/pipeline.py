"""Pipeline: apply César's optimizations to outgoing LLM messages.

This is the single entry point wired into ``src/llm_core.py``
(``llm_call_async`` and ``_stream_llm_inner``). It is deliberately
boring: when the master switch is off — the default — it returns the
messages untouched. When on, it runs the enabled stages in order:

1. Temporal filter (Past / Present / Future) — past turns become
   digests, future turns become intent lines, present turns pass.
2. Probability cache — record the turn's prompt prefix for the
   session's settled code (lookup happens in the caller, not here;
   this stage only records, so a cache can never change a reply).
3. Semantic compression — encode the *latest user turn* with the
   session codebook and attach the payload as metadata. The full
   text is always kept alongside the payload, so decoding is
   optional and nothing is lost.
4. ERL erosion/reconstruction — applied to the numeric sketch of
   the latest turn (word-length vector), kept as metadata.
5. Locks — flag violations in the outgoing text (never rewrite it).
6. Integration filters — reality + non-repetition report on the
   outgoing text.

The function returns ``(messages, report)``. ``messages`` are the
(possibly annotated) messages to send; ``report`` says what each
stage did. Nothing here calls a model, touches the network, or
loads weights.
"""

from __future__ import annotations

from .cache import ProbabilityCache
from .compression import SessionCodebook, encode
from .config import OptimizationConfig
from .erl import apply_integration_filters, erl_cycle
from .locks import check_locks
from .seed import SeedCompiler, SessionMemory, UserSeed
from .temporal_filter import apply_temporal_filter


class OptimizationPipeline:
    """Holds the session-scoped state: cache, codebook, seed, memory."""

    def __init__(self, config: OptimizationConfig | None = None):
        self.config = config or OptimizationConfig()
        self.cache = ProbabilityCache(max_entries=self.config.probability_cache_size)
        self.codebook = SessionCodebook()
        self.compiler = SeedCompiler()
        self.memory = SessionMemory()
        self.history: list = []

    def apply(self, messages: list, *, session_id: str | None = None) -> tuple:
        """Apply the enabled stages to ``messages``.

        Always returns a ``(messages, report)`` tuple, even when
        everything is off (then ``messages`` is the input unchanged
        and the report says so).
        """
        config = self.config
        report = {"enabled": False, "stages": {}}
        if not config.any_enabled():
            return list(messages or []), report
        report["enabled"] = True
        working = [dict(m) if isinstance(m, dict) else {"role": "user", "content": str(m)} for m in (messages or [])]

        # Seed + session memory: crystallize once per session.
        if config.seed_enabled and config.seed_path:
            try:
                seed = UserSeed.load(config.seed_path)
                if not self.memory.is_crystallized:
                    compiled = self.compiler.compile(seed, _last_user_text(working))
                    self.memory.crystallize(compiled, seed)
                    report["stages"]["seed"] = {"active_points": compiled["active_points"]}
            except Exception:
                report["stages"]["seed"] = {"error": "seed file unreadable; skipped"}

        # 1. Temporal filter.
        if config.temporal_filter:
            working = apply_temporal_filter(working)
            report["stages"]["temporal_filter"] = {
                "states": [m.get("temporal_state", "?") for m in working]
            }

        # 2. Probability cache: record the latest user turn.
        if config.probability_cache:
            last_user = _last_user_text(working)
            if last_user:
                self.cache.record(last_user[:120], last_user)
                report["stages"]["probability_cache"] = self.cache.stats()

        # 3. Semantic compression: learn + encode the latest user turn.
        if config.semantic_compression:
            last_user = _last_user_text(working)
            if last_user:
                self.codebook.learn(last_user)
                payload = encode(last_user, self.codebook)
                report["stages"]["semantic_compression"] = {"ratio": payload["ratio"]}
                if working:
                    working[-1] = dict(working[-1])
                    working[-1]["semantic_payload"] = payload

        # 4. ERL: erode + reconstruct the numeric sketch of the turn.
        if config.erl_enabled:
            last_user = _last_user_text(working)
            if last_user:
                sketch = [float(len(word)) for word in last_user.split()[:32]] or [0.0]
                context = [float(len(word)) for word in " ".join(
                    m.get("content", "") for m in working[:-1]
                ).split()[:32]] or [0.0]
                cycle = erl_cycle(sketch, context, bits=config.erl_quantization_bits)
                report["stages"]["erl"] = {"bits": cycle["bits"], "mold_len": len(cycle["mold"])}

        # 5. Locks + 6. integration filters: report only, never rewrite.
        if config.anti_humanization_lock or config.anti_dehumanization_lock:
            text = " ".join(str(m.get("content", "")) for m in working)
            violations = check_locks(
                text,
                anti_humanization=config.anti_humanization_lock,
                anti_dehumanization=config.anti_dehumanization_lock,
            )
            report["stages"]["locks"] = {"violations": violations}
        if config.integration_filters:
            last_user = _last_user_text(working)
            report["stages"]["integration_filters"] = apply_integration_filters(
                last_user, self.history
            )
        self.history.extend(m.get("content", "") for m in working if m.get("role") == "user")
        return working, report


def _last_user_text(messages: list) -> str:
    for msg in reversed(messages or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else str(content)
    return ""


# Module-level default pipeline used by the llm_core hook. The hook
# reads the config from the environment on every call so toggling env
# vars takes effect without a restart; the pipeline state (cache,
# codebook, memory) is kept per process, which matches the doc's
# "common code settled for the session".
_default_pipeline: OptimizationPipeline | None = None


def apply_outgoing_optimizations(messages: list, *, session_id: str | None = None) -> list:
    """Hook called from ``src/llm_core.py``. Returns messages to send.

    Safe by construction: with the default config (everything OFF) it
    returns the input list unchanged, and any internal error is
    swallowed so the model call path can never break because of it.
    """
    global _default_pipeline
    try:
        if _default_pipeline is None:
            _default_pipeline = OptimizationPipeline(OptimizationConfig.from_env())
        else:
            _default_pipeline.config = OptimizationConfig.from_env()
        out, _report = _default_pipeline.apply(messages, session_id=session_id)
        return out
    except Exception:
        return list(messages or [])
