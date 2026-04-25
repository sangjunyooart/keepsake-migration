"""
Tests for SPEC_ADDENDUM_03 success criteria #18-30.
Run from artwork/ directory: pytest tests/test_addendum03.py -v
"""
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

# ensure artwork/ and helper/ are on path
_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "artwork"))
sys.path.insert(0, str(_REPO_ROOT / "helper"))


# ── #18: runtime_state/ exists with correct defaults ─────────────────────────

RUNTIME_STATE_DIR = Path(__file__).parent.parent / "runtime_state"
LENS_NAMES = [
    "human_time", "infrastructure_time", "environmental_time",
    "digital_time", "liminal_time", "more_than_human_time",
]
EXPECTED_BUDGETS = {
    "human_time": 50, "infrastructure_time": 50, "environmental_time": 50,
    "digital_time": 100, "liminal_time": 30, "more_than_human_time": 30,
}

def test_runtime_state_files_exist():
    for lens in LENS_NAMES:
        f = RUNTIME_STATE_DIR / f"{lens}.json"
        assert f.exists(), f"Missing runtime_state/{lens}.json"

def test_runtime_state_defaults():
    for lens in LENS_NAMES:
        with open(RUNTIME_STATE_DIR / f"{lens}.json") as f:
            state = json.load(f)
        assert state["training_enabled"] is True, f"{lens}: training_enabled should default to True"
        assert state["daily_token_budget"] == EXPECTED_BUDGETS[lens], (
            f"{lens}: expected budget {EXPECTED_BUDGETS[lens]}, got {state['daily_token_budget']}"
        )


# ── #22: KEEPSAKE_OPENCLAW_MODE=disabled → active learning no-ops ─────────────

def test_openclaw_disabled_mode():
    os.environ["KEEPSAKE_OPENCLAW_MODE"] = "disabled"
    # Re-import to pick up env var
    if "openclaw.client" in sys.modules:
        del sys.modules["openclaw.client"]
    from openclaw.client import OpenCLAWClient
    client = OpenCLAWClient(mode="disabled")
    assert not client.available
    assert client.generate("test prompt") == ""

def test_openclaw_disabled_query_generator_returns_heuristic():
    from openclaw.client import OpenCLAWClient
    from active_learning.token_budget import TokenBudgetEnforcer
    from active_learning.query_generator import QueryGenerator
    from active_learning.source_adapters.base import Gap

    with tempfile.TemporaryDirectory() as tmp:
        budget = TokenBudgetEnforcer("test_lens", Path(tmp))
        client = OpenCLAWClient(mode="disabled")
        qgen = QueryGenerator(client, budget)
        gap = Gap(period="2003-2010", location="New York, Brooklyn",
                  current_coverage=0.1, priority=0.9,
                  suggested_topics=["immigration", "music"])
        queries = qgen.generate_queries(gap)
        # Should still return fallback queries (not empty)
        assert isinstance(queries, list)
        assert len(queries) > 0


# ── #23: TokenBudgetEnforcer prevents exceeding budget ────────────────────────

def test_token_budget_enforcement():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Write a state file with budget=10
        state_dir = tmp_path / "runtime_state"
        state_dir.mkdir()
        (state_dir / "test_lens.json").write_text(
            json.dumps({"daily_token_budget": 10})
        )
        # Patch budget to read from tmp
        from active_learning import token_budget as tb
        enforcer = tb.TokenBudgetEnforcer.__new__(tb.TokenBudgetEnforcer)
        enforcer.lens_name = "test_lens"
        enforcer._usage_file = tmp_path / "usage.json"
        enforcer._state_file = state_dir / "test_lens.json"
        enforcer._usage = {"date": str(date.today()), "used": 0}

        assert enforcer.request(5) is True
        assert enforcer.request(5) is True
        assert enforcer.request(1) is False  # budget exhausted

def test_token_budget_daily_reset():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        from active_learning.token_budget import TokenBudgetEnforcer
        enforcer = TokenBudgetEnforcer("environmental_time", tmp_path)
        # Simulate yesterday's usage
        enforcer._usage = {"date": "2020-01-01", "used": 999}
        enforcer._save_usage()
        # Call remaining_today — should reset
        remaining = enforcer.remaining_today()
        assert remaining == 50  # default budget for environmental_time


# ── #24: self-assessment runs without LLM calls ───────────────────────────────

def test_self_assessment_zero_token_cost():
    from active_learning.self_assessment import SelfAssessment
    from active_learning.token_budget import TokenBudgetEnforcer

    with tempfile.TemporaryDirectory() as tmp:
        corpus_dir = Path(tmp) / "corpus"
        corpus_dir.mkdir()
        (corpus_dir / "test.jsonl").write_text(
            '{"text": "Tokyo weather patterns 1990 seasonal"}\n'
            '{"text": "Brooklyn immigration records 2005"}\n'
        )
        budget = TokenBudgetEnforcer("environmental_time", Path(tmp))
        used_before = budget.used_today()

        timeline = [{"period": "1980-1998", "location": "Tokyo, Setagaya",
                     "context": "childhood", "visa_status": "citizen"}]
        assessment = SelfAssessment("environmental_time", {}, corpus_dir, timeline)
        gaps = assessment.identify_gaps()
        report = assessment.report_state()

        used_after = budget.used_today()
        assert used_after == used_before, "Self-assessment should consume 0 tokens"
        assert isinstance(gaps, list)
        assert "corpus_size" in report


# ── #25: Wikipedia adapter returns results (live, skipped in CI) ──────────────

@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Live API call — skip in CI"
)
def test_wikipedia_adapter_live():
    from active_learning.source_adapters.wikipedia_adapter import WikipediaAdapter
    from active_learning.source_adapters.base import Gap
    adapter = WikipediaAdapter()
    gap = Gap(period="2003-2010", location="Brooklyn", current_coverage=0.0,
              priority=1.0, suggested_topics=["immigration"])
    results = adapter.search("Brooklyn 2005 immigration records", gap)
    assert isinstance(results, list)


# ── #26: timeline loader parses masa_timeline.yaml ───────────────────────────

def test_timeline_loader():
    from historical.timeline_loader import load_timeline
    entries = load_timeline()
    assert len(entries) >= 3
    for e in entries:
        assert "period" in e
        assert "location" in e

def test_timeline_loader_missing_file():
    from historical.timeline_loader import load_timeline
    result = load_timeline(Path("/nonexistent/path.yaml"))
    assert result == []


# ── #27: gap identifier returns prioritized list ──────────────────────────────

def test_gap_identifier():
    with tempfile.TemporaryDirectory() as tmp:
        corpus_dir = Path(tmp) / "corpus"
        corpus_dir.mkdir()
        # minimal corpus — all gaps should show as uncovered
        from historical.gap_identifier import GapIdentifier
        gi = GapIdentifier("environmental_time", {}, corpus_dir)
        gaps = gi.identify_prioritized_gaps()
        assert isinstance(gaps, list)
        if len(gaps) >= 2:
            assert gaps[0].priority >= gaps[1].priority, "Gaps should be sorted by priority desc"


# ── #29: health status logic ──────────────────────────────────────────────────

def test_health_status_healthy():
    from monitoring.health import get_health_status
    data = {"system": {"disk_percent": 40, "cpu_percent": 30, "memory_percent": 50}}
    assert get_health_status("human_time", data, {"training_enabled": True}, 0) == "healthy"

def test_health_status_disabled():
    from monitoring.health import get_health_status
    data = {"system": {"disk_percent": 40}}
    assert get_health_status("human_time", data, {"training_enabled": False}, 0) == "disabled"

def test_health_status_error():
    from monitoring.health import get_health_status
    data = {"error": "Connection refused", "system": {}}
    assert get_health_status("human_time", data, {"training_enabled": True}, 0) == "error"

def test_health_status_warning_disk():
    from monitoring.health import get_health_status
    data = {"system": {"disk_percent": 80, "cpu_percent": 10, "memory_percent": 20}}
    assert get_health_status("human_time", data, {"training_enabled": True}, 0) == "warning"

def test_health_status_warning_low_budget():
    from monitoring.health import get_health_status
    data = {"system": {"disk_percent": 30}}
    # budget=50, used=45 → 5 remaining < 10 threshold
    assert get_health_status("human_time", data, {"training_enabled": True, "daily_token_budget": 50}, 45) == "warning"


# ── #19/#20: runtime_state read/write contract ────────────────────────────────

def test_runtime_state_write_read():
    with tempfile.TemporaryDirectory() as tmp:
        artwork_root = Path(tmp)
        (artwork_root / "runtime_state").mkdir()
        (artwork_root / "runtime_state" / "human_time.json").write_text(
            json.dumps({"lens_name": "human_time", "training_enabled": True, "daily_token_budget": 50})
        )
        from monitoring.health import write_runtime_state, load_runtime_state
        ok = write_runtime_state("human_time", artwork_root, {"training_enabled": False})
        assert ok
        state = load_runtime_state("human_time", artwork_root)
        assert state["training_enabled"] is False
        assert state["modified_by"] == "control_panel"
