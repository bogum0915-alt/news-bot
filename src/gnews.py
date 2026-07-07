"""Google News RSS 영문 검색 피드."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser
import requests

from .models import Article

log = logging.getLogger(__name__)

RSS = "https://news.google.com/rss/search"


def search(query: str) -> list[Article]:
    try:
        r = requests.get(
            RSS,
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"gnews fetch fail ({query}): {e}")
        return []

    out = []
    for e in feedparser.parse(r.content).entries:
        if not e.get("published_parsed"):
            continue
        published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        source = e.get("source", {}).get("title", "")
        title = e.title
        # 구글 뉴스 제목은 "Headline - Publisher" 꼴 — 언론사 중복 제거
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        out.append(Article(
            title=title.strip(),
            url=e.link,
            source=source or "Google News",
            published=published,
            origin="gnews",
        ))
    return out
