"""영문 뉴스 노이즈 필터 — 주식 찌라시/자동생성 기사 제거.

Google News 는 기업명 검색 시 MarketBeat/Moomoo 류의 자동생성 주식 스팸을
대량으로 끌어옴. 실제 밸류체인 뉴스만 남기려면 소스 + 제목 패턴으로 거른다.
"""
from __future__ import annotations

import re

from .models import Article

# 자동생성 주식 스팸 소스 (제목 무관 전부 차단)
SPAM_SOURCES = {
    "marketbeat", "moomoo", "tipranks", "insider monkey", "simply wall st",
    "defense world", "etf daily news", "american banking news", "the cerbat gem",
    "marketbeat.com", "zolmax", "modern readers", "the markets daily",
    "wall street pit", "invezz", "stocktitan", "stocktwits", "benzinga",
    "the motley fool", "motley fool", "24/7 wall st.", "24/7 wall st",
    "gurufocus", "guru focus", "zacks", "zacks investment research",
}

# 제목에 이 패턴이 있으면 차단 (주식 트레이딩/공시 노이즈)
_SPAM_RE = re.compile(
    r"\b("
    r"price target|insider|sold shares|shares worth|sec filing|"
    r"grows? position|sells? position|boosts? position|reduces? position|"
    r"trims? (?:stake|position|holdings)|acquires? \d|has \$[\d.]+ (?:million|billion)|"
    r"pension fund|hedge fund|stake in|shares? (?:of|sold|bought)|"
    r"buy the dip|should you buy|is it time to buy|still a buy|a buy after|"
    r"stocks? to buy|stock to buy|buy now|top \w+ stock|best \w+ stock|"
    r"stock split|why .{0,30}\bstock\b (?:is|jumped|soared|fell|dropped|climbing)|"
    r"(?:raises|lowers|cuts|reiterates|maintains|reaffirms|initiates) .{0,15}(?:target|rating)|"
    r"(?:upgraded|downgraded) (?:to|by)|analyst (?:rating|estimate|call)s?|"
    r"why .{0,30}\bstock\b (?:is|jumped|soared|fell|dropped|plummeted|plunged|surged|sank|tumbled|rose|slid|gained|rallied|climbing)|"
    r"average rating|consensus (?:rating|estimate|target)|"
    r"52[- ]week|market cap of|dividend|short interest|"
    r"price[- ]to[- ]earnings|p/e ratio|earnings per share"
    r")\b",
    re.IGNORECASE,
)


def is_noise(a: Article) -> bool:
    if a.origin != "gnews":
        return False
    if a.source.lower().strip() in SPAM_SOURCES:
        return True
    return _SPAM_RE.search(a.title) is not None
