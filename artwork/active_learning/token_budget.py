import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_LENS_DEFAULT_BUDGETS = {
    "human_time": 50,
    "infrastructure_time": 50,
    "environmental_time": 50,
    "digital_time": 100,
    "liminal_time": 30,
    "more_than_human_time": 30,
}


class TokenBudgetEnforcer:
    """
    Tracks and enforces per-lens daily token budget.
    Budget ceiling is read from artwork/runtime_state/{lens}.json each time it's needed
    so control-panel changes take effect without restart.
    Usage is persisted in artwork/logs/token_usage_{lens}.json.
    """

    def __init__(self, lens_name: str, log_dir: Path):
        self.lens_name = lens_name
        self._usage_file = Path(log_dir) / f"token_usage_{lens_name}.json"
        self._state_file = Path("runtime_state") / f"{lens_name}.json"
        self._usage: dict = self._load_usage()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load_usage(self) -> dict:
        if self._usage_file.exists():
            try:
                with open(self._usage_file) as f:
                    data = json.load(f)
                if data.get("date") == str(date.today()):
                    return data
            except Exception:
                pass
        return {"date": str(date.today()), "used": 0}

    def _save_usage(self):
        self._usage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._usage_file, "w") as f:
            json.dump(self._usage, f)

    def _reset_if_new_day(self):
        today = str(date.today())
        if self._usage.get("date") != today:
            self._usage = {"date": today, "used": 0}
            self._save_usage()

    # ── budget ceiling ────────────────────────────────────────────────────────

    def _daily_budget(self) -> int:
        try:
            if self._state_file.exists():
                with open(self._state_file) as f:
                    state = json.load(f)
                return int(state.get("daily_token_budget",
                                    _LENS_DEFAULT_BUDGETS.get(self.lens_name, 50)))
        except Exception as e:
            logger.warning(f"Could not read token budget from runtime state: {e}")
        return _LENS_DEFAULT_BUDGETS.get(self.lens_name, 50)

    # ── public API ────────────────────────────────────────────────────────────

    def request(self, estimated_tokens: int) -> bool:
        """Deduct tokens if budget allows. Returns True if approved."""
        self._reset_if_new_day()
        budget = self._daily_budget()
        if budget == 0:
            return False
        if self._usage["used"] + estimated_tokens > budget:
            logger.debug(
                f"{self.lens_name}: budget request denied "
                f"({self._usage['used']} + {estimated_tokens} > {budget})"
            )
            return False
        self._usage["used"] += estimated_tokens
        self._save_usage()
        return True

    def remaining_today(self) -> int:
        self._reset_if_new_day()
        return max(0, self._daily_budget() - self._usage["used"])

    def used_today(self) -> int:
        self._reset_if_new_day()
        return self._usage.get("used", 0)

    def reset_daily(self):
        self._usage = {"date": str(date.today()), "used": 0}
        self._save_usage()
