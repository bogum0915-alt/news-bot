"""텔레그램 채널 릴레이 — 유저 세션으로 다른 채널을 읽어 봇 채널로 재발송.

② digest_channels: 애널리스트가 아침에 올리는 뉴스 모음(URL 3개 이상)을
   항목 단위로 끊어서 개별 발송. 단건 메시지는 무시.
③ forward_channels: 워치리스트 기업이 걸리고 뉴스 링크가 있는 메시지만 재발송.

봇 API 로는 남의 채널을 못 읽으므로 Telethon 유저 세션이 필요하다.
세션은 scripts/make_session.py 로 1회 생성 (⚠️ investment-research 의 세션
파일을 복사하면 안 됨 — 같은 auth key 를 두 곳에서 동시에 쓰면
AUTH_KEY_DUPLICATED 로 양쪽 다 로그아웃된다).

상태는 state/relay.json (채널별 마지막 처리 메시지 id) — seen.json 과 같이
git 커밋으로 실행 간 이어짐. 채널 첫 등장 시엔 seed (기록만, 발송 안 함).

사용법:
  python -m src.relay          한 사이클 수집 → 발송
  python -m src.relay --dry    전송 대신 콘솔 출력
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import yaml

from . import telegram, watchlist
from .config import (
    RELAY_LOOKBACK_MIN,
    RELAY_MAX_PER_CHANNEL,
    RELAY_PATH,
    RELAY_STATE_FILE,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION,
)

log = logging.getLogger("news-bot.relay")

URL_RE = re.compile(r"https?://\S+")
DIGEST_MIN_URLS = 3   # URL 이 이 개수 이상이어야 '뉴스 모음'으로 판정
MAX_LEN = 3500        # 텔레그램 4096 제한 여유


def _load_state() -> dict[str, int]:
    if not RELAY_STATE_FILE.exists():
        return {}
    try:
        return json.loads(RELAY_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(d: dict[str, int]) -> None:
    RELAY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RELAY_STATE_FILE.write_text(
        json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8"
    )


def split_digest(text: str) -> list[str]:
    """뉴스 모음 메시지를 항목 단위로 분할 — URL 이 나온 줄에서 항목이 끝난다.

    [헤더]           ← 첫 항목에 붙어 나감 (따로 안 떼어냄)
    1. 제목 …
    https://…        ← 여기서 항목 종료
    맺음말           ← 마지막 URL 뒤 잔여 텍스트는 버림
    """
    items, buf = [], []
    for line in text.splitlines():
        buf.append(line)
        if URL_RE.search(line):
            item = "\n".join(buf).strip()
            if item:
                items.append(item)
            buf = []
    return items


def _send(text: str, dry: bool) -> bool:
    if dry:
        print("-" * 60)
        print(text)
        return True
    ok = telegram.send(text)
    if ok:
        time.sleep(1)  # rate limit 여유
    return ok


def _handle_digest(label: str, text: str, dry: bool) -> bool:
    """뉴스 모음이면 분할 발송. 전부 성공해야 True (실패 시 다음 사이클 재시도)."""
    if len(URL_RE.findall(text)) < DIGEST_MIN_URLS:
        return True  # 단건 코멘트 — 무시
    for item in split_digest(text):
        msg = f"📮 <b>{telegram.escape(label)}</b>\n{telegram.escape(item[:MAX_LEN])}"
        if not _send(msg, dry):
            return False
    return True


def _handle_forward(wl: watchlist.Watchlist, label: str, username: str,
                    msg_id: int, text: str, dry: bool) -> bool:
    if not URL_RE.search(text):
        return True  # 뉴스 링크 없는 잡담 — 무시
    hits = wl.match(text, text)
    if not hits:
        return True
    tags = " · ".join(c.tag for c in hits[:3])
    body = (
        f"{tags}\n"
        f"{telegram.escape(text[:MAX_LEN])}\n"
        f"— {telegram.escape(label)} (t.me/{username}/{msg_id})"
    )
    return _send(body, dry)


async def _process_channel(client, kind: str, ch: dict, state: dict[str, int],
                           wl: watchlist.Watchlist, dry: bool) -> None:
    username, label = ch["username"], ch.get("label") or ch["username"]
    last_id = state.get(username, 0)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=RELAY_LOOKBACK_MIN)

    msgs = []
    try:
        async for m in client.iter_messages(
            username, min_id=last_id, limit=RELAY_MAX_PER_CHANNEL
        ):
            msgs.append(m)
    except Exception as e:
        log.warning(f"[{label}] fetch fail: {e}")
        return
    if not msgs:
        return

    max_id = max(m.id for m in msgs)
    if last_id == 0:  # 첫 등장 채널 — 기준점만 기록, 발송 안 함
        state[username] = max_id
        log.info(f"[{label}] seeded at message {max_id}")
        return

    handled = 0
    for m in sorted(msgs, key=lambda m: m.id):  # 오래된 것부터
        text = m.message or ""
        if not text.strip() or (m.date and m.date < cutoff):
            state[username] = m.id  # 스킵도 처리로 간주
            continue
        if kind == "digest":
            ok = _handle_digest(label, text, dry)
        else:
            ok = _handle_forward(wl, label, username, m.id, text, dry)
        if not ok:
            log.warning(f"[{label}] send fail at {m.id} — 다음 사이클 재시도")
            return  # state 안 올림 → 이 메시지부터 재시도
        state[username] = m.id
        handled += 1
    if handled:
        log.info(f"[{label}] {handled} messages processed (last_id={max_id})")


async def _run(dry: bool) -> None:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    wl = watchlist.load()
    cfg = yaml.safe_load(RELAY_PATH.read_text(encoding="utf-8")) or {}
    state = _load_state()

    async with TelegramClient(
        StringSession(TELEGRAM_SESSION), int(TELEGRAM_API_ID), TELEGRAM_API_HASH
    ) as client:
        for kind, key in (("digest", "digest_channels"),
                          ("forward", "forward_channels")):
            for ch in cfg.get(key) or []:
                await _process_channel(client, kind, ch, state, wl, dry)

    if not dry:
        _save_state(state)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true", help="전송 대신 콘솔 출력")
    args = p.parse_args()

    if not (TELEGRAM_API_ID and TELEGRAM_API_HASH and TELEGRAM_SESSION):
        log.info("TELEGRAM_API_ID/HASH/SESSION 미설정 — 릴레이 skip")
        return
    asyncio.run(_run(args.dry))


if __name__ == "__main__":
    main()
