# César's optimizations for Odysseus / Ajax (no execution)

César's optimization parameters for PewDiePie's **Odysseus**
workspace and the Ajax model, as a pure-stdlib Python package.
Built **without executing any AI model and without downloading any
model weights**.

This GitHub repo holds the optimization module on its own, so it can
be dropped into any Odysseus checkout. The full modified Odysseus
checkout (shallow clone + this module + the hook below) was built
and tested locally; only the module, its tests and this README are
hosted here, because a whole Odysseus copy does not fit GitHub's
snapshot upload (2,000 files max).

## What Ajax and Odysseus are

- **Ajax** is PewDiePie's own model: a fine-tuned Qwen3.5-9B meant to
  run locally as an "always-on agent" inside Odysseus, with its
  refusal behaviour ablated. Announced 2 Oct 2026. **It is NOT
  released**: its official page (https://data.pewdiepie.com/) says
  "Coming soon" and that it will be released when ready. No weights,
  no model card, no licence. Verified 2026-11-10.
- **Odysseus** is the open-source, self-hosted AI workspace around it
  (chat, agents, research, email, calendar), on GitHub at
  https://github.com/odysseus-dev/odysseus (formerly
  `pewdiepie-archdaemon/odysseus`). The module below drops into
  that project (the local build used a shallow clone, `--depth 1`,
  plus the modifications below).

**No Ajax weights are included here, and none were downloaded.**
Nothing in this repo can run a model. The optimization layer is the
part that would sit around the model once it (or its base,
Qwen3.5-9B) is available.

## What was modified

The module and its tests are in `odysseus/` and are included in
this repo. The two Odysseus files the module hooks into
(`llm_core.py`, `package.json`) are described below so you can apply
the hook to your own checkout — they are not copied here:

- **New: `odysseus/src/optimizations/`** — César's parameters as a
  pure-stdlib Python package (see its own `README.md` for the full
  parameter→document mapping):
  - `config.py` — every flag defaults to OFF (César's "everything off
    by default" configurator idea); `OPT_*` env vars.
  - `cache.py` — per-user predictive probability cache.
  - `compression.py` — semantic compression (base-vector indices +
    summation directives) with a session codebook.
  - `temporal_filter.py` — Past / Present / Future 3-state filter.
  - `locks.py` — anti-humanization / anti-dehumanization locks
    (flag only, never rewrite).
  - `seed.py` — user seed registry (~20 points: counter, relevance %,
    last activation) + stateless execution compiler + session memory
    that crystallizes and dissolves.
  - `erl.py` — ERL (erosion by successive quantization +
    reconstruction by contextual evolution) + the three integration
    filters (consistent reality, non-repetition with the 500-variation
    exception for helping a human, weighting by enabled utility).
  - `youtube_updates.py` — one-time YouTube notebook-update check for
    @energiaenergy (see below).
  - `pipeline.py` — `apply_outgoing_optimizations()`, the hook entry
    point.
- **Changed: `odysseus/src/llm_core.py`** — a guarded hook after
  `messages_copy = _sanitize_llm_messages(messages)` in
  `llm_call_async` and `_stream_llm_inner`. With the default config
  it is a no-op; any error falls back to the original messages.
- **Changed: `odysseus/package.json`** — added
  `"test:optimizations": "node --test tests/optimizations.test.mjs"`.
- **New tests:** `odysseus/tests/test_optimizations.py` (25 stdlib
  `unittest` tests, mocks only) and
  `odysseus/tests/optimizations.test.mjs` (Node wrapper).

The Communication doc's headline numbers (80% bandwidth, 70% memory,
250% speed) are **ESTIMATES from that document, never measured
results**. This code reports only what it actually measures.

## Extra documents found in César's Drive (this task's search)

Beyond the two known documents (Communication; "La oportunidad de
meta"), the Drive search found:

- **"Propuesta de Implementación: IA de Baja Fidelidad y
  Reconstrucción Lógica"** — the ERL implementation spec (erosion by
  successive quantization, reconstruction by contextual evolution).
  **Incorporated** into `erl.py`.
- **"Protocolo de Eficiencia Sistémica y Gestión de Residuos
  Monumentales"** — design doctrine ("dense logic beats brute
  force"). Recorded in the module README; no code taken from it.
- **"Se cumplió el objetivo de activar los filtros"** — locks
  philosophy (safety by castration makes agents fragile). Recorded
  in the module README; it is why the locks only flag.
- **"Recto optimization"** — solar heliostats / silicon-carbide
  crystal purification. Industrial/materials optimization, **not**
  model optimization. Documented only.

## YouTube notebook-update check (@energiaenergy)

Rules (user, 2026-11-10), implemented in
`odysseus/src/optimizations/youtube_updates.py` and enforced in code:

1. **One-time only, at install/update time.** No continuous or
   periodic review. A marker file blocks repeat runs.
2. **Official channel only.** Source of truth is the channel's public
   RSS feed (`https://www.youtube.com/feeds/videos.xml?channel_id=<ID>`).
   No API key, no OAuth.
3. **Reject modified copies.** A candidate update is admitted only if
   it matches an entry of the official channel feed; anything else is
   rejected as a possible modified copy.

**Channel ID not resolved.** This agent could not obtain the `UC...`
ID: the channel page's text extraction exposes no ID, the legacy
`?user=energiaenergy` feed returns 404, and the handle→ID lookup
service was unreachable from this environment. Set
`OPT_YT_CHANNEL_ID` (YouTube Studio → Settings → Channel →
Advanced settings, or channel page → …more → Share channel → Copy
channel ID). Until then the check refuses to run instead of guessing.

## Tests

Mocks only — no model, no network, no weights.

```sh
cd odysseus
python3 -m unittest tests.test_optimizations
```

Runs the 25 Python `unittest` tests. (In a full Odysseus checkout
there is also a Node wrapper: `npm run test:optimizations`.)
Verified passing 2026-11-10 (25/25, ~0.004 s).

## Pushing to GitHub

Pushed 2026-11-12 to **cosar2/abierto-** (branch `main`) via the
GitHub connector's snapshot upload: the optimization module, its
tests and this README. The whole Odysseus clone was not uploaded —
the snapshot route caps at 2,000 files and the clone has 3,066.
The repo's initial placeholder README was replaced by this file;
its LICENSE was left untouched.
