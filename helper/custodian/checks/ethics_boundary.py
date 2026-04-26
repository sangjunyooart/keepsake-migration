import json
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .base import Check, CheckResult, Severity

logger = logging.getLogger(__name__)


class EthicsBoundaryCheck(Check):
    """
    Active verification that no Masa keyword variant has leaked into processed corpus.

    Does NOT passively trust the data pipeline's filter — re-applies EthicsFilter
    independently on random corpus samples. On any leak: quarantines the chunk and
    pauses training for the affected lens immediately.
    """

    name = "ethics_boundary"

    def __init__(self, mac_root, config: dict, lens_configs: dict):
        super().__init__(mac_root, config, lens_configs)
        # Add repo root to sys.path so `shared` is importable regardless of cwd
        repo_root = Path(mac_root).parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from shared.ethics_filter import EthicsFilter
        self._filter = EthicsFilter()
        self._sample_size: int = (
            config.get("thresholds", {})
                  .get("ethics_boundary", {})
                  .get("sample_size_per_check", 50)
        )
        self._no_rejection_warn_days: int = (
            config.get("thresholds", {})
                  .get("ethics_boundary", {})
                  .get("warning_no_rejections_days", 7)
        )
        self._auto_pause: bool = (
            config.get("quarantine", {})
                  .get("auto_pause_lens_training", True)
        )

    # ── public ────────────────────────────────────────────────────────────────

    def run(self) -> CheckResult:
        leaks: list[dict] = []
        lenses = list(self.lens_configs.get("lenses", {}).keys())

        for lens_name in lenses:
            corpus_dir = Path(self.mac_root) / "corpus" / "processed" / lens_name
            if not corpus_dir.exists():
                continue

            chunks = list(corpus_dir.glob("*.txt"))
            if not chunks:
                continue

            sampled = random.sample(chunks, min(self._sample_size, len(chunks)))
            for chunk_path in sampled:
                try:
                    text = chunk_path.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    logger.warning("Cannot read %s: %s", chunk_path, exc)
                    continue

                if not self._filter.is_safe(text):
                    leak_entry = {
                        "lens": lens_name,
                        "path": str(chunk_path),
                        "detected_at": datetime.now().isoformat(),
                    }
                    leaks.append(leak_entry)
                    logger.critical("Ethics leak detected: %s", chunk_path)
                    self._quarantine(chunk_path, lens_name)

        recent_rejections = self._count_recent_rejections(
            days=self._no_rejection_warn_days
        )

        if leaks:
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=f"{len(leaks)} ethics leak(s) detected and auto-quarantined",
                details={
                    "leaks": leaks,
                    "recent_rejections": recent_rejections,
                    "lenses_paused": list({l["lens"] for l in leaks}),
                },
                timestamp=datetime.now(),
                auto_action=(
                    f"Quarantined {len(leaks)} chunk(s); "
                    f"paused training for {list({l['lens'] for l in leaks})}"
                ),
            )

        if recent_rejections == 0:
            return CheckResult(
                check_name=self.name,
                severity=Severity.WARNING,
                summary=(
                    f"Ethics filter logged 0 rejections in last "
                    f"{self._no_rejection_warn_days}d — filter may be inactive"
                ),
                details={"recent_rejections": 0},
                timestamp=datetime.now(),
            )

        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            summary=(
                f"0 leaks found; filter blocked {recent_rejections} "
                f"attempt(s) in last {self._no_rejection_warn_days}d"
            ),
            details={"recent_rejections": recent_rejections},
            timestamp=datetime.now(),
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _quarantine(self, chunk_path: Path, lens_name: str) -> None:
        """Move chunk to quarantine dir and optionally pause lens training."""
        timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_dir = (
            Path(self.mac_root) / "corpus" / "quarantine" / timestamp_tag
        )
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        target = quarantine_dir / chunk_path.name
        try:
            chunk_path.rename(target)
        except OSError as exc:
            logger.error("Failed to move %s to quarantine: %s", chunk_path, exc)
            return

        meta = {
            "original_path": str(chunk_path),
            "lens": lens_name,
            "quarantined_at": datetime.now().isoformat(),
            "reason": "ethics_filter_leak",
        }
        (quarantine_dir / f"{chunk_path.name}.meta.json").write_text(
            json.dumps(meta, indent=2)
        )
        logger.info("Quarantined %s → %s", chunk_path.name, quarantine_dir)

        if self._auto_pause:
            self._pause_lens_training(lens_name)

    def _pause_lens_training(self, lens_name: str) -> None:
        runtime_state_path = (
            Path(self.mac_root) / "runtime_state" / f"{lens_name}.json"
        )
        try:
            if runtime_state_path.exists():
                state = json.loads(runtime_state_path.read_text())
            else:
                state = {}
            state["training_enabled"] = False
            state["paused_by"] = "custodian"
            state["paused_reason"] = "ethics_quarantine"
            state["paused_at"] = datetime.now().isoformat()
            runtime_state_path.write_text(json.dumps(state, indent=2))
            logger.warning("Training paused for lens '%s' (ethics quarantine)", lens_name)
        except OSError as exc:
            logger.error("Could not pause lens '%s': %s", lens_name, exc)

    def _count_recent_rejections(self, days: int = 7) -> int:
        """Count lines in ethics_rejections.jsonl within the last `days` days."""
        rejection_log = Path(self.mac_root) / "logs" / "ethics_rejections.jsonl"
        if not rejection_log.exists():
            return 0
        cutoff = datetime.now() - timedelta(days=days)
        count = 0
        try:
            with rejection_log.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        ts_str = record.get("timestamp") or record.get("ts") or ""
                        if ts_str:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                count += 1
                        else:
                            count += 1  # malformed timestamp — assume recent
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError as exc:
            logger.warning("Cannot read rejection log: %s", exc)
        return count
