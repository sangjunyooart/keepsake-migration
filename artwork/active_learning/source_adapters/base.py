from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Gap:
    period: str
    location: str
    current_coverage: float   # 0.0 (no coverage) → 1.0 (well covered)
    priority: float           # 0.0 (low) → 1.0 (high)
    suggested_topics: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    url: str
    title: str
    content: str
    source: str
    gap_period: str = ""
    gap_location: str = ""
    score: float = 0.5


class SourceAdapter(ABC):
    name: str = "base"
    requires_api_key: bool = False

    @abstractmethod
    def search(self, query: str, gap: Gap) -> List[SearchResult]:
        ...

    @abstractmethod
    def fetch_content(self, result: SearchResult) -> str:
        ...
