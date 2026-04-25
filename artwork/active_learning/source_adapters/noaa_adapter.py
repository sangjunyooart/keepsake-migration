import logging
import os
from typing import List

import requests

from active_learning.source_adapters.base import Gap, SearchResult, SourceAdapter

logger = logging.getLogger(__name__)

_CDO_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
_TIMEOUT = 15


class NOAAAdapter(SourceAdapter):
    """
    NOAA Climate Data Online (CDO) adapter.
    Requires NOAA_API_TOKEN env var. Gracefully returns empty results if not set.
    Free token: https://www.ncdc.noaa.gov/cdo-web/token
    """

    name = "noaa"
    requires_api_key = True

    def __init__(self):
        self._token = os.environ.get("NOAA_API_TOKEN", "")

    def _available(self) -> bool:
        if not self._token:
            logger.debug("NOAA_API_TOKEN not set — NOAA adapter inactive")
            return False
        return True

    def search(self, query: str, gap: Gap) -> List[SearchResult]:
        if not self._available():
            return []
        parts = gap.period.split("-")
        start_year = parts[0].strip() if parts else "2000"
        end_year = parts[-1].strip() if len(parts) > 1 else start_year
        if end_year == "present":
            end_year = "2026"
        try:
            resp = requests.get(
                f"{_CDO_BASE}/data",
                params={
                    "datasetid": "GHCND",
                    "startdate": f"{start_year}-01-01",
                    "enddate": f"{end_year}-12-31",
                    "limit": 5,
                    "units": "metric",
                },
                headers={"token": self._token},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            items = resp.json().get("results", [])
            results = []
            for item in items:
                results.append(SearchResult(
                    url=f"{_CDO_BASE}/data?datasetid=GHCND&station={item.get('station', '')}",
                    title=f"NOAA climate record {item.get('date', '')} — {item.get('datatype', '')}",
                    content=(
                        f"Station: {item.get('station', '')} | "
                        f"Date: {item.get('date', '')} | "
                        f"Type: {item.get('datatype', '')} | "
                        f"Value: {item.get('value', '')} | "
                        f"Attributes: {item.get('attributes', '')}"
                    ),
                    source=self.name,
                    gap_period=gap.period,
                    gap_location=gap.location,
                ))
            return results
        except Exception as e:
            logger.warning(f"NOAA search failed for gap {gap.period}/{gap.location}: {e}")
            return []

    def fetch_content(self, result: SearchResult) -> str:
        return result.content
