"""보낸 기사 기록 (state/seen.json) — 중복 발송 방지.

JSON 파일로 저장해 git 에 커밋 가능 — GitHub Actions 처럼 매 실행이
새 머신이어도 상태가 이어짐. 7일 지난 기록은 자동 정리.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .config import STATE_FILE

_KEEP_DAYS = 7


def _load() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8"
    )


def is_empty() -> bool:
    return not _load()


def is_seen(url: str) -> bool:
    return url in _load()


def mark(url: str) -> None:
    d = _load()
    d[url] = datetime.now(timezone.utc).isoformat()
    cutoff = datetime.now(timezone.utc) - timedelta(days=_KEEP_DAYS)
    d = {u: t for u, t in d.items()
         if datetime.fromisoformat(t) >= cutoff}
    _save(d)
