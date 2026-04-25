"""
NOAA Climate Data Online adapter.
Requires NOAA_API_TOKEN env var. Gracefully returns [] if not set.
"""
import logging
import os
from dataclasses import dataclass
from typing import List

import requests

logger = logging.getLogger(__name__)

CDO_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
TIMEOUT = 15


@dataclass
class SearchResult:
    title: str
    snippet: str
    source: str = "noaa"


class NOAAAdapter:
    def __init__(self):
        self.token = os.environ.get("NOAA_API_TOKEN", "")

    def search(self, query: str, location: str = "", period: str = "") -> List[SearchResult]:
        if not self.token:
            logger.debug("NOAA_API_TOKEN not set — skipping NOAA search")
            return []
        try:
            return self._search_datasets(query, location, period)
        except Exception as e:
            logger.warning("NOAA search failed for '%s': %s", query, e)
            return []

    # ------------------------------------------------------------------

    def _search_datasets(self, query: str, location: str, period: str) -> List[SearchResult]:
        headers = {"token": self.token}
        params = {
            "datasetid": "GHCND",
            "limit": 5,
        }
        if period and "-" in period:
            start_year = period.split("-")[0][:4]
            if start_year.isdigit():
                params["startdate"] = f"{start_year}-01-01"
                params["enddate"] = f"{start_year}-12-31"

        resp = requests.get(f"{CDO_URL}/data", headers=headers, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=f"NOAA GHCND {item.get('station', '')} {item.get('date', '')}",
                snippet=f"value={item.get('value', '')} datatype={item.get('datatype', '')}",
            ))
        return results
