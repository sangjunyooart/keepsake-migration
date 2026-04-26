"""
Seed initial corpus for all 6 lenses using Wikipedia search.
Runs before Masa's timeline arrives — uses lens-appropriate historical queries
based on known trajectory anchors (Japan, Tokyo, New York).

Run from keepsake-migration/:
  python -m mac.scripts.seed_corpus
  python -m mac.scripts.seed_corpus environmental_time   # single lens
"""
import sys
import logging
from pathlib import Path

MAC_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = MAC_ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

from mac.active_learning.source_adapters.wikipedia_adapter import WikipediaAdapter
from mac.data_pipeline.collect import FeedCollector
from mac.data_pipeline.preprocess import Preprocessor
from shared.ethics_filter import EthicsFilter

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed queries per lens
# Anchored to Masa's known trajectory: Japan (childhood/youth/university),
# New York (early career migration), Korea (connections).
# Queries are lens-type-specific — not about Masa personally.
# ---------------------------------------------------------------------------

SEED_QUERIES: dict[str, list[str]] = {
    "human_time": [
        "Tokyo daily life 1980s 1990s",
        "Japan Showa Heisei era youth culture",
        "Setagaya Tokyo neighborhood history",
        "Tokyo university student life 2000s",
        "New York immigrant daily life 2000s",
        "Japan generational memory oral history",
        "Korean Japanese diaspora daily experience",
        "New York artist community 2000s",
        "Tokyo commuter culture history",
        "Japan domestic life changing society 1990s",
    ],
    "infrastructure_time": [
        "Japan immigration policy foreigners 2000s",
        "United States O-1 visa artist performer",
        "Japan residence card zairyu card system",
        "New York immigration bureaucracy history",
        "Japan administrative procedure alien registration",
        "United States immigration reform 2000s",
        "Japan visa regulation cultural activities",
        "New York city administration immigrant services",
        "Japan legal residency foreign national process",
        "South Korea immigration policy history",
    ],
    "environmental_time": [
        "Tokyo climate seasons history",
        "Japan natural disasters 1990s earthquake",
        "Setagaya Tokyo parks river ecology",
        "New York weather climate history 2000s",
        "Japan Kanto plain environmental history",
        "Tokyo urban heat island environmental change",
        "New York Hudson River ecology history",
        "Japan Pacific coast climate ocean current",
        "Seoul Korea climate seasonal history",
        "Japan Great Hanshin earthquake 1995 environment",
    ],
    "digital_time": [
        "Japan internet history 1990s 2000s",
        "Japanese digital culture bulletin board 2channel",
        "Tokyo technology adoption mobile phone 2000s",
        "New York digital media art 2000s",
        "Japan broadband internet expansion history",
        "Japanese video game culture 1990s",
        "New York social media early internet culture",
        "Japan mobile internet i-mode history",
        "South Korea internet broadband history 2000s",
        "digital art new media Japan United States",
    ],
    "liminal_time": [
        "Japanese diaspora New York artists",
        "Japan emigration artists performers abroad",
        "cultural identity migration Japan America",
        "transnational experience artist Japan United States",
        "border crossing immigration experience narrative",
        "Japan returnee kikokushijo experience",
        "New York artist visa immigration story",
        "liminality migration anthropology",
        "Japan cultural exchange program United States",
        "diaspora identity homeland belonging narrative",
    ],
    "more_than_human_time": [
        "Tokyo urban ecology wildlife birds",
        "Japan geological history tectonics",
        "Setagaya Tama river ecosystem fish",
        "New York Central Park urban ecology history",
        "Japan biodiversity endemic species",
        "Tokyo rivers waterways history ecology",
        "Japan forest history satoyama landscape",
        "New York harbor marine ecology history",
        "Japan seasonal nature phenology cherry blossom",
        "multispecies cohabitation urban Japan",
    ],
}


def seed_lens(
    lens_name: str,
    mac_root: Path,
    queries_per_lens: int = 5,
    results_per_query: int = 3,
) -> int:
    """
    Seed one lens corpus via Wikipedia. Returns total chunk count after seeding.
    """
    raw_dir = mac_root / "corpus" / "raw"
    processed_dir = mac_root / "corpus" / "processed"

    wiki = WikipediaAdapter()
    collector = FeedCollector(lens_name, raw_dir)
    ethics = EthicsFilter()

    queries = SEED_QUERIES.get(lens_name, [])[:queries_per_lens]
    added = 0

    for query in queries:
        results = wiki.search(query, max_results=results_per_query)
        for r in results:
            content = wiki.fetch_content(r, max_chars=3000)
            if not content:
                continue
            if not ethics.is_safe(content):
                logger.debug("Ethics filter dropped: %s", r.title)
                continue
            text = f"{r.title}\n\n{content}"
            if collector.add_text(text, source=f"wikipedia:{r.title}"):
                added += 1
                logger.info("  + %s", r.title)

    # Preprocess into chunks
    preprocessor = Preprocessor(lens_name, raw_dir, processed_dir, chunk_size=512, overlap=32)
    preprocessor.run()
    chunk_count = preprocessor.count_chunks()

    logger.info(
        "[%s] seeded %d new texts → %d total chunks",
        lens_name, added, chunk_count,
    )
    return chunk_count


def main():
    mac_root = MAC_ROOT

    target_lenses = sys.argv[1:] if len(sys.argv) > 1 else list(SEED_QUERIES.keys())

    print(f"\nSeeding corpus for: {', '.join(target_lenses)}\n")
    total = 0
    for lens_name in target_lenses:
        if lens_name not in SEED_QUERIES:
            print(f"Unknown lens: {lens_name}")
            continue
        print(f"── {lens_name}")
        chunks = seed_lens(lens_name, mac_root)
        total += chunks

    print(f"\nDone. Total chunks across all lenses: {total}")
    print("Run training when chunk counts exceed min_corpus_chunks (50 per lens).")


if __name__ == "__main__":
    main()
