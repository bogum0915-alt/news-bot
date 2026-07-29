"""GitHub Actions 릴레이용 텔레그램 유저 세션 생성 — 로컬에서 1회 실행.

⚠️ investment-research 의 세션 파일을 복사해 쓰면 안 된다. 같은 auth key 를
로컬 수집기와 Actions 두 곳에서 동시에 쓰면 AUTH_KEY_DUPLICATED 로 양쪽 다
로그아웃된다. 반드시 여기서 새로 로그인해 별도 세션을 만들 것.

사전 준비: .env 에 TELEGRAM_API_ID, TELEGRAM_API_HASH
  (investment-research/.env 의 값 그대로 복사 — api_id 공유는 문제 없음)

실행: python scripts/make_session.py
  → 전화번호(+82...) / 텔레그램 앱으로 온 코드 입력
  → session_string.txt 생성 (.gitignore 됨)

Secrets 등록 (PowerShell):
  Get-Content session_string.txt | gh secret set TELEGRAM_SESSION --repo bogum0915-alt/news-bot
등록 후 session_string.txt 는 삭제할 것.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


async def main() -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()  # 전화번호 / 코드 / (2단계 비밀번호) 프롬프트
    s = client.session.save()
    await client.disconnect()

    out = ROOT / "session_string.txt"
    out.write_text(s, encoding="utf-8")
    print(f"\n세션 문자열 저장 완료: {out}")
    print("등록: Get-Content session_string.txt | gh secret set TELEGRAM_SESSION --repo bogum0915-alt/news-bot")
    print("등록 후 session_string.txt 는 삭제하세요.")


if __name__ == "__main__":
    asyncio.run(main())
