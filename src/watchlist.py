"""watchlist.yaml 로드 + 기사-기업 매칭 규칙."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from .config import WATCHLIST_PATH


@dataclass
class Company:
    name: str
    layer_key: str
    layer_name: str
    emoji: str
    aliases: list[str]
    broad: bool = False
    require_any: list[str] = field(default_factory=list)
    en_query: str = ""
    is_theme: bool = False  # 계층 extra_keywords 로 만들어진 가상 엔트리

    @property
    def tag(self) -> str:
        return f"{self.emoji} {self.layer_name} | {self.name}"


def _has_word(alias: str, text: str) -> bool:
    """alias 가 text 에 있는지.

    짧은 전부-대문자 영문 약어(MS, AWS, AMD, HBM...)는 대소문자 구분 + 단어 경계
    매칭 — 'systems' 에 MS 가 걸리는 오탐 방지. 그 외는 대소문자 무시 부분 매칭.
    """
    if alias.isascii() and alias.isupper() and len(alias) <= 4:
        # 뒤에 소문자만 아니면 매치 — HBM4, HBM3E 는 HBM 에 걸리고 'systems' 는 MS 에 안 걸림
        return re.search(rf"\b{re.escape(alias)}(?![a-z])", text) is not None
    if alias.isascii():
        return re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE) is not None
    return alias in text  # 한글은 조사가 붙으므로 부분 매칭


class Watchlist:
    def __init__(self, companies: list[Company], context_keywords: list[str],
                 exclude_title_keywords: list[str]):
        self.companies = companies
        self.context_keywords = context_keywords
        self.exclude_title_keywords = exclude_title_keywords

    def match(self, title: str, full_text: str = "") -> list[Company]:
        """기사에 걸리는 엔트리 전부 반환.

        회사명(alias)은 제목에서만 찾음 — 본문 요약에 스치듯 언급된 시황성
        기사(코스피 폭락에 하이닉스가 언급되는 류)를 걸러냄. 문맥 키워드
        (broad/require_any)는 제목+요약 전체에서 확인.
        """
        if any(_has_word(k, title) for k in self.exclude_title_keywords):
            return []
        full_text = full_text or title
        hits = []
        for c in self.companies:
            if not any(_has_word(a, title) for a in c.aliases):
                continue
            required = c.require_any or (self.context_keywords if c.broad else [])
            if required and not any(_has_word(k, full_text) for k in required):
                continue
            hits.append(c)
        return hits


def load() -> Watchlist:
    data = yaml.safe_load(WATCHLIST_PATH.read_text(encoding="utf-8"))
    companies: list[Company] = []
    for key, layer in data["layers"].items():
        lname, emoji = layer["name"], layer.get("emoji", "")
        for c in layer.get("companies", []):
            companies.append(Company(
                name=c["name"], layer_key=key, layer_name=lname, emoji=emoji,
                aliases=c.get("aliases") or [c["name"]],
                broad=bool(c.get("broad")),
                require_any=c.get("require_any") or [],
                en_query=c.get("en_query", ""),
            ))
        for kw in layer.get("extra_keywords", []):
            companies.append(Company(
                name=kw, layer_key=key, layer_name=lname, emoji=emoji,
                aliases=[kw], is_theme=True,
            ))
    return Watchlist(
        companies,
        data.get("context_keywords", []),
        data.get("exclude_title_keywords", []),
    )
