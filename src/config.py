import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
NAVER_CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # 없으면 요약 없이 발송

WATCHLIST_PATH = ROOT / "watchlist.yaml"

STATE_FILE = ROOT / "state" / "seen.json"

# 이 시간(분)보다 오래된 기사는 푸시하지 않음 — 봇 재시작 시 과거 기사 폭탄 방지
LOOKBACK_MIN = int(os.environ.get("LOOKBACK_MIN", "60"))
