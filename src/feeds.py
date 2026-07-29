"""언론사 직접 RSS 피드 — Google News 가 잘 못 잡는 전문지.

피드 전체 기사를 받아 watchlist 매칭으로 우리 기업 기사만 남긴다.
(Google News 연동 언론사는 sources.py 화이트리스트 담당)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import requests

from .models import Article
from .watchlist import Watchlist

log = logging.getLogger(__name__)

FEEDS = {
    "TrendForce": "https://www.trendforce.com/news/feed",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Tom's Hardware": "https://www.tomshardware.com/feeds/all",
    "Wccftech": "https://wccftech.com/feed/",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
}

_UA = {"User-Agent": "Mozilla/5.0 (news-bot RSS reader)"}


def _fetch(name: str, url: str) -> list[Article]:
    try:
        r = requests.get(url, headers=_UA, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"feed fetch fail ({name}): {e}")
        return []

    out = []
    for e in feedparser.parse(r.content).entries:
        ts = e.get("published_parsed") or e.get("updated_parsed")
        if not ts or not e.get("link"):
            continue
        out.append(Article(
            title=e.get("title", "").strip(),
            url=e.link,
            source=name,
            published=datetime(*ts[:6], tzinfo=timezone.utc),
            origin="feed",
            summary=e.get("summary", "")[:500],
        ))
    return out


def collect(wl: Watchlist) -> list[Article]:
    """전 피드 수집 후 watchlist 에 걸리는 기사만 태깅해 반환."""
    articles = []
    for name, url in FEEDS.items():
        for a in _fetch(name, url):
            a.companies = wl.match(a.title, f"{a.title} {a.summary}")
            if a.companies:
                articles.append(a)
    return articles
