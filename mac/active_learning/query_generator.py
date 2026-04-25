"""
Template-based search query generation. No LLM calls.
Each lens type has its own templates.
"""
from dataclasses import dataclass
from typing import List

from mac.active_learning.self_assessment import Gap


TEMPLATES: dict[str, list[str]] = {
    "environmental_time": [
        "{location} climate {period}",
        "{location} weather history {period}",
        "{location} natural disasters {period}",
        "{location} environmental conditions {period}",
        "{location} ecology {period}",
        "{location} seasons {period}",
    ],
    "infrastructure_time": [
        "{period} immigration policy {country}",
        "{period} visa regulation {country}",
        "{period} administrative procedure {country}",
        "{country} bureaucracy {period}",
        "{country} residency permit {period}",
    ],
    "human_time": [
        "{location} daily life {period}",
        "{location} {period} memoir",
        "{location} cultural history {period}",
        "{location} society {period}",
        "{location} generation {period}",
    ],
    "digital_time": [
        "{period} digital media {country}",
        "{period} internet {country}",
        "{period} mobile phone {country}",
        "{country} online culture {period}",
        "{country} technology adoption {period}",
    ],
    "liminal_time": [
        "migration narrative {period}",
        "{country} immigrants {period}",
        "rite of passage {country} {period}",
        "border crossing {country} {period}",
        "diaspora {country} {period}",
    ],
    "more_than_human_time": [
        "{location} natural history {period}",
        "{location} wildlife {period}",
        "{location} ecosystem {period}",
        "{location} biodiversity {period}",
        "{location} geological history",
    ],
}


class QueryGenerator:
    def generate(self, gap: Gap) -> List[str]:
        templates = TEMPLATES.get(gap.lens_type, [])
        queries = []
        for t in templates:
            q = t.format(
                location=gap.location or "",
                period=gap.period or "",
                country=gap.country or "",
            ).strip()
            if q:
                queries.append(q)
        return queries
