"""
Adapter version format shared between Mac (writer) and Pi (reader).
"""
import json
from pathlib import Path
from datetime import datetime, timezone


VERSION_FILE = "version.json"


def write_version(adapter_dir: Path, lens_name: str, epoch: int, source: str = "") -> dict:
    version = {
        "lens_name": lens_name,
        "epoch": epoch,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    (adapter_dir / VERSION_FILE).write_text(json.dumps(version, indent=2))
    return version


def read_version(adapter_dir: Path) -> dict:
    vfile = adapter_dir / VERSION_FILE
    if not vfile.exists():
        return {}
    return json.loads(vfile.read_text())
