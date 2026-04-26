import logging
import os

import requests

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class TelegramPusher:
    """Send critical alerts to the artist via Telegram Bot API."""

    def __init__(self, rate_limiter: RateLimiter):
        self.token = os.environ.get("KEEPSAKE_TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.environ.get("KEEPSAKE_TELEGRAM_CHAT_ID", "")
        self.rate_limiter = rate_limiter
        if not self.token or not self.chat_id:
            logger.warning(
                "Telegram not configured (KEEPSAKE_TELEGRAM_BOT_TOKEN / "
                "KEEPSAKE_TELEGRAM_CHAT_ID not set); criticals will not push"
            )

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def push_critical(self, check_name: str, message: str) -> bool:
        if not self.configured:
            return False
        if not self.rate_limiter.allow(check_name):
            logger.info("Telegram suppressed by rate limiter: %s", check_name)
            return False
        return self._send(f"[Keepsake CRITICAL]\n{message}")

    def send_test(self) -> bool:
        """Test connectivity without rate limiter."""
        if not self.configured:
            logger.error("Telegram not configured — cannot send test message")
            return False
        return self._send(
            "[Keepsake] Test message from Custodian.\n"
            "If you see this, Telegram alerts are working correctly."
        )

    def _send(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if resp.ok:
                return True
            logger.error("Telegram API error %s: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as exc:
            logger.error("Telegram push failed: %s", exc)
            return False


if __name__ == "__main__":
    # python -m helper.custodian.alerts.telegram_pusher --test
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / "mac" / ".env")

    state_dir = Path(__file__).resolve().parent.parent / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    limiter = RateLimiter(state_dir, window_seconds=0)  # no rate limit in test
    pusher = TelegramPusher(limiter)
    ok = pusher.send_test()
    print("Test message sent successfully." if ok else "Test failed — check KEEPSAKE_TELEGRAM_* env vars.")
