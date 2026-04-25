import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CHECK_INTERVALS = {
    "human_time": 3600,
    "infrastructure_time": 21600,
    "environmental_time": 43200,
    "digital_time": 300,
    "liminal_time": 86400,
    "more_than_human_time": 86400,
}


def get_health_status(
    lens_name: str,
    data: dict,
    runtime_state: Optional[dict] = None,
    token_used: int = 0,
) -> str:
    """
    Returns one of: 'healthy', 'warning', 'error', 'disabled'.

    healthy  — Pi online, last training within expected interval, no alerts
    warning  — online but stale training, low token budget, or disk >75%
    error    — Pi unreachable, or >5 consecutive errors in recent decisions
    disabled — training_enabled=false in runtime_state
    """
    if runtime_state and not runtime_state.get("training_enabled", True):
        return "disabled"

    if data.get("error"):
        return "error"

    sys_ = data.get("system", {})

    if sys_.get("disk_percent", 0) > 75:
        return "warning"

    budget = (runtime_state or {}).get("daily_token_budget", 50)
    if token_used > 0 and budget > 0 and (budget - token_used) < 10:
        return "warning"

    check_interval = _CHECK_INTERVALS.get(lens_name, 3600)
    last_training = data.get("training", {}).get("last_training")
    if last_training:
        try:
            dt = datetime.fromisoformat(last_training.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
            if elapsed > 2 * check_interval:
                return "warning"
        except Exception:
            pass

    return "healthy"


def load_runtime_state(lens_name: str, artwork_root: Path) -> Optional[dict]:
    state_file = artwork_root / "runtime_state" / f"{lens_name}.json"
    if not state_file.exists():
        return None
    try:
        with open(state_file) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load runtime state for {lens_name}: {e}")
        return None


def write_runtime_state(lens_name: str, artwork_root: Path, updates: dict) -> bool:
    """
    Merges `updates` into the existing runtime state JSON.
    Returns True on success.
    """
    state_file = artwork_root / "runtime_state" / f"{lens_name}.json"
    try:
        existing = {}
        if state_file.exists():
            with open(state_file) as f:
                existing = json.load(f)
        existing.update(updates)
        existing["last_modified"] = datetime.now(timezone.utc).astimezone().isoformat()
        existing["modified_by"] = "control_panel"
        with open(state_file, "w") as f:
            json.dump(existing, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to write runtime state for {lens_name}: {e}")
        return False


def load_token_usage(lens_name: str, artwork_root: Path) -> int:
    usage_file = artwork_root / "logs" / f"token_usage_{lens_name}.json"
    if not usage_file.exists():
        return 0
    try:
        with open(usage_file) as f:
            data = json.load(f)
        if data.get("date") == str(date.today()):
            return int(data.get("used", 0))
    except Exception:
        pass
    return 0
