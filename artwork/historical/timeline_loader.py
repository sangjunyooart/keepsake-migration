import logging
from pathlib import Path
from typing import List, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_TIMELINE_PATH = Path(__file__).parent / "masa_timeline.yaml"


def load_timeline(path: Optional[Path] = None) -> List[Dict]:
    """
    Loads Masa's spatiotemporal timeline from YAML.
    Returns list of period dicts: {period, location, context, visa_status}.
    Falls back to empty list on any error so callers degrade gracefully.
    """
    target = Path(path) if path else _DEFAULT_TIMELINE_PATH
    if not target.exists():
        logger.warning(f"Timeline file not found: {target}")
        return []
    try:
        with open(target, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        entries = data.get("masa_timeline", []) or []
        logger.debug(f"Loaded {len(entries)} timeline entries from {target}")
        return entries
    except Exception as e:
        logger.error(f"Failed to load timeline from {target}: {e}")
        return []
