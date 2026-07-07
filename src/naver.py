"""네이버 뉴스 검색 API (sort=date)."""
from __future__ import annotations

import html
import logging
import re
from email.utils import parsedate_to_datetime

import requests

from .config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
from .models import Article

log = logging.getLogger(__name__)

API = "https://openapi.naver.com/v1/search/news.json"
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    return html.unescape(_TAG.sub("", s)).strip()


def search(query: str, display: int = 20) -> list[Article]:
    try:
        r = requests.get(
            API,
            params={"query": query, "display": display, "sort": "date"},
            headers={
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            },
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"naver search fail ({query}): {e}")
        return []

    out = []
    for it in r.json().get("items", []):
        try:
            published = parsedate_to_datetime(it["pubDate"])
        except Exception:
            continue
        out.append(Article(
            title=_clean(it["title"]),
            url=it["link"],
            source=_press_name(it.get("originallink", "")),
            published=published,
            origin="naver",
            summary=_clean(it.get("description", "")),
        ))
    return out


def _press_name(originallink: str) -> str:
    """API 가 언론사명을 안 주므로 원문 도메인으로 대충 표기."""
    m = re.search(r"https?://(?:www\.)?([^/]+)", originallink)
    return m.group(1) if m else "네이버뉴스"
