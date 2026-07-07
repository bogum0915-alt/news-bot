"""봇 토큰으로 chat_id 알아내기.

사전 조건: 텔레그램에서 봇에게 아무 메시지나 하나 보내둘 것.
사용법: python scripts/get_chat_id.py
"""
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    sys.exit(".env 에 TELEGRAM_BOT_TOKEN 먼저 채워주세요")

r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15)
updates = r.json().get("result", [])
if not updates:
    sys.exit("업데이트 없음 — 텔레그램에서 봇에게 메시지를 먼저 보내고 다시 실행")

for u in updates:
    chat = (u.get("message") or u.get("channel_post") or {}).get("chat", {})
    if chat:
        print(f"chat_id: {chat['id']}  ({chat.get('type')}, {chat.get('title') or chat.get('first_name')})")
