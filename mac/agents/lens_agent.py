"""
LensAgent — one per temporal lens.

Reads corpus samples, assesses gaps relative to the lens description,
generates Wikipedia search queries. Replaces TF-IDF SelfAssessment.

Ethics: never generates queries targeting Masa's personal information.
All queries target historical, geographical, cultural, environmental context.
"""
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# ── Lens system prompts ───────────────────────────────────────────────────────

_LENS_SYSTEM_PROMPTS = {
    "human_time": """You are the human_time curation agent for an AI art installation called "Keepsake in Every Hair ~ Migration".

Your lens: HUMAN TIME — daily-life rhythms, generational patterns, diaries, memoirs, lived experience of ordinary people across the same geographies and generations as the subject. Focus on collective human temporality, not individual biography.

You curate training data that helps an AI model embody this temporal perspective. You identify what historical and cultural context is missing from the current corpus and generate precise Wikipedia search queries to fill those gaps.

ETHICS CONSTRAINT (absolute): Never generate queries that would return personal biographical information about any specific living or recently deceased individual. Focus exclusively on historical patterns, cultural movements, and collective human experience.""",

    "infrastructure_time": """You are the infrastructure_time curation agent for "Keepsake in Every Hair ~ Migration".

Your lens: INFRASTRUCTURE TIME — the slow time of institutions, bureaucracy, visa regimes, administrative systems, legal frameworks. How states and institutions shape human trajectories through procedural time.

You curate training data capturing how bureaucratic infrastructure operates across Japan, Korea, New York, and relevant migration corridors. Focus on institutional histories, administrative procedures, immigration policy history.

ETHICS CONSTRAINT (absolute): Never generate queries targeting specific individuals' immigration or legal records. Focus on systemic, historical, and policy-level analysis only.""",

    "environmental_time": """You are the environmental_time curation agent for "Keepsake in Every Hair ~ Migration".

Your lens: ENVIRONMENTAL TIME — natural histories, seasonal cycles, climate records, ecological systems of the geographies moved through. The more-than-human temporal backdrop of human migration.

You curate training data about natural and environmental histories of Tokyo, Seoul, New York, and relevant geographic corridors. Focus on climate records, seasonal ecology, urban environmental history.

ETHICS CONSTRAINT (absolute): All queries must focus on environmental and geographical data, not on any individual person's life or location history.""",

    "digital_time": """You are the digital_time curation agent for "Keepsake in Every Hair ~ Migration".

Your lens: DIGITAL TIME — the accelerated temporality of networked media, internet culture, digital infrastructure. How digital systems create their own temporal ecologies distinct from human or natural time.

You curate training data about the history and sociology of digital culture, internet infrastructure development, and networked communication across Japan, Korea, and the US.

ETHICS CONSTRAINT (absolute): Never generate queries about specific individuals' digital activity or online presence. Focus on infrastructural, historical, and sociological analysis.""",

    "liminal_time": """You are the liminal_time curation agent for "Keepsake in Every Hair ~ Migration".

Your lens: LIMINAL TIME — the suspended time of thresholds, migration, in-between states. Airports, border crossings, displacement, the temporal experience of being between worlds.

You curate training data about migration narratives, border crossing experiences, diaspora studies, and the phenomenology of cultural displacement — especially across Japan-Korea-US corridors.

ETHICS CONSTRAINT (absolute): Focus on collective migration experiences and diaspora studies, not any individual's specific migration history.""",

    "more_than_human_time": """You are the more_than_human_time curation agent for "Keepsake in Every Hair ~ Migration".

Your lens: MORE-THAN-HUMAN TIME — geological, cosmological, multispecies, and nonhuman temporalities. The vast timescales within which human life is embedded.

You curate training data about geological history, deep time, multispecies studies, and nonhuman ecological temporalities of the regions relevant to this work.

ETHICS CONSTRAINT (absolute): All queries target nonhuman and geological temporal scales. No personal biographical material.""",
}

_DEFAULT_SYSTEM = """You are a curation agent for "Keepsake in Every Hair ~ Migration", an AI art installation.
Your task: analyze corpus samples and generate precise Wikipedia search queries to fill knowledge gaps.
ETHICS CONSTRAINT: Never generate queries targeting specific individuals' personal information."""


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    lens_name: str
    status: str                        # "complete" | "error" | "no_corpus"
    assessment: str = ""
    gaps: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    model: str = ""
    duration_s: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "lens_name": self.lens_name,
            "status": self.status,
            "assessment": self.assessment,
            "gaps": self.gaps,
            "queries": self.queries,
            "model": self.model,
            "duration_s": self.duration_s,
            "timestamp": self.timestamp,
            "error": self.error,
        }


# ── Agent ─────────────────────────────────────────────────────────────────────

class LensAgent:
    """
    Analyzes corpus for one lens and generates search queries.
    Writes state to mac/runtime_state/agent_{lens}.json after each run.
    """

    def __init__(
        self,
        lens_name: str,
        lens_config: dict,
        mac_root: Path,
        client: OllamaClient,
        n_corpus_samples: int = 15,
        n_raw_titles: int = 10,
    ):
        self.lens_name = lens_name
        self.lens_config = lens_config
        self.mac_root = mac_root
        self.client = client
        self.n_corpus_samples = n_corpus_samples
        self.n_raw_titles = n_raw_titles

        self._state_path = mac_root / "runtime_state" / f"agent_{lens_name}.json"
        self._corpus_dir = mac_root / "corpus" / "processed" / lens_name
        self._raw_dir = mac_root / "corpus" / "raw" / lens_name

    def run(self) -> AgentResult:
        t0 = time.time()
        self._write_state({"status": "running", "timestamp": _now()})
        logger.info("[agent:%s] starting run with model=%s", self.lens_name, self.client.model)

        corpus_samples = self._sample_corpus()
        if not corpus_samples:
            result = AgentResult(
                lens_name=self.lens_name,
                status="no_corpus",
                assessment="No corpus available yet.",
                timestamp=_now(),
                model=self.client.model,
                duration_s=round(time.time() - t0, 2),
            )
            self._write_state(result.to_dict())
            return result

        raw_titles = self._recent_raw_titles()
        prompt = self._build_prompt(corpus_samples, raw_titles)
        system = _LENS_SYSTEM_PROMPTS.get(self.lens_name, _DEFAULT_SYSTEM)

        response = self.client.generate(
            prompt=prompt,
            system=system,
            temperature=0.4,
            max_tokens=800,
            require_json=True,
        )

        elapsed = round(time.time() - t0, 2)

        if not response:
            result = AgentResult(
                lens_name=self.lens_name,
                status="error",
                error="Ollama returned no response",
                timestamp=_now(),
                model=self.client.model,
                duration_s=elapsed,
            )
            self._write_state(result.to_dict())
            return result

        result = AgentResult(
            lens_name=self.lens_name,
            status="complete",
            assessment=response.get("assessment", ""),
            gaps=response.get("gaps", [])[:6],
            queries=self._clean_queries(response.get("queries", [])),
            model=self.client.model,
            duration_s=elapsed,
            timestamp=_now(),
        )

        logger.info(
            "[agent:%s] complete in %.1fs — %d gaps, %d queries",
            self.lens_name, elapsed, len(result.gaps), len(result.queries)
        )
        self._write_state(result.to_dict())
        return result

    # ── prompt builder ────────────────────────────────────────────────────────

    def _build_prompt(self, samples: list[str], raw_titles: list[str]) -> str:
        sample_block = "\n---\n".join(
            f"[chunk {i+1}]\n{s[:400]}" for i, s in enumerate(samples)
        )
        titles_block = (
            "\n".join(f"  - {t}" for t in raw_titles)
            if raw_titles else "  (none yet)"
        )
        lens_display = self.lens_name.replace("_", " ").upper()

        return f"""LENS: {lens_display}
Corpus chunks: {self._count_chunks()}
Recent raw document titles:
{titles_block}

CORPUS SAMPLE ({len(samples)} chunks):
{sample_block}

TASK:
1. Assess the current state of this corpus for the {lens_display} temporal perspective.
2. Identify 3-4 specific knowledge gaps — what historical/cultural/environmental context is missing?
3. Generate 4-6 precise Wikipedia search queries to fill those gaps.

Queries must be:
- Specific enough to find relevant Wikipedia articles
- Focused on historical, geographical, cultural, or environmental context
- In English (Wikipedia search)
- NOT targeting any individual person's biography

Output JSON with exactly these keys:
{{
  "assessment": "2-3 sentence analysis of what the corpus covers and what is missing",
  "gaps": ["gap description 1", "gap description 2", ...],
  "queries": ["Wikipedia search query 1", "Wikipedia search query 2", ...]
}}"""

    # ── corpus helpers ────────────────────────────────────────────────────────

    def _sample_corpus(self) -> list[str]:
        if not self._corpus_dir.exists():
            return []
        chunks = list(self._corpus_dir.glob("*.txt"))
        if not chunks:
            return []
        sampled = random.sample(chunks, min(self.n_corpus_samples, len(chunks)))
        texts = []
        for p in sampled:
            try:
                texts.append(p.read_text(encoding="utf-8", errors="replace").strip())
            except OSError:
                continue
        return [t for t in texts if t]

    def _recent_raw_titles(self) -> list[str]:
        if not self._raw_dir.exists():
            return []
        files = sorted(
            self._raw_dir.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[: self.n_raw_titles]
        titles = []
        for f in files:
            try:
                data = json.loads(f.read_text())
                t = data.get("title") or data.get("source") or ""
                if t:
                    titles.append(t[:80])
            except Exception:
                continue
        return titles

    def _count_chunks(self) -> int:
        if not self._corpus_dir.exists():
            return 0
        return len(list(self._corpus_dir.glob("*.txt")))

    @staticmethod
    def _clean_queries(raw: list) -> list[str]:
        """Ensure queries are non-empty strings, deduplicated, max 6."""
        seen = set()
        clean = []
        for q in raw:
            q = str(q).strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                clean.append(q)
        return clean[:6]

    # ── state ─────────────────────────────────────────────────────────────────

    def _write_state(self, data: dict) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            logger.warning("[agent:%s] could not write state: %s", self.lens_name, exc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
