"""
Verifies each Pi is reachable and its status endpoint is responding.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

STATUS_PORT = 5000
TIMEOUT = 5


class PiHealthChecker:
    def __init__(self, pi_targets: list):
        self.targets = pi_targets  # list of {hostname, lens}

    def check_all(self) -> dict[str, dict]:
        """Returns {hostname: {"reachable": bool, "lens": str, "status": dict | None}}"""
        results = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(self._check_one, t): t for t in self.targets}
            for f in as_completed(futures):
                target = futures[f]
                hostname = target["hostname"]
                results[hostname] = f.result()
        return results

    def check_one(self, hostname: str) -> dict:
        target = next((t for t in self.targets if t["hostname"] == hostname), None)
        if not target:
            return {"reachable": False, "lens": "", "status": None, "error": "unknown host"}
        return self._check_one(target)

    # ------------------------------------------------------------------

    def _check_one(self, target: dict) -> dict:
        hostname = target["hostname"]
        lens = target["lens"]
        try:
            resp = requests.get(
                f"http://{hostname}:{STATUS_PORT}/status",
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                return {"reachable": True, "lens": lens, "status": resp.json(), "error": None}
            return {"reachable": False, "lens": lens, "status": None, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"reachable": False, "lens": lens, "status": None, "error": str(e)}
