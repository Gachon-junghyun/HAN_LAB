# FILE: experiments/insight_pipeline/02_extract/schema.py
"""V1 데이터 스키마.

핵심 원칙(설계 메모 §2):
- 명제(proposition)와 원문 인용(raw_quote)은 영구히 페어.
- 다중 라벨: types는 list. 이항 분류 안 함.
- 신뢰도는 categorical(confidence_level). 연속 점수 안 씀.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

# ---- 라벨 정의 (메모 §3 다중라벨 + §4 스키마) -----------------------------
PropositionType = Literal[
    "fact_statement",          # 사실 진술
    "causal_claim",            # 인과 주장
    "prediction",              # 예측
    "conditional_prediction",  # 조건부 예측
    "interpretation",          # 해석·프레이밍
    "anecdote",                # 일화·예시
    "meta_remark",             # 메타 발언
    "promotion_chatter",       # 광고·잡담
]

Direction = Literal["bullish", "bearish", "neutral", "conditional"]
TimeHorizon = Literal["intraday", "short", "mid", "long", "unspecified"]
ConfidenceLevel = Literal["high", "medium", "low", "hedged"]
Verifiable = Literal["yes_now", "yes_after_time", "no_opinion"]
EvidenceType = Literal["none", "data", "anecdote", "other_opinion", "public_fact"]
Position = Literal["intro", "body", "outro"]


# ---- 1단계(01_clean) 산출물 ---------------------------------------------
@dataclass
class Sentence:
    """청크 안의 한 문장(=srt segment 1행)."""
    sentence_idx: int        # 청크 내부 0-based 인덱스
    timestamp_start: str     # HH:MM:SS,mmm
    timestamp_end: str
    text: str


@dataclass
class Chunk:
    """02_extract의 입력 단위. 60초 윈도우 + 문장 경계 우선."""
    chunk_id: str                          # f"{video_id}:{chunk_idx:04d}"
    video_id: str                          # 11자리
    channel: str                           # 머니코믹스 / 김단테 월가아재 / ...
    chunk_idx: int                         # 0-based
    start_ts: str
    end_ts: str
    duration_s: float
    sentences: list[Sentence] = field(default_factory=list)
    position_in_video: Position = "body"
    hallucination_suspected: bool = False  # 윈도우 N=5에 동일문장 3회+ 등장

    def to_dict(self) -> dict:
        return asdict(self)


# ---- 2단계(02_extract) 산출물 — 메모 §4 그대로 ---------------------------
@dataclass
class Proposition:
    """1발언 = 1행. raw_quote와 proposition은 항상 페어."""
    speaker: str
    video_id: str
    chunk_idx: int
    sentence_idx_in_chunk: int
    timestamp_start: str
    raw_quote: str
    proposition: str
    types: list[PropositionType]
    evidence_mentioned: list[str]
    evidence_type: EvidenceType
    direction: Direction
    time_horizon: TimeHorizon
    conditions: list[str]
    confidence_level: ConfidenceLevel
    verifiable: Verifiable
    verification_hint: str | None
    topics: list[str]
    is_promotional: bool = False
    is_meta_remark: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
