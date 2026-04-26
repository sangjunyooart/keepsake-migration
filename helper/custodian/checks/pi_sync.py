import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

from .base import Check, CheckResult, Severity

logger = logging.getLogger(__name__)

_PI_HOSTS = {
    "human_time": ("pi1.local", 5000),
    "infrastructure_time": ("pi2.local", 5000),
    "environmental_time": ("pi3.local", 5000),
    "digital_time": ("pi4.local", 5000),
    "liminal_time": ("pi5.local", 5000),
    "more_than_human_time": ("pi6.local", 5000),
}


class PiSyncCheck(Check):
    """Check 4: Do all 6 Pis have current adapters?"""

    name = "pi_sync"

    def run(self) -> CheckResult:
        cfg = self.config.get("thresholds", {}).get("pi_sync", {})
        warn_behind = cfg.get("warning_versions_behind", 2)
        crit_unreachable_hours = cfg.get("critical_unreachable_hours", 24)
        crit_consec_failures = cfg.get("critical_consecutive_push_failures", 5)

        lenses = list(self.lens_configs.get("lenses", {}).keys())
        now = datetime.now()
        lens_status: dict = {}
        critical_lenses: list[str] = []
        warning_lenses: list[str] = []

        push_failures = self._load_push_failures()

        for lens_name in lenses:
            mac_version = self._mac_current_version(lens_name)
            mac_count = self._mac_checkpoint_count(lens_name)
            pi_info = self._poll_pi(lens_name)
            push_info = push_failures.get(lens_name, {})

            consecutive_fails = push_info.get("consecutive_failures", 0)
            last_push_ts = push_info.get("last_success")

            status = {
                "mac_version": mac_version,
                "mac_checkpoint_count": mac_count,
                "pi_reachable": pi_info.get("reachable", False),
                "pi_adapter_version": pi_info.get("adapter_version"),
                "consecutive_push_failures": consecutive_fails,
                "last_successful_push": last_push_ts,
            }

            if pi_info.get("reachable"):
                if mac_version and pi_info.get("adapter_version"):
                    pi_count = self._version_count(pi_info["adapter_version"])
                    mac_c = self._version_count(mac_version)
                    if mac_c - pi_count >= warn_behind:
                        warning_lenses.append(lens_name)
                        status["versions_behind"] = mac_c - pi_count
            else:
                # Check how long unreachable
                last_seen_str = push_info.get("last_success")
                if last_seen_str:
                    try:
                        last_seen = datetime.fromisoformat(last_seen_str)
                        hours_unreachable = (now - last_seen).total_seconds() / 3600
                        status["hours_unreachable"] = round(hours_unreachable, 1)
                        if hours_unreachable >= crit_unreachable_hours:
                            critical_lenses.append(lens_name)
                        else:
                            warning_lenses.append(lens_name)
                    except ValueError:
                        warning_lenses.append(lens_name)
                else:
                    warning_lenses.append(lens_name)

            if consecutive_fails >= crit_consec_failures:
                if lens_name not in critical_lenses:
                    critical_lenses.append(lens_name)

            lens_status[lens_name] = status

        if critical_lenses:
            return CheckResult(
                check_name=self.name,
                severity=Severity.CRITICAL,
                summary=f"Critical Pi sync issue: {', '.join(critical_lenses)}",
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
                summary=f"Pi sync warning: {', '.join(warning_lenses)}",
                details={"warning_lenses": warning_lenses, "lens_status": lens_status},
                timestamp=now,
            )

        online = sum(
            1 for v in lens_status.values() if v.get("pi_reachable")
        )
        return CheckResult(
            check_name=self.name,
            severity=Severity.INFO,
            summary=f"Pi sync healthy ({online}/{len(lenses)} reachable, adapters current)",
            details={"lens_status": lens_status},
            timestamp=now,
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _mac_current_version(self, lens_name: str) -> Optional[str]:
        current_json = (
            Path(self.mac_root) / "adapters" / lens_name / "current.json"
        )
        if not current_json.exists():
            return None
        try:
            data = json.loads(current_json.read_text())
            return data.get("tag") or data.get("version")
        except Exception:
            return None

    def _mac_checkpoint_count(self, lens_name: str) -> int:
        adapter_dir = Path(self.mac_root) / "adapters" / lens_name
        if not adapter_dir.exists():
            return 0
        return sum(1 for d in adapter_dir.iterdir() if d.is_dir())

    def _poll_pi(self, lens_name: str) -> dict:
        host, port = _PI_HOSTS.get(lens_name, ("", 5000))
        if not host:
            return {"reachable": False}
        try:
            resp = requests.get(
                f"http://{host}:{port}/status", timeout=3
            )
            resp.raise_for_status()
            data = resp.json()
            adapter_info = data.get("adapter", {})
            return {
                "reachable": True,
                "adapter_version": adapter_info.get("tag") or adapter_info.get("version"),
                "inference_ready": data.get("inference_ready", False),
            }
        except Exception:
            return {"reachable": False}

    def _load_push_failures(self) -> dict:
        push_log = Path(self.mac_root) / "logs" / "push_history.jsonl"
        if not push_log.exists():
            return {}

        lens_data: dict = {}
        try:
            with push_log.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        lens = rec.get("lens_name", "")
                        if not lens:
                            continue
                        if lens not in lens_data:
                            lens_data[lens] = {"consecutive_failures": 0, "last_success": None}

                        if rec.get("success"):
                            lens_data[lens]["consecutive_failures"] = 0
                            lens_data[lens]["last_success"] = rec.get("timestamp")
                        else:
                            lens_data[lens]["consecutive_failures"] += 1
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.warning("Cannot read push history: %s", exc)
        return lens_data

    @staticmethod
    def _version_count(version_str: str) -> int:
        """Extract numeric sequence from version tag for comparison."""
        import re
        m = re.search(r"(\d+)", str(version_str))
        return int(m.group(1)) if m else 0
