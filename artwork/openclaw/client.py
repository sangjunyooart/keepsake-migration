import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

_MODE = os.environ.get("KEEPSAKE_OPENCLAW_MODE", "disabled")


class OpenCLAWClient:
    """
    OpenCLAW SDK wrapper.
    mode='disabled' — all calls no-op (default until OpenCLAW reviewed).
    mode='local'    — HTTP to local LLM server (e.g. Ollama on Pi).
    mode='api'      — HTTP to remote OpenCLAW API.

    Until OpenCLAW's actual API surface is documented, this is a placeholder
    using generic HTTP. Artist reviews after consulting openclaw.ai.
    """

    def __init__(
        self,
        mode: Literal["local", "api", "disabled"] = None,
        config: dict = None,
    ):
        self.mode = (mode or _MODE).lower()
        self.config = config or {}
        self._base_url = self.config.get(
            "url",
            os.environ.get("OPENCLAW_URL", "http://localhost:11434"),
        )
        if self.mode != "disabled":
            logger.info(f"OpenCLAWClient initialized in '{self.mode}' mode at {self._base_url}")

    @property
    def available(self) -> bool:
        return self.mode != "disabled"

    def generate(self, prompt: str, max_tokens: int = 50) -> str:
        if not self.available:
            return ""
        try:
            import requests as _req
            if self.mode == "local":
                resp = _req.post(
                    f"{self._base_url}/api/generate",
                    json={"model": "tinyllama", "prompt": prompt, "max_tokens": max_tokens},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json().get("response", "")
            elif self.mode == "api":
                # Placeholder — update with real OpenCLAW API spec
                resp = _req.post(
                    f"{self._base_url}/generate",
                    json={"prompt": prompt, "max_tokens": max_tokens},
                    headers={"Authorization": f"Bearer {os.environ.get('OPENCLAW_API_KEY', '')}"},
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json().get("text", "")
        except Exception as e:
            logger.warning(f"OpenCLAW generate failed: {e}")
        return ""

    def estimate_tokens(self, prompt: str) -> int:
        return max(1, len(prompt.split()) * 2)
