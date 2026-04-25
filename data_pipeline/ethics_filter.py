import re
import yaml
from pathlib import Path
from typing import List


class EthicsFilter:
    def __init__(self, config_path: str = "config/system_config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        keywords = config["system"]["ethics"]["masa_keywords_block"]
        pattern = "|".join(re.escape(kw) for kw in keywords)
        self._pattern = re.compile(pattern, re.IGNORECASE)

    def is_safe(self, text: str) -> bool:
        return self._pattern.search(text) is None

    def filter_batch(self, texts: List[str]) -> List[str]:
        return [t for t in texts if self.is_safe(t)]

    def report_filtering(self, texts: List[str]) -> dict:
        safe = self.filter_batch(texts)
        filtered_out = len(texts) - len(safe)
        return {
            "total_input": len(texts),
            "safe_output": len(safe),
            "filtered_out": filtered_out,
            "filter_rate": filtered_out / len(texts) if texts else 0.0,
        }


if __name__ == "__main__":
    f = EthicsFilter()

    assert not f.is_safe("Masayoshi Ishikawa was born in Japan.")
    assert not f.is_safe("His friend Masa Ishikawa attended the event.")
    assert not f.is_safe("이시카와 마사요시 씨의 기록.")
    assert not f.is_safe("石川正義 の 旅")
    assert f.is_safe("The seasons change slowly in northern Hokkaido.")
    assert f.is_safe("Migration patterns of the Arctic tern span continents.")

    report = f.report_filtering([
        "Clean text about ecology.",
        "Masayoshi Ishikawa visited Seoul.",
        "Another clean record.",
    ])
    assert report["filtered_out"] == 1
    assert report["safe_output"] == 2

    print("EthicsFilter self-test passed.")
