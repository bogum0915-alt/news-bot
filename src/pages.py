"""중요 뉴스를 기업 페이지 데이터(pages/<page>-news.json)로 축적.

company-pages HTML(예: nvidia.html)이 GitHub raw URL로 이 JSON을 읽는다.
텔레그램 발송(IMPORTANCE_MIN)과 별개로 PAGE_IMPORTANCE_MIN 이상 기사만
쌓이며, 파일당 최신 MAX_ITEMS개 롤링. Actions가 매 실행 후 커밋.

watchlist.yaml 엔트리에 `page: nvda` 처럼 키를 달면 해당 기업이 대상이 됨.
"""
from __future__ import annotations

import json
import logging
from zoneinfo import ZoneInfo

from .config import PAGE_IMPORTANCE_MIN, ROOT
from .models import Article

log = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")
PAGES_DIR = ROOT / "pages"
MAX_ITEMS = 80


def add(a: Article, verdict: dict) -> None:
    """판정(assess) 결과를 받아 page 키가 있는 기업 파일에 축적."""
    if verdict["importance"] < PAGE_IMPORTANCE_MIN:
        return
    for c in a.companies:
        if not getattr(c, "page", ""):
            continue
        path = PAGES_DIR / f"{c.page}-news.json"
        items: list[dict] = []
        if path.exists():
            try:
                items = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                log.warning(f"corrupt page file, resetting: {path.name}")
        if any(it.get("url") == a.url for it in items):
            continue
        items.insert(0, {
            "ts": a.published.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
            "tag": verdict.get("category") or "기타",
            "title": a.title,
            "source": a.source,
            "url": a.url,
            "summary": verdict.get("summary", ""),
            "importance": verdict["importance"],
        })
        PAGES_DIR.mkdir(exist_ok=True)
        path.write_text(
            json.dumps(items[:MAX_ITEMS], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        log.info(f"page+ {c.page} (i={verdict['importance']}): {a.title[:60]}")
