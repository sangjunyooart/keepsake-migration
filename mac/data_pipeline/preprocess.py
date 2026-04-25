"""
Cleaning and chunking of raw corpus items.
Chunks: 1024 tokens, 64-token overlap.
"""
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MAC_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAC_ROOT.parent))

from shared.ethics_filter import EthicsFilter


class Preprocessor:
    def __init__(self, lens_name: str, raw_dir: Path, processed_dir: Path,
                 chunk_size: int = 1024, overlap: int = 64):
        self.lens_name = lens_name
        self.raw_dir = raw_dir / lens_name
        self.processed_dir = processed_dir / lens_name
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.ethics = EthicsFilter()

    def run(self) -> int:
        """Process all unprocessed raw files. Returns total chunk count."""
        processed_stems = {f.stem for f in self.processed_dir.glob("*.txt")}
        new_chunks = 0
        for raw_file in sorted(self.raw_dir.glob("*.json")):
            stem = raw_file.stem
            if any(s.startswith(stem) for s in processed_stems):
                continue
            item = json.loads(raw_file.read_text())
            text = item.get("text", "")
            chunks = self._process(text)
            for i, chunk in enumerate(chunks):
                out = self.processed_dir / f"{stem}_{i:04d}.txt"
                out.write_text(chunk)
                new_chunks += 1
        logger.info("Preprocessed %d new chunks for %s", new_chunks, self.lens_name)
        return new_chunks

    def count_chunks(self) -> int:
        return len(list(self.processed_dir.glob("*.txt")))

    # ------------------------------------------------------------------

    def _process(self, text: str) -> list[str]:
        if not text:
            return []
        text = self._clean(text)
        if not self.ethics.is_safe(text):
            return []
        words = text.split()
        if not words:
            return []
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk = " ".join(words[start:end])
            if len(chunk) > 20:
                chunks.append(chunk)
            if end >= len(words):
                break
            start = end - self.overlap
        return chunks

    def _clean(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)           # strip HTML tags
        text = re.sub(r"\s+", " ", text)                # normalize whitespace
        text = re.sub(r"http\S+", "", text)             # remove URLs
        text = text.strip()
        return text
