"""Gemini로 기사 1~3줄 요약 (~음/함 톤). 영문 기사는 한글 번역 겸함."""
from __future__ import annotations

import logging

from google import genai

from .config import GEMINI_API_KEY
from .models import Article

log = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL = "gemini-2.5-flash"

PROMPT = """아래는 뉴스 기사의 제목과 발췌야. AI 밸류체인 투자자 관점에서 핵심만 1~3줄로 요약해.

제목: {title}
발췌: {snippet}
언론사: {source}

규칙:
- 1~3줄, 각 줄 60자 이내. 줄바꿈으로 구분.
- 제공된 제목/발췌에 있는 사실만. 없는 내용 추측·과장 금지.
- 영문 기사면 한국어로 번역해서 요약.
- 모든 문장 반말·축약형 ~음/함/됐음/했음/임 어미. 메모 톤.
  좋은 예: "TSMC가 CoWoS 캐파 2배 증설 발표했음"
  나쁜 예: "...입니다", "...합니다"
- 발췌가 부실해서 요약할 내용이 제목뿐이면 제목을 한 줄로 옮기기만 함.
- 다른 텍스트 없이 요약문만 출력."""


def summarize(a: Article) -> str:
    """실패하면 빈 문자열 — 요약 없이 발송하면 됨."""
    if _client is None:
        return ""
    try:
        r = _client.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(
                title=a.title,
                snippet=a.summary or "(발췌 없음)",
                source=a.source,
            ),
        )
        text = (r.text or "").strip()
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())[:400]
    except Exception as e:
        log.warning(f"gemini summarize fail: {e}")
        return ""
