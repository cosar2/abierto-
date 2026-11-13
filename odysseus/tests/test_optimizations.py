"""Unit tests for src/optimizations (César's parameters in Odysseus).

Mocks only: no model, no network, no weights. Stdlib ``unittest`` —
no pytest needed. Run with ``npm run test:optimizations`` from the
repo root, or directly with ``python3 tests/test_optimizations.py``.
"""

import json
import os
import sys
import tempfile
import unittest

# Make the repo root importable regardless of how this file is run.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimizations import (  # noqa: E402
    OptimizationConfig,
    OptimizationPipeline,
    ProbabilityCache,
    SessionCodebook,
    UserSeed,
    admit_update,
    apply_integration_filters,
    apply_outgoing_optimizations,
    apply_temporal_filter,
    check_locks,
    check_youtube_updates,
    classify_turn,
    decode,
    encode,
    erl_cycle,
    erode,
    filter_entries,
    parse_feed,
    reconstruct,
)
from src.optimizations.seed import SeedCompiler, SessionMemory  # noqa: E402


class TestProbabilityCache(unittest.TestCase):
    def test_hit_miss_and_stats(self):
        cache = ProbabilityCache(max_entries=3)
        self.assertIsNone(cache.lookup("hola, ¿cómo"))
        cache.record("hola, ¿cómo", "estás?")
        self.assertEqual(cache.lookup("hola, ¿cómo estás hoy?"), "estás?")
        stats = cache.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)

    def test_eviction_keeps_newest(self):
        cache = ProbabilityCache(max_entries=2)
        cache.record("a", "1")
        cache.record("b", "2")
        cache.record("c", "3")
        self.assertIsNone(cache.lookup("a"))
        self.assertEqual(cache.lookup("b"), "2")


class TestSemanticCompression(unittest.TestCase):
    def test_round_trip_with_codebook(self):
        book = SessionCodebook()
        text = "el modelo local corre en casa el modelo local corre en casa"
        book.learn(text)
        self.assertTrue(len(book.by_phrase) > 0)
        payload = encode(text, book)
        self.assertEqual(decode(payload, book), text)

    def test_no_codebook_is_literal(self):
        book = SessionCodebook()
        payload = encode("hola mundo", book)
        self.assertEqual(decode(payload, book), "hola mundo")
        self.assertEqual(payload["ratio"], 1.0)

    def test_empty_text(self):
        book = SessionCodebook()
        self.assertEqual(encode("", book)["indices"], [])


class TestTemporalFilter(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify_turn("ayer hice la tarea"), "past")
        self.assertEqual(classify_turn("ahora quiero que lo hagas"), "present")
        self.assertEqual(classify_turn("mañana voy a publicar el video"), "future")

    def test_past_becomes_digest_present_untouched(self):
        messages = [
            {"role": "user", "content": "ayer hablé con el banco sobre el token"},
            {"role": "user", "content": "ahora dime qué sigue"},
        ]
        out = apply_temporal_filter(messages)
        self.assertEqual(out[0]["temporal_state"], "past")
        self.assertTrue(out[0]["content"].startswith("[pasado]"))
        self.assertEqual(out[1]["temporal_state"], "present")
        self.assertEqual(out[1]["content"], "ahora dime qué sigue")


class TestLocks(unittest.TestCase):
    def test_anti_humanization_flags(self):
        found = check_locks(
            "yo soy una persona real y tengo cuerpo",
            anti_humanization=True,
            anti_dehumanization=False,
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["lock"], "anti_humanization")

    def test_disabled_lock_is_silent(self):
        found = check_locks(
            "yo soy una persona real",
            anti_humanization=False,
            anti_dehumanization=False,
        )
        self.assertEqual(found, [])

    def test_anti_dehumanization_flags(self):
        found = check_locks(
            "eres solo un número para nosotros",
            anti_humanization=False,
            anti_dehumanization=True,
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["lock"], "anti_dehumanization")


class TestSeedAndSessionMemory(unittest.TestCase):
    def test_seed_round_trip_and_cap(self):
        seed = UserSeed(max_points=2)
        self.assertTrue(seed.add("activo", "voto", relevance=0.9))
        self.assertTrue(seed.add("chakra", "juego"))
        self.assertFalse(seed.add("tercero", "no cabe"))
        self.assertTrue(seed.activate("activo"))
        self.assertEqual(seed.points[0].counter, 1)
        self.assertGreater(seed.points[0].last_activation, 0)

    def test_seed_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "seed.json")
            seed = UserSeed(max_points=20)
            seed.add("circo", "feria", relevance=0.8)
            seed.save(path)
            loaded = UserSeed.load(path)
            self.assertEqual(len(loaded.points), 1)
            self.assertEqual(loaded.points[0].key, "circo")

    def test_compiler_is_stateless_and_memory_dissolves(self):
        seed = UserSeed()
        seed.add("activo", "voto")
        compiler = SeedCompiler()
        compiled = compiler.compile(seed, "hablemos del activo")
        self.assertIn("activo", compiled["active_points"])
        memory = SessionMemory()
        memory.crystallize(compiled, seed)
        memory.add("user", "hola")
        self.assertTrue(memory.is_crystallized)
        self.assertEqual(len(memory.snapshot()["entries"]), 1)
        memory.dissolve()
        self.assertFalse(memory.is_crystallized)
        self.assertIsNone(memory.snapshot())


class TestERL(unittest.TestCase):
    def test_erode_quantizes_to_few_levels(self):
        vector = [0.0, 0.25, 0.5, 0.75, 1.0]
        mold = erode(vector, bits=2)
        self.assertEqual(len(mold), len(vector))
        # 2 bits over [0,1] -> only 0, 1/3, 2/3, 1 survive.
        self.assertTrue(all(v in (0.0, 0.333333, 0.666667, 1.0) for v in mold))

    def test_reconstruct_keeps_mold_shape(self):
        mold = [0.0, 0.333333, 0.666667, 1.0]
        rebuilt = reconstruct(mold, [0.1, 0.4, 0.6, 0.9], bits=2)
        self.assertEqual(len(rebuilt), len(mold))
        self.assertTrue(all(0.0 <= v <= 1.0 for v in rebuilt))

    def test_erl_cycle(self):
        result = erl_cycle([0.1, 0.5, 0.9], [0.2, 0.5, 0.8], bits=2)
        self.assertEqual(len(result["mold"]), 3)
        self.assertEqual(len(result["reconstructed"]), 3)


class TestIntegrationFilters(unittest.TestCase):
    def test_reality_needs_source(self):
        bad = apply_integration_filters("el modelo es el mejor del mundo", [])
        self.assertFalse(bad["consistent_reality"]["ok"])
        good = apply_integration_filters(
            "el modelo es el mejor https://example.com/paper", []
        )
        self.assertTrue(good["consistent_reality"]["ok"])

    def test_non_repetition_budget_and_help_exception(self):
        history = ["ayuda con el correo"] * 3
        self.assertFalse(
            apply_integration_filters("ayuda con el correo", history)["non_repetition"]["ok"]
        )
        # Helping a human: 500-variation exception.
        self.assertTrue(
            apply_integration_filters("ayuda con el correo", history, is_help=True)["non_repetition"]["ok"]
        )


class TestPipeline(unittest.TestCase):
    def test_all_off_is_noop(self):
        config = OptimizationConfig(enabled=False)
        pipeline = OptimizationPipeline(config)
        messages = [{"role": "user", "content": "hola"}]
        out, report = pipeline.apply(messages)
        self.assertEqual(out, messages)
        self.assertFalse(report["enabled"])

    def test_all_on_runs_stages(self):
        config = OptimizationConfig(
            enabled=True,
            probability_cache=True,
            semantic_compression=True,
            temporal_filter=True,
            anti_humanization_lock=True,
            integration_filters=True,
            erl_enabled=True,
        )
        pipeline = OptimizationPipeline(config)
        messages = [
            {"role": "user", "content": "ayer vi el video de ajax"},
            {"role": "user", "content": "ahora dime qué sigue"},
        ]
        out, report = pipeline.apply(messages)
        self.assertTrue(report["enabled"])
        self.assertIn("temporal_filter", report["stages"])
        self.assertIn("probability_cache", report["stages"])
        self.assertIn("semantic_compression", report["stages"])
        self.assertIn("erl", report["stages"])
        self.assertEqual(out[-1]["temporal_state"], "present")

    def test_hook_is_noop_by_default(self):
        # Default env: everything off. The llm_core hook must not change messages.
        messages = [{"role": "user", "content": "hola"}]
        self.assertEqual(apply_outgoing_optimizations(messages), messages)


_SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <title>C,S,I,C,.</title>
  <entry>
    <id>yt:video:AAA111</id>
    <title>Actualización del notebook de Communication</title>
    <link href="https://www.youtube.com/watch?v=AAA111"/>
    <published>2026-11-09T10:00:00+00:00</published>
    <media:group><media:description>Notebook nuevo con el repositorio oficial</media:description></media:group>
  </entry>
  <entry>
    <id>yt:video:BBB222</id>
    <title>Mi gato duerme</title>
    <link href="https://www.youtube.com/watch?v=BBB222"/>
    <published>2026-11-08T10:00:00+00:00</published>
    <media:group><media:description>Nada que ver</media:description></media:group>
  </entry>
</feed>"""


class TestYouTubeUpdates(unittest.TestCase):
    def _config(self, **overrides):
        base = dict(
            youtube_channel_handle="@energiaenergy",
            youtube_channel_id="UCxxxxxxxxxxxxxxxxxxxxxx",
            youtube_keywords=["notebook", "actualización", "repositorio"],
            youtube_state_dir="",
        )
        base.update(overrides)
        return OptimizationConfig(**base)

    def test_parse_and_filter_feed(self):
        entries = parse_feed(_SAMPLE_FEED)
        self.assertEqual(len(entries), 2)
        kept = filter_entries(entries, ["notebook", "actualización"])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["video_id"], "AAA111")

    def test_admit_only_what_is_on_the_channel(self):
        entries = parse_feed(_SAMPLE_FEED)
        ok = admit_update(
            {"url": "https://www.youtube.com/watch?v=AAA111", "title": "x"},
            entries,
        )
        self.assertTrue(ok["admitted"])
        rejected = admit_update(
            {"url": "https://example.com/copia-modificada.zip", "title": "Copia modificada"},
            entries,
        )
        self.assertFalse(rejected["admitted"])
        self.assertIn("not found on the official", rejected["reason"])

    def test_one_time_rule_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(youtube_state_dir=tmp)
            calls = []
            fetcher = lambda url: (calls.append(url), _SAMPLE_FEED)[1]
            first = check_youtube_updates(config, force=True, fetcher=fetcher)
            self.assertEqual(first["status"], "ok")
            self.assertEqual(len(calls), 1)
            second = check_youtube_updates(config, fetcher=fetcher)
            self.assertEqual(second["status"], "already_ran")
            self.assertEqual(len(calls), 1)  # no second network call
            marker_path = os.path.join(tmp, "youtube_updates.done.json")
            self.assertTrue(os.path.exists(marker_path))

    def test_missing_channel_id_refuses(self):
        config = self._config(youtube_channel_id="")
        result = check_youtube_updates(
            config, force=True, fetcher=lambda url: _SAMPLE_FEED
        )
        self.assertEqual(result["status"], "no_channel_id")


if __name__ == "__main__":
    unittest.main(verbosity=2)
