"""
Minimal Ollama HTTP client.
Requires Ollama running at OLLAMA_BASE_URL (default: http://localhost:11434).
"""
import json
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_DEFAULT_MODEL = os.environ.get(
    "KEEPSAKE_AGENT_MODEL", "qwen2.5:14b-instruct-q4_K_M"
)


class OllamaClient:
    def __init__(
        self,
        base_url: str = _BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.ok
        except Exception:
            return False

    def available_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 800,
        require_json: bool = True,
    ) -> Optional[dict]:
        """
        Call Ollama generate endpoint.
        Returns parsed JSON dict if require_json=True, else raw text in {"text": ...}.
        Returns None on failure.
        """
        payload = {
            "model": model or self.model,
            "prompt": prompt if not system else f"{system}\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if require_json:
            payload["format"] = "json"

        try:
            t0 = time.time()
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            elapsed = time.time() - t0

            raw = resp.json().get("response", "")
            logger.debug("Ollama response in %.1fs: %s...", elapsed, raw[:80])

            if require_json:
                return json.loads(raw)
            return {"text": raw, "elapsed_s": round(elapsed, 2)}

        except json.JSONDecodeError as exc:
            logger.error("Ollama JSON parse failed: %s | raw: %s", exc, raw[:200])
            return None
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            return None
