"""
Records which adapter version is deployed to each Pi.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionTracker:
    def __init__(self, mac_root: Path):
        self.log_path = mac_root / "logs" / "push_history.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path = mac_root / "runtime_state" / "pi_versions.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def record_push(self, lens_name: str, pi_hostname: str, adapter_path: Path, success: bool):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lens": lens_name,
            "pi": pi_hostname,
            "adapter": str(adapter_path),
            "success": success,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        if success:
            state = self._load_state()
            state[pi_hostname] = {
                "lens": lens_name,
                "adapter": str(adapter_path),
                "pushed_at": entry["timestamp"],
            }
            self.state_path.write_text(json.dumps(state, indent=2))

    def current_version(self, pi_hostname: str) -> dict:
        state = self._load_state()
        return state.get(pi_hostname, {})

    def all_versions(self) -> dict:
        return self._load_state()

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text())
