"""Telegram Bot API sendMessage 래퍼 (stock-bot 패턴)."""
from __future__ import annotations

import html
import logging

import requests

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def escape(s: str) -> str:
    return html.escape(s, quote=False)


def send(text: str) -> bool:
    try:
        r = requests.post(
            f"{API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if r.status_code != 200:
            log.error(f"telegram error {r.status_code}: {r.text[:300]}")
            return False
        return True
    except Exception as e:
        log.error(f"telegram send fail: {e}")
        return False
