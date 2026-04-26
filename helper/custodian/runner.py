"""
Custodian runner — runs all 5 checks on schedule, dispatches alerts, writes state.

Entry point: python -m helper.custodian.runner
"""
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml

from .alerts.email_sender import EmailSender
from .alerts.rate_limiter import RateLimiter
from .alerts.telegram_pusher import TelegramPusher
from .checks.base import CheckResult, Severity
from .checks.data_flow import DataFlowCheck
from .checks.ethics_boundary import EthicsBoundaryCheck
from .checks.pi_sync import PiSyncCheck
from .checks.system_activity import SystemActivityCheck
from .checks.training_progress import TrainingProgressCheck

_HERE = Path(__file__).resolve().parent           # helper/custodian/
_REPO_ROOT = _HERE.parent.parent                  # keepsake-migration/
_MAC_ROOT = _REPO_ROOT / "mac"
_STATE_DIR = _HERE / "state"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [custodian] %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class CustodianRunner:
    def __init__(self, mac_root: Path = _MAC_ROOT, state_dir: Path = _STATE_DIR):
        self.mac_root = mac_root
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config()
        self.lens_configs = self._load_lens_configs()

        rate_window = self.config.get("telegram", {}).get(
            "rate_limit_per_critical_type_seconds", 21600
        )
        self._rate_limiter = RateLimiter(self.state_dir, window_seconds=rate_window)
        self._telegram = TelegramPusher(self._rate_limiter)
        self._email = EmailSender()

        self.checks = [
            EthicsBoundaryCheck(mac_root, self.config, self.lens_configs),
            SystemActivityCheck(mac_root, self.config, self.lens_configs),
            TrainingProgressCheck(mac_root, self.config, self.lens_configs),
            DataFlowCheck(mac_root, self.config, self.lens_configs),
            PiSyncCheck(mac_root, self.config, self.lens_configs),
        ]

        self._last_email_date: Optional[str] = None  # YYYY-MM-DD

    # ── main loop ─────────────────────────────────────────────────────────────

    def run_forever(self) -> None:
        logger.info(
            "Custodian starting. mac_root=%s, check_interval=%ds",
            self.mac_root,
            self.config.get("check_interval_seconds", 3600),
        )
        while True:
            try:
                results = self._run_all_checks()
                self._update_state(results)
                self._handle_criticals(results)
                if self._is_email_time():
                    self._send_daily_email(results)
            except Exception:
                logger.exception("Custodian cycle failed — continuing")

            interval = self.config.get("check_interval_seconds", 3600)
            logger.info("Sleeping %ds until next check cycle", interval)
            time.sleep(interval)

    def run_once(self) -> list[CheckResult]:
        """Run all checks once and return results (used in tests / CLI)."""
        results = self._run_all_checks()
        self._update_state(results)
        return results

    # ── check execution ───────────────────────────────────────────────────────

    def _run_all_checks(self) -> list[CheckResult]:
        results = []
        for check in self.checks:
            try:
                result = check.run()
                logger.info(
                    "[%s] %s: %s", check.name, result.severity.value, result.summary
                )
                results.append(result)
            except Exception:
                logger.exception("Check '%s' raised an exception", check.name)
        return results

    # ── state persistence ─────────────────────────────────────────────────────

    def _update_state(self, results: list[CheckResult]) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        worst = self._worst_severity(results)

        current = {
            "timestamp": now_iso,
            "overall_severity": worst.value,
            "checks": {r.check_name: r.to_dict() for r in results},
        }

        try:
            (self.state_dir / "current.json").write_text(
                json.dumps(current, indent=2)
            )
        except OSError as exc:
            logger.error("Failed to write current.json: %s", exc)

        self._append_jsonl(self.state_dir / "history.jsonl", current)

        for result in results:
            if result.severity in (Severity.WARNING, Severity.CRITICAL):
                self._append_jsonl(
                    self.state_dir / "incidents.jsonl", result.to_dict()
                )

    @staticmethod
    def _append_jsonl(path: Path, record: dict) -> None:
        try:
            with path.open("a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as exc:
            logger.error("Failed to append to %s: %s", path, exc)

    # ── alerts ────────────────────────────────────────────────────────────────

    def _handle_criticals(self, results: list[CheckResult]) -> None:
        if not self.config.get("telegram", {}).get("enabled", True):
            return
        for result in results:
            if result.severity == Severity.CRITICAL:
                self._telegram.push_critical(
                    result.check_name, self._format_telegram_message(result)
                )

    def _format_telegram_message(self, result: CheckResult) -> str:
        lines = [result.summary]
        if result.auto_action:
            lines.append(f"\nAction taken: {result.auto_action}")
        details = result.details
        if "leaks" in details:
            for leak in details["leaks"][:3]:
                lines.append(f"  • {Path(leak['path']).name} ({leak['lens']})")
        elif "critical_lenses" in details:
            lines.append(f"Affected: {', '.join(details['critical_lenses'])}")
        return "\n".join(lines)

    # ── email ─────────────────────────────────────────────────────────────────

    def _is_email_time(self) -> bool:
        if not self.config.get("daily_email", {}).get("enabled", True):
            return False
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_email_date == today:
            return False

        email_time_str = self.config.get("daily_email", {}).get("time_of_day", "09:00")
        try:
            h, m = (int(x) for x in email_time_str.split(":"))
        except ValueError:
            h, m = 9, 0
        now = datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if now >= target:
            self._last_email_date = today
            return True
        return False

    def _send_daily_email(self, results: list[CheckResult]) -> None:
        ok = self._email.send_daily_summary(results)
        if ok:
            logger.info("Daily email sent")
        else:
            logger.warning("Daily email not sent (not configured or SMTP error)")

    # ── config loading ────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        config_path = self.mac_root / "config" / "custodian_config.yaml"
        if not config_path.exists():
            logger.warning("custodian_config.yaml not found — using defaults")
            return {}
        try:
            with config_path.open() as f:
                data = yaml.safe_load(f) or {}
            return data.get("custodian", data)
        except Exception as exc:
            logger.error("Failed to load custodian config: %s", exc)
            return {}

    def _load_lens_configs(self) -> dict:
        config_path = self.mac_root / "config" / "lens_configs.yaml"
        if not config_path.exists():
            logger.error("lens_configs.yaml not found at %s", config_path)
            return {"lenses": {}}
        try:
            with config_path.open() as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.error("Failed to load lens configs: %s", exc)
            return {"lenses": {}}

    @staticmethod
    def _worst_severity(results: list[CheckResult]) -> Severity:
        order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
        if not results:
            return Severity.INFO
        return min(results, key=lambda r: order[r.severity]).severity


def main():
    runner = CustodianRunner()
    runner.run_forever()


if __name__ == "__main__":
    main()
