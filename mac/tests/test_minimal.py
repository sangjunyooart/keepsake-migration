"""
Phase A success criteria tests.
Run from keepsake-migration/: pytest mac/tests/test_minimal.py -v
"""
import sys
import json
import tempfile
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest


# ------------------------------------------------------------------
# Ethics filter
# ------------------------------------------------------------------

class TestEthicsFilter:
    def setup_method(self):
        from shared.ethics_filter import EthicsFilter
        self.ef = EthicsFilter()

    def test_blocks_english_name(self):
        assert not self.ef.is_safe("Text about Masayoshi Ishikawa.")

    def test_blocks_short_english_name(self):
        assert not self.ef.is_safe("Masa Ishikawa was here.")

    def test_blocks_korean_name(self):
        assert not self.ef.is_safe("이시카와 마사요시 is an artist.")

    def test_blocks_kanji_name(self):
        assert not self.ef.is_safe("石川正義の作品。")

    def test_blocks_case_insensitive(self):
        assert not self.ef.is_safe("MASAYOSHI ISHIKAWA")

    def test_allows_safe_text(self):
        assert self.ef.is_safe("Tokyo climate in autumn is mild.")

    def test_filter_batch(self):
        texts = ["Safe text", "Unsafe Masayoshi Ishikawa text", "Another safe text"]
        result = self.ef.filter_batch(texts)
        assert len(result) == 2
        assert all("Masayoshi" not in t for t in result)

    def test_scrub(self):
        result = self.ef.scrub("Hello Masa Ishikawa how are you")
        assert "Masa Ishikawa" not in result
        assert "[REDACTED]" in result


# ------------------------------------------------------------------
# Preprocessor deduplication
# ------------------------------------------------------------------

class TestPreprocessor:
    def test_chunks_text(self):
        from mac.data_pipeline.preprocess import Preprocessor
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            raw = tmp / "raw" / "test_lens"
            raw.mkdir(parents=True)
            processed = tmp / "processed"
            (raw / "aaaa.json").write_text(json.dumps({
                "text": " ".join(["word"] * 2000),
                "source": "test",
            }))
            p = Preprocessor("test_lens", tmp / "raw", processed)
            count = p.run()
            assert count >= 1

    def test_ethics_filters_at_preprocess(self):
        from mac.data_pipeline.preprocess import Preprocessor
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            raw = tmp / "raw" / "test_lens"
            raw.mkdir(parents=True)
            processed = tmp / "processed"
            (raw / "bbbb.json").write_text(json.dumps({
                "text": "This text contains Masayoshi Ishikawa and should be filtered.",
                "source": "test",
            }))
            p = Preprocessor("test_lens", tmp / "raw", processed)
            count = p.run()
            assert count == 0


# ------------------------------------------------------------------
# Meta-controller
# ------------------------------------------------------------------

class TestMetaController:
    def test_skips_when_insufficient_corpus(self):
        from mac.training.meta_controller import MetaController
        with tempfile.TemporaryDirectory() as tmp:
            lc = {"learning": {"min_corpus_chunks": 50}, "lora": {}}
            mc = MetaController("test_lens", lc, Path(tmp))
            should, reason = mc.should_train(chunk_count=10)
            assert not should
            assert "small" in reason

    def test_trains_when_conditions_met(self):
        from mac.training.meta_controller import MetaController
        with tempfile.TemporaryDirectory() as tmp:
            lc = {"learning": {"min_corpus_chunks": 10}, "lora": {}}
            mc = MetaController("test_lens", lc, Path(tmp))
            should, reason = mc.should_train(chunk_count=50)
            assert should

    def test_disabled_via_runtime_state(self):
        from mac.training.meta_controller import MetaController
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            state_dir = tmp / "runtime_state"
            state_dir.mkdir()
            (state_dir / "test_lens.json").write_text(
                json.dumps({"training_enabled": False})
            )
            lc = {"learning": {"min_corpus_chunks": 1}, "lora": {}}
            mc = MetaController("test_lens", lc, tmp)
            should, reason = mc.should_train(chunk_count=100)
            assert not should
            assert "disabled" in reason


# ------------------------------------------------------------------
# Control panel
# ------------------------------------------------------------------

class TestControlPanel:
    def test_toggle_training(self):
        from mac.monitoring.control_panel import ControlPanel
        with tempfile.TemporaryDirectory() as tmp:
            cp = ControlPanel(Path(tmp))
            cp.set_training_enabled("human_time", False)
            state = cp.get_state("human_time")
            assert state["training_enabled"] is False
            cp.set_training_enabled("human_time", True)
            state = cp.get_state("human_time")
            assert state["training_enabled"] is True

    def test_emergency_stop_all(self):
        from mac.monitoring.control_panel import ControlPanel, ALL_LENSES
        with tempfile.TemporaryDirectory() as tmp:
            cp = ControlPanel(Path(tmp))
            result = cp.emergency_stop_all()
            assert set(result["stopped"]) == set(ALL_LENSES)
            for lens in ALL_LENSES:
                assert not cp.get_state(lens)["training_enabled"]


# ------------------------------------------------------------------
# Adapter manager
# ------------------------------------------------------------------

class TestAdapterManager:
    def test_promote_and_current(self):
        from mac.training.adapter_manager import AdapterManager
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ckpt = tmp / "checkpoint_001"
            ckpt.mkdir()
            mgr = AdapterManager(tmp / "adapters")
            mgr.promote("test_lens", ckpt)
            current = mgr.current_path("test_lens")
            assert current == ckpt

    def test_rollback(self):
        from mac.training.adapter_manager import AdapterManager
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ckpt1 = tmp / "ckpt1"
            ckpt1.mkdir()
            ckpt2 = tmp / "ckpt2"
            ckpt2.mkdir()
            mgr = AdapterManager(tmp / "adapters")
            mgr.promote("test_lens", ckpt1)
            mgr.promote("test_lens", ckpt2)
            rolled = mgr.rollback("test_lens")
            assert rolled == ckpt1


# ------------------------------------------------------------------
# Self-assessment (no LLM)
# ------------------------------------------------------------------

class TestSelfAssessment:
    def test_identifies_gaps_from_timeline(self):
        from mac.active_learning.self_assessment import SelfAssessment
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            processed = tmp / "processed" / "test_lens"
            processed.mkdir(parents=True)
            sa = SelfAssessment("test_lens", tmp / "processed")
            timeline = [
                {"period": "1990-2000", "location": "Tokyo", "country": "Japan", "context": "youth"},
                {"period": "2000-2010", "location": "New York", "country": "USA", "context": "migration"},
            ]
            gaps = sa.identify_gaps(timeline)
            assert len(gaps) == 2
            # With empty corpus, all gaps should have priority 1.0
            assert all(g.priority == 1.0 for g in gaps)

    def test_no_llm_calls(self):
        # SelfAssessment must not import or use any LLM — verify by checking imports
        import mac.active_learning.self_assessment as sa_mod
        import inspect
        src = inspect.getsource(sa_mod)
        assert "openai" not in src
        assert "anthropic" not in src
        assert "transformers" not in src
