import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .base import Check, CheckResult, Severity

logger = logging.getLogger(__name__)

_CHECK_INTERVALS = {
    "human_time": 3600,
    "infrastructure_time": 21600,
    "environmental_time": 43200,
    "digital_time": 300,
    "liminal_time": 86400,
    "more_than_human_time": 86400,
}


class SystemActivityCheck(Check):
    """Check 1: Are all 6 lenses actively cycling?"""

    name = "system_activity"

    def run(self) -> CheckResult:
        warn_mult = self.config.get("thresholds", {}).get(
            "system_activity", {}
        ).get("warning_multiplier", 3.0)
        crit_mult = self.config.get("thresholds", {}).get(
            "system_activity", {}
        ).get("critical_multiplier", 6.0)

        lenses = list(self.lens_configs.get("lenses", {}).keys())
        now = datetime.now()
        lens_status: dict = {}
        all_idle_since: list[datetime] = []

        for lens_name in lenses:
            last_cycle = self._last_cycle_time(lens_name)
            interval = _CHECK_INTERVALS.get(lens_name, 3600)
            lens_status[lens_name] = {
                "last_cycle": last_cycle.isoformat() if last_cycle else None,
                "interval_s": interval,
            }
            if last_cycle:
                age_s = (now - last_cycle).total_seconds()
                lens_status[lens_name]["age_s"] = round(age_s)
                all_idle_since.append(last_cycle)
            else:
                all_idle_since.append(datetime.min)

        # Critical: all lenses idle for 24h
        all_idle_hours = (now - max(all_idle_since)).total_seconds() / 3600 if all_idle_since else 999
        critical_lenses = []
        warning_lenses = []

        for lens_name in lenses:
            age_s = lens_status[lens_name].get("age_s")
            if age_s is None:
                continue  # no data — treat as warning
            interval = _CHECK_INTERVALS.get(lens_name, 3600)
            if age_s > interval * crit_mult:
                critical_lenses.append(lens_name)
            elif age_s > interval * warn_mult:
                warning_lenses.append(lens_name)

        no_data_lenses = [
            n for n in lenses if lens_status[n].get("age_s") is None
        ]

        if critical_lenses or all_idle_hours >= 24:
            summary = (
                f"IDLE: {', '.join(critical_lenses)}"
                if critical_lenses
                else f"All lenses idle for {all_idle_hours:.0f}h"
            )
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=summary,
                details={
                    "critical_lenses": critical_lenses,
                    "warning_lenses": warning_lenses,
                    "no_data_lenses": no_data_lenses,
                    "all_idle_hours": round(all_idle_hours, 1),
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        if warning_lenses or no_data_lenses:
            return CheckResult(
                check_name=self.name,
                severity=Severity.WARNING,
                summary=f"Stale: {', '.join(warning_lenses + no_data_lenses)}",
                details={
                    "warning_lenses": warning_lenses,
                    "no_data_lenses": no_data_lenses,
                    "lens_status": lens_status,
                },
                timestamp=now,
            )

        active_count = sum(
            1 for n in lenses if lens_status[n].get("age_s") is not None
        )
        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            summary=f"All {active_count} lenses active within expected intervals",
            details={"lens_status": lens_status},
            timestamp=now,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _last_cycle_time(self, lens_name: str) -> Optional[datetime]:
        """Try cycle log → decisions log → adapter checkpoint as fallback."""
        cycle_log = Path(self.mac_root) / "logs" / "cycles" / f"{lens_name}.jsonl"
        ts = self._last_timestamp_in_jsonl(cycle_log)
        if ts:
            return ts

        decisions_log = (
            Path(self.mac_root) / "logs" / f"decisions_{lens_name}.jsonl"
        )
        ts = self._last_timestamp_in_jsonl(decisions_log)
        if ts:
            return ts

        current_json = (
            Path(self.mac_root) / "adapters" / lens_name / "current.json"
        )
        if current_json.exists():
            try:
                data = json.loads(current_json.read_text())
                ts_str = data.get("promoted_at") or data.get("created_at") or ""
                if ts_str:
                    return datetime.fromisoformat(ts_str)
            except Exception:
                pass

        return None

    def _last_timestamp_in_jsonl(self, path: Path) -> Optional[datetime]:
        if not path.exists():
            return None
        last_line = None
        try:
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
        except OSError:
            return None
        if not last_line:
            return None
        try:
            record = json.loads(last_line)
            ts_str = record.get("timestamp") or record.get("ts") or ""
            if ts_str:
                return datetime.fromisoformat(ts_str)
        except (json.JSONDecodeError, ValueError):
            pass
        return None
