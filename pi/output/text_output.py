"""
Text output module — prints generated lens output to stdout / log.
Primary output mode for pre-exhibition development.
"""
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TextOutput:
    def __init__(self, lens_name: str, log_dir=None):
        self.lens_name = lens_name
        self.log_dir = log_dir

    def emit(self, text: str, metadata: dict | None = None):
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] [{self.lens_name}] {text}"
        print(entry, flush=True)
        logger.info("OUTPUT: %s", text[:120])

        if self.log_dir:
            try:
                import json
                log_file = self.log_dir / f"output_{self.lens_name}.jsonl"
                with open(log_file, "a") as f:
                    f.write(json.dumps({
                        "timestamp": timestamp,
                        "lens": self.lens_name,
                        "text": text,
                        **(metadata or {}),
                    }) + "\n")
            except Exception as e:
                logger.warning("Failed to write output log: %s", e)
