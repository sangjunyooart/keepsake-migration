import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from .base import Check, CheckResult, Severity

logger = logging.getLogger(__name__)


class DataFlowCheck(Check):
    """Check 3: Is data entering the system?"""

    name = "data_flow"

    def run(self) -> CheckResult:
        cfg = self.config.get("thresholds", {}).get("data_flow", {})
        warn_days = cfg.get("warning_no_data_days", 7)
        crit_days = cfg.get("critical_no_data_days", 14)

        lenses = list(self.lens_configs.get("lenses", {}).keys())
        now = datetime.now()
        lens_status: dict = {}
        system_last_new_file: list[datetime] = []

        for lens_name in lenses:
            info = self._lens_data_info(lens_name, now)
            lens_status[lens_name] = info
            if info.get("newest_file_time"):
                try:
                    system_last_new_file.append(
                        datetime.fromisoformat(info["newest_file_time"])
                    )
                except ValueError:
                    pass

        # System-wide no-data check
        if system_last_new_file:
            latest = max(system_last_new_file)
            days_since_any = (now - latest).days
        else:
            days_since_any = 9999

        # Detect search dispatch but 0 results
        zero_result_searches = self._check_zero_result_searches(lenses)

        if days_since_any >= crit_days:
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=f"No new data system-wide in {days_since_any}d",
                details={
                    "days_since_any_data": days_since_any,
                    "zero_result_searches": zero_result_searches,
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        has_warning = (
            days_since_any >= warn_days
            or bool(zero_result_searches)
            or any(
                v.get("days_since_new", 0) >= warn_days
                for v in lens_status.values()
            )
        )

        if has_warning:
            return CheckResult(
                check_name=self.name,
                severity=Severity.WARNING,
                summary=(
                    f"Data flow slowing: last new data {days_since_any}d ago"
                    + (f"; {len(zero_result_searches)} zero-result search(es)" if zero_result_searches else "")
                ),
                details={
                    "days_since_any_data": days_since_any,
                    "zero_result_searches": zero_result_searches,
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        total_raw = sum(v.get("raw_count", 0) for v in lens_status.values())
        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            summary=f"Data flowing normally ({total_raw} total raw documents)",
            details={"lens_status": lens_status, "days_since_any_data": days_since_any},
            timestamp=now,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _lens_data_info(self, lens_name: str, now: datetime) -> dict:
        raw_dir = Path(self.mac_root) / "corpus" / "raw" / lens_name
        info: dict = {"lens": lens_name, "raw_count": 0}

        if not raw_dir.exists():
            return info

        files = list(raw_dir.glob("*.json"))
        info["raw_count"] = len(files)

        if not files:
            return info

        newest = max(files, key=lambda f: f.stat().st_mtime)
        newest_dt = datetime.fromtimestamp(newest.stat().st_mtime)
        info["newest_file_time"] = newest_dt.isoformat()
        info["days_since_new"] = (now - newest_dt).days

        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d = now - timedelta(days=7)
        info["new_last_24h"] = sum(
            1 for f in files
            if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff_24h
        )
        info["new_last_7d"] = sum(
            1 for f in files
            if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff_7d
        )

        return info

    def _check_zero_result_searches(self, lenses: list) -> list[str]:
        """Check for active-learning searches that returned 0 results."""
        zero = []
        for lens_name in lenses:
            log_path = (
                Path(self.mac_root) / "logs" / f"active_learning_{lens_name}.jsonl"
            )
            if not log_path.exists():
                continue
            try:
                with log_path.open() as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                            if rec.get("results_count", 1) == 0 and rec.get("query"):
                                zero.append(f"{lens_name}:{rec['query'][:40]}")
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue
        return zero[-10:]  # last 10 at most
