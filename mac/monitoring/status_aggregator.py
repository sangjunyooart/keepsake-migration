"""
Pulls /status from all 6 Pis in parallel.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

PI_STATUS_PORT = 5000
TIMEOUT = 3


class StatusAggregator:
    def __init__(self, pi_targets: list):
        self.targets = pi_targets  # [{hostname, lens}]

    def fetch_all(self) -> dict:
        """Returns {lens_name: status_dict | None}"""
        results = {}
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(self._fetch_one, t): t for t in self.targets}
            for f in as_completed(futures):
                target = futures[f]
                lens = target["lens"]
                try:
                    results[lens] = f.result()
                except Exception as e:
                    results[lens] = {"error": str(e), "reachable": False}
        return results

    def _fetch_one(self, target: dict) -> dict:
        hostname = target["hostname"]
        try:
            resp = requests.get(
                f"http://{hostname}:{PI_STATUS_PORT}/status",
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                data["reachable"] = True
                data["hostname"] = hostname
                return data
            return {"reachable": False, "hostname": hostname, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"reachable": False, "hostname": hostname, "error": str(e)}
