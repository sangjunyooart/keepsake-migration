import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import feedparser

logger = logging.getLogger(__name__)


class DataCollector:
    def __init__(self, lens_config: dict, corpus_dir: Path):
        self.lens_config = lens_config
        self.corpus_dir = Path(corpus_dir)
        self.lens_name = lens_config.get("name", corpus_dir.name)

        self._raw_dir = self.corpus_dir / "raw" / self.lens_name
        self._raw_dir.mkdir(parents=True, exist_ok=True)

        self._hashes_path = self._raw_dir / "_collected_hashes.json"
        self._seen_hashes = self._load_hashes()

    def _load_hashes(self) -> set:
        if self._hashes_path.exists():
            with open(self._hashes_path, "r") as f:
                return set(json.load(f))
        return set()

    def _save_hashes(self):
        with open(self._hashes_path, "w") as f:
            json.dump(list(self._seen_hashes), f)

    def _hash_content(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def collect_rss(self, source_url: str, max_items: int = 20) -> List[Dict]:
        new_items = []
        try:
            feed = feedparser.parse(source_url)
            for entry in feed.entries[:max_items]:
                content = entry.get("summary", "") or entry.get("title", "")
                if not content:
                    continue
                h = self._hash_content(content)
                if h in self._seen_hashes:
                    continue
                self._seen_hashes.add(h)
                new_items.append({
                    "source": source_url,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "content": content,
                    "url": entry.get("link", ""),
                    "hash": h,
                })
        except Exception as e:
            logger.error(f"RSS collection failed for {source_url}: {e}")
        return new_items

    def collect_all_sources(self) -> List[Dict]:
        all_items = []
        sources = self.lens_config.get("realtime_sources", [])
        for source in sources:
            source_type = source.get("type", "rss")
            if source_type == "rss":
                items = self.collect_rss(source["url"], source.get("max_items", 20))
                all_items.extend(items)
            else:
                logger.warning(f"Source type '{source_type}' not yet implemented, skipping.")
        self._save_hashes()
        return all_items

    def save_batch(self, items: List[Dict]):
        if not items:
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = self._raw_dir / f"batch_{timestamp}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(items)} items to {out_path}")
