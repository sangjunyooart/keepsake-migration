"""
Generate a minimal test corpus for environmental_time.
Use for development before Masa's timeline arrives.
Run from keepsake-migration/: python -m mac.scripts.seed_corpus
"""
import sys
from pathlib import Path

MAC_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_TEXTS = [
    "Tokyo experiences four distinct seasons. Spring brings cherry blossoms in March and April. "
    "Summers are hot and humid with temperatures reaching 35°C. Autumn is mild with colorful foliage. "
    "Winters are cold but rarely snowy in central Tokyo.",

    "The Japanese archipelago sits at the intersection of multiple tectonic plates, making it "
    "one of the most seismically active regions on Earth. Major earthquakes have shaped the "
    "landscape and influenced construction practices throughout modern history.",

    "Setagaya ward in western Tokyo is known for its residential character and extensive park network. "
    "Showa period development transformed former agricultural land into dense urban neighborhoods. "
    "The ward retains traces of village boundaries visible in its irregular street patterns.",

    "New York City's climate in the late twentieth century was characterized by cold winters "
    "and warm humid summers. The urban heat island effect raises temperatures compared to "
    "surrounding regions. Significant snowfall events occur on average several times per winter.",

    "The East Asian monsoon system determines precipitation patterns across Japan, Korea, and "
    "eastern China. Summer rainfall peaks correspond with rice cultivation cycles maintained "
    "for over two thousand years across the region.",

    "Korean Peninsula experiences a temperate climate with four distinct seasons. The winter "
    "months bring cold, dry air masses from Siberia. Spring and autumn are brief transition "
    "periods with mild temperatures and variable rainfall.",
]


def seed(lens_name: str = "environmental_time", count: int = 6):
    raw_dir = MAC_ROOT / "corpus" / "raw" / lens_name
    raw_dir.mkdir(parents=True, exist_ok=True)

    import hashlib
    import json
    from datetime import datetime, timezone

    written = 0
    for i, text in enumerate(SAMPLE_TEXTS[:count]):
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        out = raw_dir / f"{h}.json"
        if not out.exists():
            out.write_text(json.dumps({
                "text": text,
                "source": "seed_corpus",
                "title": f"seed_{i:02d}",
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2))
            written += 1
    print(f"Seeded {written} texts into {raw_dir}")


if __name__ == "__main__":
    lens = sys.argv[1] if len(sys.argv) > 1 else "environmental_time"
    seed(lens)
