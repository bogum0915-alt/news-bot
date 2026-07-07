"""공용 Article 모델."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .watchlist import Company


@dataclass
class Article:
    title: str
    url: str
    source: str          # 언론사명
    published: datetime  # tz-aware
    origin: str          # 'naver' | 'gnews'
    summary: str = ""
    companies: list[Company] = field(default_factory=list)
