"""
Decides when and whether to train a lens.
Reads runtime_state/{lens}.json for training_enabled flag.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MetaController:
    def __init__(self, lens_name: str, lens_config: dict, mac_root: Path):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.mac_root = mac_root
        self.runtime_state_dir = mac_root / "runtime_state"
        self.runtime_state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = mac_root / lens_config["learning"].get("log_dir", "logs")
        self.decisions_log = mac_root / "logs" / f"decisions_{lens_name}.jsonl"
        self.decisions_log.parent.mkdir(parents=True, exist_ok=True)

    def should_train(self, chunk_count: int = 0, corpus_chunk_count: int = 0) -> tuple[bool, str]:
        corpus_chunk_count = chunk_count or corpus_chunk_count
        """
        Return (should_train, reason).
        Checks: training_enabled → min corpus → novelty (if applicable).
        """
        if not self._is_training_enabled():
            return False, "training disabled via control panel"

        lc = self.lens_config["learning"]
        if corpus_chunk_count < lc["min_corpus_chunks"]:
            return False, f"corpus too small ({corpus_chunk_count} < {lc['min_corpus_chunks']})"

        return True, "conditions met"

    def record_decision(self, action: str, reason: str, metadata: Optional[dict] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lens": self.lens_name,
            "action": action,
            "reason": reason,
        }
        if metadata:
            entry.update(metadata)
        with open(self.decisions_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ------------------------------------------------------------------

    def _is_training_enabled(self) -> bool:
        state_file = self.runtime_state_dir / f"{self.lens_name}.json"
        if not state_file.exists():
            self._write_default_state()
            return True
        try:
            data = json.loads(state_file.read_text())
            return data.get("training_enabled", True)
        except Exception:
            return True

    def _write_default_state(self):
        state_file = self.runtime_state_dir / f"{self.lens_name}.json"
        default = {
            "training_enabled": True,
            "lens": self.lens_name,
        }
        state_file.write_text(json.dumps(default, indent=2))
