import re
from typing import List


class EthicsFilter:
    """
    Hardcoded keyword block for Masa Ishikawa's name variants.
    Used on Mac (training data filtering) and Pi (output safety check).
    Cannot be bypassed by configuration — this is a structural constraint.
    """

    BLOCKED_KEYWORDS = [
        "Masayoshi Ishikawa",
        "Masa Ishikawa",
        "이시카와 마사요시",
        "石川正義",
    ]

    def __init__(self):
        self._patterns = [
            re.compile(re.escape(kw), re.IGNORECASE)
            for kw in self.BLOCKED_KEYWORDS
        ]

    def is_safe(self, text: str) -> bool:
        """Return True if text contains no blocked name variants."""
        return not any(p.search(text) for p in self._patterns)

    def filter_batch(self, texts: List[str]) -> List[str]:
        """Return only texts that pass the safety check."""
        return [t for t in texts if self.is_safe(t)]

    def scrub(self, text: str) -> str:
        """Replace blocked name variants with [REDACTED]. Use sparingly."""
        result = text
        for p in self._patterns:
            result = p.sub("[REDACTED]", result)
        return result
