import json
import logging
import re
from pathlib import Path
from typing import Dict, List

from data_pipeline.ethics_filter import EthicsFilter

logger = logging.getLogger(__name__)


class Preprocessor:
    def __init__(self, ethics_filter: EthicsFilter, chunk_size: int = 1024, chunk_overlap: int = 64):
        self.ethics_filter = ethics_filter
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def chunk_text(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            if len(chunk_words) >= 50:
                chunks.append(" ".join(chunk_words))
            start += self.chunk_size - self.chunk_overlap
        return chunks

    def process_raw_batch(self, raw_file: Path, output_dir: Path) -> Dict:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        raw_items = []
        with open(raw_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    raw_items.append(json.loads(line))

        total_items = len(raw_items)
        safe_items = 0
        total_chunks = 0

        out_path = output_dir / (raw_file.stem + "_processed.jsonl")
        with open(out_path, "w", encoding="utf-8") as out_f:
            for item in raw_items:
                content = item.get("content", "")
                if not self.ethics_filter.is_safe(content):
                    continue
                safe_items += 1
                cleaned = self.clean_text(content)
                chunks = self.chunk_text(cleaned)
                for i, chunk in enumerate(chunks):
                    record = {
                        "text": chunk,
                        "source": item.get("source", ""),
                        "collected_at": item.get("collected_at", ""),
                        "chunk_index": i,
                        "parent_hash": item.get("hash", ""),
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    total_chunks += 1

        logger.info(f"Processed {raw_file.name}: {safe_items}/{total_items} safe, {total_chunks} chunks")
        return {
            "total_items": total_items,
            "safe_items": safe_items,
            "total_chunks": total_chunks,
        }
