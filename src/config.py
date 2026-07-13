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

# Gemini 중요도 점수(1~5)가 이 값 미만이면 발송 안 함 — 높일수록 엄격
IMPORTANCE_MIN = int(os.environ.get("IMPORTANCE_MIN", "3"))

# 기업 페이지(pages/<page>-news.json)에는 이 점수 이상만 축적 — 텔레그램보다 엄격
PAGE_IMPORTANCE_MIN = int(os.environ.get("PAGE_IMPORTANCE_MIN", "4"))

# 한 사이클에 처리(판정+발송)할 기사 상한 — 기사 폭탄으로 실행이 늘어지는 것 방지.
# 넘친 기사는 seen 처리 안 하므로 다음 사이클이 이어서 처리 (오래된 것부터).
MAX_PER_CYCLE = int(os.environ.get("MAX_PER_CYCLE", "40"))
