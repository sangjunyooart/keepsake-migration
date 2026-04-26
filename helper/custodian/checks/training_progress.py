import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .base import Check, CheckResult, Severity

logger = logging.getLogger(__name__)


class TrainingProgressCheck(Check):
    """Check 2: Is training actually happening?"""

    name = "training_progress"

    def run(self) -> CheckResult:
        cfg = self.config.get("thresholds", {}).get("training_progress", {})
        warn_days = cfg.get("warning_no_training_days", 7)
        crit_days = cfg.get("critical_no_training_days", 14)
        over_train_threshold = cfg.get("over_training_per_hour_threshold", 1)

        lenses = list(self.lens_configs.get("lenses", {}).keys())
        now = datetime.now()
        lens_status: dict = {}
        critical_lenses: list[str] = []
        warning_lenses: list[str] = []

        for lens_name in lenses:
            info = self._lens_info(lens_name)
            lens_status[lens_name] = info

            chunk_count = info.get("corpus_chunks", 0)
            min_chunks = (
                self.lens_configs.get("lenses", {})
                    .get(lens_name, {})
                    .get("learning", {})
                    .get("min_corpus_chunks", 50)
            )
            corpus_sufficient = chunk_count >= min_chunks

            last_ts_str = info.get("last_training")
            if last_ts_str:
                try:
                    last_dt = datetime.fromisoformat(last_ts_str)
                    days_since = (now - last_dt).days
                    info["days_since_training"] = days_since
                    if corpus_sufficient and days_since >= crit_days:
                        critical_lenses.append(lens_name)
                    elif corpus_sufficient and days_since >= warn_days:
                        warning_lenses.append(lens_name)
                except ValueError:
                    pass
            elif corpus_sufficient:
                # Has data but no training at all
                warning_lenses.append(lens_name)

            # Over-training check (>1 checkpoint/hour average)
            cp_count = info.get("checkpoint_count", 0)
            if cp_count > 1 and last_ts_str:
                try:
                    first_dt = self._first_checkpoint_time(lens_name)
                    if first_dt:
                        span_h = max(1.0, (now - first_dt).total_seconds() / 3600)
                        rate = cp_count / span_h
                        info["checkpoint_rate_per_hour"] = round(rate, 3)
                        if rate > over_train_threshold:
                            warning_lenses.append(f"{lens_name}(over-train)")
                except Exception:
                    pass

        if critical_lenses:
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=f"No training in {crit_days}d despite sufficient corpus: {', '.join(critical_lenses)}",
                details={
                    "critical_lenses": critical_lenses,
                    "warning_lenses": warning_lenses,
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        if warning_lenses:
            return CheckResult(
                check_name=self.name,
                severity=Severity.WARNING,
                summary=f"Training attention needed: {', '.join(warning_lenses)}",
                details={
                    "warning_lenses": warning_lenses,
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        total_checkpoints = sum(
            v.get("checkpoint_count", 0) for v in lens_status.values()
        )
        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            summary=f"Training proceeding normally ({total_checkpoints} total checkpoints)",
            details={"lens_status": lens_status},
            timestamp=now,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _lens_info(self, lens_name: str) -> dict:
        mac_root = Path(self.mac_root)
        info: dict = {"lens": lens_name}

        # Corpus chunk count
        processed_dir = mac_root / "corpus" / "processed" / lens_name
        if processed_dir.exists():
            info["corpus_chunks"] = len(list(processed_dir.glob("*.txt")))
        else:
            info["corpus_chunks"] = 0

        # Adapter checkpoint count
        adapter_dir = mac_root / "adapters" / lens_name
        if adapter_dir.exists():
            checkpoints = [
                d for d in adapter_dir.iterdir()
                if d.is_dir() and d.name.startswith("checkpoint_")
            ]
            info["checkpoint_count"] = len(checkpoints)
        else:
            info["checkpoint_count"] = 0

        # Last training from current.json
        current_json = mac_root / "adapters" / lens_name / "current.json"
        if current_json.exists():
            try:
                data = json.loads(current_json.read_text())
                info["last_training"] = data.get("created_at") or data.get("promoted_at")
                info["current_version"] = data.get("tag") or data.get("version")
            except Exception:
                pass

        return info

    def _first_checkpoint_time(self, lens_name: str) -> Optional[datetime]:
        history_json = (
            Path(self.mac_root) / "adapters" / lens_name / "history.json"
        )
        if not history_json.exists():
            return None
        try:
            history = json.loads(history_json.read_text())
            if history:
                first = history[0]
                ts_str = first.get("created_at") or first.get("promoted_at") or ""
                if ts_str:
                    return datetime.fromisoformat(ts_str)
        except Exception:
            pass
        return None
