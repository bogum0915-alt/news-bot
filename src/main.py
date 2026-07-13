"""AI 밸류체인 뉴스 실시간 푸시 봇.

사용법:
  python -m src.main            한 사이클 수집 → 신규 기사 푸시
  python -m src.main --loop 180 180초마다 반복 (상시 실행)
  python -m src.main --dry      전송 대신 콘솔 출력
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import gnews, naver, noise, pages, store, summarizer, telegram, watchlist
from .config import IMPORTANCE_MIN, LOOKBACK_MIN
from .models import Article

log = logging.getLogger("news-bot")
KST = ZoneInfo("Asia/Seoul")


def collect(wl: watchlist.Watchlist) -> list[Article]:
    """네이버(전 엔트리) + Google News(en_query 있는 기업)에서 수집하고 태깅."""
    by_url: dict[str, Article] = {}

    for c in wl.companies:
        for a in naver.search(c.aliases[0]):
            by_url.setdefault(a.url, a)
        if c.en_query:
            for a in gnews.search(c.en_query):
                if a.url not in by_url and not noise.is_noise(a):
                    a.companies = [c]  # 피드 자체가 기업 검색 결과 → 직접 태깅
                    by_url[a.url] = a
        time.sleep(0.1)  # API 예의

    # 네이버 기사는 제목+요약으로 전 엔트리 재매칭 (한 기사가 여러 기업에 걸릴 수 있음)
    articles = []
    for a in by_url.values():
        if a.origin == "naver":
            a.companies = wl.match(a.title, f"{a.title} {a.summary}")
        if a.companies:
            articles.append(a)
    return articles


def fmt(a: Article, gist: str = "") -> str:
    tags = " · ".join(c.tag for c in a.companies[:3])
    t = a.published.astimezone(KST).strftime("%H:%M")
    body = f"<b>{telegram.escape(a.title)}</b>\n"
    if gist:
        body += f"{telegram.escape(gist)}\n"
    return (
        f"{tags}\n"
        f"{body}"
        f"{telegram.escape(a.source)} · {t}\n"
        f"{a.url}"
    )


def run_once(wl: watchlist.Watchlist, dry: bool = False) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MIN)
    fresh = [
        a for a in collect(wl)
        if a.published >= cutoff and not store.is_seen(a.url)
    ]
    fresh.sort(key=lambda a: a.published)

    # 첫 실행: 쌓여 있던 기사를 전부 쏘지 않고 seen 처리만 (기준점 잡기)
    if store.is_empty() and not dry:
        for a in fresh:
            store.mark(a.url)
        log.info(f"first run: seeded {len(fresh)} articles without sending")
        return

    log.info(f"{len(fresh)} new articles")
    dropped = 0
    for a in fresh:
        v = summarizer.assess(a)
        if v["importance"] < IMPORTANCE_MIN:
            dropped += 1
            if dry:
                print(f'[DROP i={v["importance"]}] {a.title[:70]}')
            else:
                store.mark(a.url)  # 재평가 방지 — 탈락 기사도 기록
            continue
        if dry:
            print("-" * 60)
            print(f'[PUSH i={v["importance"]} cat={v.get("category","")}]')
            print(fmt(a, v["summary"]))
            continue
        if telegram.send(fmt(a, v["summary"])):
            store.mark(a.url)  # 전송 성공 시에만 기록 → 실패하면 다음 사이클 재시도
            pages.add(a, v)    # 기업 페이지 뉴스 축적 (PAGE_IMPORTANCE_MIN 이상만)
            time.sleep(1)  # 텔레그램 rate limit 여유
    if dropped:
        log.info(f"dropped {dropped} low-importance articles")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--loop", type=int, metavar="SEC", help="N초마다 반복 실행")
    p.add_argument("--dry", action="store_true", help="전송 대신 콘솔 출력")
    args = p.parse_args()

    wl = watchlist.load()
    log.info(f"watchlist: {len(wl.companies)} entries")

    if not args.loop:
        run_once(wl, dry=args.dry)
        return
    while True:
        try:
            wl = watchlist.load()  # 루프 중 watchlist.yaml 수정 즉시 반영
            run_once(wl, dry=args.dry)
        except Exception:
            log.exception("cycle failed")
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
