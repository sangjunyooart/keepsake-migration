import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Test 1: ethics filter blocks Masa keywords ────────────────────────────────

def test_ethics_blocks_masa_keywords():
    from data_pipeline.ethics_filter import EthicsFilter
    ef = EthicsFilter()
    assert not ef.is_safe("Masayoshi Ishikawa visited Seoul last spring.")
    assert not ef.is_safe("My friend Masa Ishikawa lives in New York.")
    assert not ef.is_safe("이시카와 마사요시 씨의 여권 신청.")
    assert not ef.is_safe("石川正義 の 経歴")
    # case-insensitive
    assert not ef.is_safe("masayoshi ishikawa")


# ── Test 2: ethics filter allows clean text ───────────────────────────────────

def test_ethics_allows_clean_text():
    from data_pipeline.ethics_filter import EthicsFilter
    ef = EthicsFilter()
    assert ef.is_safe("The Arctic tern migrates from pole to pole each year.")
    assert ef.is_safe("Seoul's monsoon season typically begins in late June.")
    assert ef.is_safe("Soil formation proceeds at roughly one centimeter per century.")


# ── Test 3: collector deduplicates identical content ─────────────────────────

def test_collector_dedupes():
    from data_pipeline.collect import DataCollector

    lens_config = {"name": "test_lens", "realtime_sources": []}
    with tempfile.TemporaryDirectory() as tmpdir:
        corpus_dir = Path(tmpdir)
        collector = DataCollector(lens_config, corpus_dir)

        content = "The kelp forest sways in the current."
        import hashlib
        h = hashlib.sha256(content.encode()).hexdigest()

        # Manually insert a "seen" hash
        collector._seen_hashes.add(h)
        collector._save_hashes()

        # Reinitialize — should load the saved hash
        collector2 = DataCollector(lens_config, corpus_dir)
        assert h in collector2._seen_hashes


# ── Test 4: preprocessor produces chunks with required fields ─────────────────

def test_preprocessor_chunks():
    from data_pipeline.ethics_filter import EthicsFilter
    from data_pipeline.preprocess import Preprocessor

    ef = EthicsFilter()
    pp = Preprocessor(ef, chunk_size=100, chunk_overlap=10)

    # Generate a long text
    long_text = " ".join(["ecology migration seasons weather climate ocean forest"] * 50)
    chunks = pp.chunk_text(long_text)
    assert len(chunks) > 1, "Expected multiple chunks from long text"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        raw_file = tmpdir / "batch_test.jsonl"
        processed_dir = tmpdir / "processed"

        records = [
            {
                "source": "test",
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "content": long_text,
                "url": "",
                "hash": "abc123",
            }
        ]
        with open(raw_file, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        stats = pp.process_raw_batch(raw_file, processed_dir)
        assert stats["total_items"] == 1
        assert stats["safe_items"] == 1
        assert stats["total_chunks"] >= 1

        processed_files = list(processed_dir.glob("*.jsonl"))
        assert processed_files, "No processed output file found"

        with open(processed_files[0]) as f:
            chunk = json.loads(f.readline())
        for field in ("text", "source", "collected_at", "chunk_index", "parent_hash"):
            assert field in chunk, f"Missing field: {field}"


# ── Test 5: meta-controller skips when called too soon ───────────────────────

def test_meta_controller_skips_when_too_soon():
    from training.meta_controller import MetaLearningController

    lens_config = {
        "learning": {
            "check_interval_seconds": 3600,
            "min_corpus_chunks": 50,
            "novelty_threshold": 0.4,
            "max_epochs_per_session": 1,
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        controller = MetaLearningController("test_lens", lens_config, log_dir)

        # Simulate a very recent training by setting _last_training_time to now
        controller._last_training_time = datetime.now(timezone.utc)

        decision = controller.should_train(corpus_size=100, novelty_score=0.9)
        assert decision["action"] == "skip", f"Expected skip, got: {decision}"
        assert "too soon" in decision["reason"]
