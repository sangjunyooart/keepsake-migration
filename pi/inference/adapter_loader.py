"""
Loads the latest LoRA adapter from disk for this Pi's lens.
Watches for new adapters pushed by Mac and signals lens_runtime to reload.
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AdapterLoader:
    def __init__(self, adapter_base: Path, lens_name: str):
        self.adapter_dir = adapter_base / lens_name
        self.lens_name = lens_name
        self._current_path: Optional[Path] = None

    def latest_path(self) -> Optional[Path]:
        """Return path to the most recently pushed adapter, or None."""
        if not self.adapter_dir.exists():
            return None
        # Mac writes current.json to track the active checkpoint
        current_file = self.adapter_dir / "current.json"
        if current_file.exists():
            try:
                data = json.loads(current_file.read_text())
                p = Path(data["path"])
                if p.exists():
                    return p
            except Exception:
                pass
        # Fallback: find newest checkpoint_* directory
        checkpoints = sorted(self.adapter_dir.glob("checkpoint_*"))
        return checkpoints[-1] if checkpoints else None

    def has_new_adapter(self) -> bool:
        """Return True if a newer adapter is available than currently loaded."""
        latest = self.latest_path()
        if latest is None:
            return False
        return latest != self._current_path

    def mark_loaded(self, path: Path):
        self._current_path = path
        logger.info("Adapter marked as loaded: %s", path)

    def current_version_info(self) -> dict:
        path = self._current_path or self.latest_path()
        if not path:
            return {"loaded": False}
        vfile = path / "version.json"
        if vfile.exists():
            try:
                return {**json.loads(vfile.read_text()), "loaded": True, "path": str(path)}
            except Exception:
                pass
        return {"loaded": True, "path": str(path)}
