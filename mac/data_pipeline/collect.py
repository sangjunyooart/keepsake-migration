"""
RSS / web ingestion for lens corpora.
Each lens has configurable feed URLs (populated after Masa timeline arrives).
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

# Placeholder feed URLs per lens — replace with real sources once Masa timeline arrives
DEFAULT_FEEDS: dict[str, list[str]] = {
    "human_time": [],
    "infrastructure_time": [],
    "environmental_time": [],
    "digital_time": [],
    "liminal_time": [],
    "more_than_human_time": [],
}


class FeedCollector:
    def __init__(self, lens_name: str, raw_dir: Path, feeds: Optional[list[str]] = None):
        self.lens_name = lens_name
        self.raw_dir = raw_dir / lens_name
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.feeds = feeds or DEFAULT_FEEDS.get(lens_name, [])
        self._seen_hashes = self._load_seen()

    def collect(self) -> int:
        """Fetch all feeds, deduplicate, save new items. Returns count of new items."""
        new_count = 0
        for url in self.feeds:
            try:
                items = self._fetch_feed(url)
                for item in items:
                    h = self._hash(item["text"])
                    if h not in self._seen_hashes:
                        self._save(item, h)
                        self._seen_hashes.add(h)
                        new_count += 1
            except Exception as e:
                logger.warning("Feed fetch failed (%s): %s", url, e)
        logger.info("Collected %d new items for %s", new_count, self.lens_name)
        return new_count

    def add_text(self, text: str, source: str = "manual") -> bool:
        """Directly add a text snippet (from active learning results)."""
        if not text.strip():
            return False
        h = self._hash(text)
        if h in self._seen_hashes:
            return False
        self._save({"text": text, "source": source, "title": ""}, h)
        self._seen_hashes.add(h)
        return True

    # ------------------------------------------------------------------

    def _fetch_feed(self, url: str) -> list[dict]:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries:
            text = entry.get("summary") or entry.get("description") or entry.get("content", [{}])[0].get("value", "")
            title = entry.get("title", "")
            if text:
                items.append({"text": f"{title}\n\n{text}".strip(), "source": url, "title": title})
        return items

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _save(self, item: dict, h: str):
        out = self.raw_dir / f"{h}.json"
        item["saved_at"] = datetime.now(timezone.utc).isoformat()
        out.write_text(json.dumps(item, ensure_ascii=False, indent=2))

    def _load_seen(self) -> set:
        seen = set()
        for f in self.raw_dir.glob("*.json"):
            seen.add(f.stem)
        return seen
