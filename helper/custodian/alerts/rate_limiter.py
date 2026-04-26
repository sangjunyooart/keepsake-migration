import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Prevents repeated Telegram pushes for the same critical type.
    State persisted to disk so it survives runner restarts.
    """

    def __init__(self, state_dir: Path, window_seconds: int = 21600):
        self._state_file = state_dir / "rate_limiter.json"
        self._window = timedelta(seconds=window_seconds)
        self._last_push: dict[str, str] = {}  # check_name → ISO timestamp
        self._load()

    def allow(self, check_name: str) -> bool:
        last_str = self._last_push.get(check_name)
        if last_str:
            try:
                last = datetime.fromisoformat(last_str)
                if datetime.now() - last < self._window:
                    return False
            except ValueError:
                pass
        self._last_push[check_name] = datetime.now().isoformat()
        self._save()
        return True

    def reset(self, check_name: str) -> None:
        self._last_push.pop(check_name, None)
        self._save()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._state_file.exists():
            try:
                self._last_push = json.loads(self._state_file.read_text())
            except Exception as exc:
                logger.warning("Could not load rate limiter state: %s", exc)

    def _save(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self._last_push, indent=2))
        except Exception as exc:
            logger.warning("Could not save rate limiter state: %s", exc)
