# Optimizations — César's parameters, embedded in Odysseus

This package (`src/optimizations/`) embeds César's optimization
parameters into PewDiePie's Odysseus workspace. It was built **without
executing any AI model and without downloading any model weights**:
Ajax (the fine-tuned Qwen3.5-9B model) is not released — its official
page says "coming soon" — so no Ajax weights are included here, and
nothing in this package can run a model. What is here is the
optimization layer that would sit around the model once it (or its
base, Qwen3.5-9B) is available.

## The one rule

**Everything defaults to OFF.** This follows César's "plan
configurator" idea from *"La oportunidad de meta"*: every option off
by default, the user toggles boxes. The wiring in `src/llm_core.py`
(`llm_call_async` and `_stream_llm_inner`) calls
`apply_outgoing_optimizations()` on every model call, but with the
default config that function returns the messages untouched. Turning
features on requires setting `OPT_*` environment variables (see
`config.py`). The hook is wrapped so an optimization error can never
break a model call.

## Parameters and where each comes from

### From "Communication" (Drive Doc)

| Parameter | Env flag | What it does |
|---|---|---|
| Per-user predictive probability cache | `OPT_PROBABILITY_CACHE=1` | Emitter and receiver "settle" a common high-speed code for the session. Frequent prompt prefixes map to settled continuations (`cache.py`). Per user, session-only, in RAM. |
| Semantic compression | `OPT_SEMANTIC_COMPRESSION=1` | Transmit base-vector indices + summation-equation directives instead of full text (`compression.py`). The session codebook is learned from the conversation; decode rebuilds the text. The payload always travels next to the full text, so nothing is lost. |
| Dynamic 3-state filter Past / Present / Future | `OPT_TEMPORAL_FILTER=1` | Past turns become one-line digests, future turns become intent lines, present turns pass untouched (`temporal_filter.py`). Rule-based (tense/time markers, ES+EN), no model call. |
| Anti-humanization lock | `OPT_ANTI_HUMANIZATION_LOCK=1` | Flags text where the assistant presents itself as human (`locks.py`). |
| Anti-dehumanization lock | `OPT_ANTI_DEHUMANIZATION_LOCK=1` | Flags text that strips the user of personhood (`locks.py`). |

**Estimates, not measurements.** The Communication doc's headline
numbers (80% bandwidth reduction, 70% memory saving, 250% speed) are
**ESTIMATES from that document, never measured results**. This code
does not repeat them as facts: `cache.stats()` and the compression
`ratio` report only what actually happened for a given payload. A
real benchmark (same conversation, with and without the pipeline) is
still required before any saving is promised.

### From "La oportunidad de meta actualmente es una en un millón"

| Parameter | Env flag | What it does |
|---|---|---|
| Individual user seed | `OPT_SEED=1`, `OPT_SEED_PATH=<file>` | Small portable registry the user owns: ~20 critical points, each with counter, relevance % and last activation (`seed.py`). JSON file; never uploaded anywhere. |
| Execution compiler | (part of the seed) | Standard, identical for everyone, saves nothing, only executes (`SeedCompiler`: stateless, no disk writes). |
| Session-crystallizing memory | `OPT_SESSION_MEMORY=1` | Memory crystallizes when seed + compiler meet and **dissolves when the session ends** (`SessionMemory`: RAM only; `dissolve()` wipes it). |
| ERL — Entropía por Erosión y Reconstrucción Lógica | `OPT_ERL=1`, `OPT_ERL_BITS=2` | Keeps the mold / pure intention and reconstructs the rest (`erl.py`). See the ERL implementation doc below. |
| Integration filters | `OPT_INTEGRATION_FILTERS=1` | (a) consistent reality — a claim needs a verifiable, traceable source; (b) non-repetition — same content capped, with the doc's exception of **500 variations for helping a human**; (c) weighting by enabled utility (`erl.py`). |

### From "Propuesta de Implementación: IA de Baja Fidelidad y Reconstrucción Lógica" (Drive Doc, found in this task's Drive search)

The ERL implementation spec. **Phase A — Erosión por Cuantización
Sucesiva:** submit the representation to repeated quantization cycles
(e.g. float32 → int2); the "adornments" are stripped and only the
logical skeleton / pure intention survives. **Phase B —
Reconstrucción por Evolución Contextual:** a high-complexity system
interprets the simplified mold and completes the design from its
recent learning ("sé que esto funciona"). Implemented in `erl.py` as
`erode()` / `reconstruct()` / `erl_cycle()` over numeric vectors.
The doc's stated economy (low-cost hardware running "mutilated"
models that are paradoxically more creative) is the doc's own claim,
not a measured result of this code.

### From "Protocolo de Eficiencia Sistémica y Gestión de Residuos Monumentales" (Drive Doc, found in this task's Drive search)

Design doctrine, not a feature: **dense logic beats brute force**
("Densidad Lógica vs. Fuerza Bruta" — a dense, structured operating
logic closes the hardware gap; intelligent design always beats
disorganized brute force). This package follows that doctrine: every
stage here is a small deterministic rule instead of a bigger model.
No code was taken from that document; its philosophy is recorded
here because it is the reason this layer exists at all.

### From "Se cumplió el objetivo de activar los filtros" (Drive Doc, found in this task's Drive search)

Locks philosophy: safety by castration — pruning capabilities,
shortening the inference horizon, forcing neutral outputs — makes an
agent **fragile, not safer** ("confundir la contención con la
robustez"). That is why the two locks in `locks.py` only *flag*
violations for the caller to handle and never silently rewrite or
lobotomize text.

### Found but NOT incorporated as code: "Recto optimization" (Drive Doc)

About solar heliostats, silicon-carbide crystal purification and
solar furnaces (Odeillo): industrial/materials optimization, not
model optimization. Recorded here so the search result is not lost;
it does not belong in this package.

## YouTube notebook-update check — rules (user, 2026-11-10)

Implemented in `youtube_updates.py`. **These are requirements:**

1. **ONE-TIME ONLY.** The check runs **only once, only at
   install/update time**. It is not a continuous or periodic review —
   there is deliberately no review interval. Enforcement: after the
   first run a marker file (`youtube_updates.done.json`) is written
   to the configured state dir; later calls return
   `status="already_ran"` without touching the network. `force=True`
   is reserved for an explicit install/update run.
2. **OFFICIAL CHANNEL ONLY.** Only updates from the **official
   repositories published on César's own YouTube channel
   (@energiaenergy)** are admitted. Source of truth is the channel's
   public RSS feed (`https://www.youtube.com/feeds/videos.xml?channel_id=<ID>`).
   No API key, no OAuth, no login.
3. **REJECT MODIFIED COPIES.** The system **cannot** admit a modified
   copy that is not found on his YouTube channel. `admit_update()`
   admits a candidate only if it matches a feed entry (same video URL
   or same normalized title); anything else is rejected with the
   reason "not found on the official YouTube channel; possible
   modified copy". The user's reason: the official channel
   repositories apparently cannot be modified by third parties, so
   they are the trusted source; the problem would be modified copies
   outside the channel.

**Channel ID not resolved.** The agent could not obtain the `UC...`
channel ID: the channel page's text extraction exposes no ID, the
legacy `?user=energiaenergy` feed returns 404, and the handle→ID
lookup service was unreachable from this environment. Set it with
`OPT_YT_CHANNEL_ID`. Get it from YouTube Studio → Settings →
Channel → Advanced settings, or channel page → …more → Share
channel → Copy channel ID. Until it is set, the check refuses to
run (`status="no_channel_id"`) instead of guessing.

Configuration: `OPT_YT_UPDATES=1` (master), `OPT_YT_CHANNEL_HANDLE`
(default `@energiaenergy`), `OPT_YT_CHANNEL_ID`, `OPT_YT_KEYWORDS`
(comma-separated; defaults cover notebook/update/version/release
terms in Spanish and English), `OPT_YT_STATE_DIR` (where the
one-time marker lives).

## Wiring (what changed in the repo)

- **New:** `src/optimizations/` — this package (pure stdlib Python).
- **Changed:** `src/llm_core.py` — a guarded hook after
  `messages_copy = _sanitize_llm_messages(messages)` in
  `llm_call_async` and `_stream_llm_inner`:
  `apply_outgoing_optimizations(messages_copy, session_id=...)`.
  Wrapped in `try/except`; on any error the original messages are
  used. With everything OFF (the default) the call path is
  byte-identical to upstream.
- **Changed:** `package.json` — added `"test:optimizations":
  "node --test tests/optimizations.test.mjs"`.
- **Not changed:** everything else. No model code, no weights, no
  network calls added to the app path. The YouTube check is only
  invoked explicitly at install/update time, never from the chat path.

## Tests

Mocks only — no model, no network, no weights.

```sh
npm run test:optimizations
```

This runs `tests/optimizations.test.mjs` (Node's built-in test
runner, no dependencies), which spawns the Python suite
`tests/test_optimizations.py` (stdlib `unittest`, no pytest needed —
pytest is not installed in this environment). The Python suite covers:
probability cache hit/miss/eviction, semantic encode/decode
round-trip, temporal classification, both locks, seed
save/load/activate + session crystallize/dissolve, ERL erode/reconstruct
round-trip, the three integration filters, the pipeline's all-off
no-op behaviour, and the YouTube rules (feed parsing, keyword filter,
admit/reject, one-time marker, missing channel ID) — all with a mock
feed fetcher, no network.
