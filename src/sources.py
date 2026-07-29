"""Google News 결과 언론사 화이트리스트.

지정 언론사(Bloomberg, Reuters, WSJ, FT, NYT, CNBC, The Information)만 통과.
TrendForce/TechCrunch/Tom's Hardware/Wccftech/Hugging Face 는 feeds.py 에서
직접 RSS 로 받으므로 여기 목록에 넣지 않는다 — 같은 기사가 Google News 와
직접 피드 양쪽에서 잡히면 URL 이 달라 seen 으로 못 거르기 때문.
"""
from __future__ import annotations

_ALLOWED = {
    "bloomberg",
    "reuters",
    "cnbc",
    "financial times",
    "the information",
    "the new york times",
    "new york times",
    "the wall street journal",
    "wall street journal",
    "wsj",
}


def allowed(source: str) -> bool:
    s = source.lower().strip()
    s = s.removeprefix("the ").strip()
    return s in _ALLOWED or f"the {s}" in _ALLOWED
