"""
Manages adapter versions: current pointer, history, rollback.
"""
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CURRENT_FILE = "current.json"
HISTORY_FILE = "history.json"


class AdapterManager:
    def __init__(self, adapter_root: Path, keep_history: int = 50):
        self.adapter_root = adapter_root
        self.keep_history = keep_history
        self.adapter_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------

    def current_path(self, lens_name: str) -> Optional[Path]:
        """Return path to the current adapter for a lens, or None."""
        ptr = self._current_file(lens_name)
        if not ptr.exists():
            return None
        data = json.loads(ptr.read_text())
        p = Path(data["path"])
        return p if p.exists() else None

    def promote(self, lens_name: str, checkpoint_path: Path) -> None:
        """Mark a checkpoint as current and append to history."""
        entry = {
            "path": str(checkpoint_path),
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "lens": lens_name,
        }
        # Update current pointer
        self._current_file(lens_name).write_text(json.dumps(entry, indent=2))

        # Append to history
        history = self._load_history(lens_name)
        history.append(entry)
        # Keep only the most recent N
        if len(history) > self.keep_history:
            old_entries = history[: len(history) - self.keep_history]
            history = history[len(history) - self.keep_history :]
            self._prune_old(lens_name, old_entries)
        self._save_history(lens_name, history)
        logger.info("Promoted %s adapter: %s", lens_name, checkpoint_path)

    def rollback(self, lens_name: str) -> Optional[Path]:
        """Roll back to the previous checkpoint. Returns new current path."""
        history = self._load_history(lens_name)
        if len(history) < 2:
            logger.warning("No previous adapter to roll back to for %s", lens_name)
            return None
        history.pop()  # remove current
        prev = history[-1]
        self._save_history(lens_name, history)
        self._current_file(lens_name).write_text(json.dumps(prev, indent=2))
        logger.info("Rolled back %s to %s", lens_name, prev["path"])
        return Path(prev["path"])

    def list_history(self, lens_name: str) -> list:
        return self._load_history(lens_name)

    # ------------------------------------------------------------------

    def _current_file(self, lens_name: str) -> Path:
        lens_dir = self.adapter_root / lens_name
        lens_dir.mkdir(parents=True, exist_ok=True)
        return lens_dir / CURRENT_FILE

    def _load_history(self, lens_name: str) -> list:
        hf = self.adapter_root / lens_name / HISTORY_FILE
        if not hf.exists():
            return []
        return json.loads(hf.read_text())

    def _save_history(self, lens_name: str, history: list) -> None:
        hf = self.adapter_root / lens_name / HISTORY_FILE
        hf.write_text(json.dumps(history, indent=2))

    def _prune_old(self, lens_name: str, entries: list) -> None:
        for entry in entries:
            p = Path(entry["path"])
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                logger.debug("Pruned old adapter checkpoint: %s", p)
