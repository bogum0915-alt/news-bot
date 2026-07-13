"""Gemini로 기사 판정(푸시 가치) + 1~3줄 요약 (~음/함 톤).

한 번의 호출로 중요도 점수와 요약을 같이 받음 — 점수가 IMPORTANCE_MIN
미만이면 발송하지 않음. 판정 실패 시엔 놓치는 게 더 나쁘므로 발송 쪽으로 폴백.
"""
from __future__ import annotations

import json
import logging
import re
import time

from google import genai

from .config import GEMINI_API_KEY
from .models import Article

log = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL = "gemini-2.5-flash-lite"  # 판정 볼륨이 크므로 쿼터 여유 있는 lite 사용

PROMPT = """너는 AI 밸류체인(CSP·AI랩·AI칩·파운드리·메모리) 투자자의 뉴스 필터야.
아래 기사가 투자 판단에 유의미한지 판정하고 요약해.

제목: {title}
발췌: {snippet}
언론사: {source}

JSON 한 개로만 답해:
{{"importance": 1~5, "summary": "...", "category": "실적|제품|수주|규제|기타"}}

category 기준: 실적(실적·가이던스·컨센 변화), 제품(제품·기술·로드맵),
수주(수주·공급계약·CAPEX·증설·파트너십), 규제(규제·수출통제·소송), 그 외 기타.

importance 기준:
- 5: 밸류체인 판도 변화 — 대형 CAPEX/수주/공급계약, 규제·수출통제, M&A, 대형 장애·사고
- 4: 실적·가이던스, 증설·데이터센터 착공, HBM/패키징/공정 기술 진전, 제품 로드맵, 공급망 변화, 핵심 인물의 전략 발언, 시장을 움직인 대형 리서치 콜
- 3: 유의미하지만 소식 수준 — 중소형 제휴, 점진적 업데이트, 의미 있는 산업 데이터
- 2: 재탕·간접 관련 — 이미 알려진 내용 반복, 회사가 소재로만 언급, 홍보성 보도자료
- 1: 잡음 — 주가 등락 해설, ETF/레버리지/크립토 거래, 목표가·매수의견, "Can X be the next Y" 류 의견 기사, 게임 드라이버 등 소비자 제품 소식, 개인 투자자 대상 콘텐츠

summary 규칙:
- 1~3줄, 각 줄 60자 이내, 줄바꿈으로 구분. importance 2 이하면 빈 문자열 "".
- 제공된 제목/발췌의 사실만. 추측·과장 금지. 영문이면 한국어로 번역.
- 모든 문장 반말·축약형 ~음/함/됐음/했음/임 어미. 메모 톤.
  좋은 예: "TSMC가 CoWoS 캐파 2배 증설 발표했음" / 나쁜 예: "...입니다"
- JSON 외 다른 텍스트 출력 금지."""

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


_CATEGORIES = {"실적", "제품", "수주", "규제", "기타"}


def assess(a: Article) -> dict:
    """{'importance': int, 'summary': str, 'category': str}. 실패 시 importance=3(발송) 폴백."""
    fallback = {"importance": 3, "summary": "", "category": "기타"}
    if _client is None:
        return fallback
    for attempt in (1, 2):  # 503 등 일시 오류 대비 1회 재시도
        try:
            r = _client.models.generate_content(
                model=MODEL,
                contents=PROMPT.format(
                    title=a.title,
                    snippet=a.summary or "(발췌 없음)",
                    source=a.source,
                ),
            )
            d = json.loads(_FENCE.sub("", (r.text or "").strip()))
            cat = str(d.get("category", "기타")).strip()
            return {
                "importance": max(1, min(5, int(d.get("importance", 3)))),
                "summary": str(d.get("summary", "")).strip()[:400],
                "category": cat if cat in _CATEGORIES else "기타",
            }
        except Exception as e:
            log.warning(f"gemini assess fail (try {attempt}): {e}")
            if attempt == 1:
                time.sleep(3)
    return fallback
