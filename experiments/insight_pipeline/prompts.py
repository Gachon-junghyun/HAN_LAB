# FILE: experiments/insight_pipeline/prompts.py
"""LLM 프롬프트 (gemma4:e4b 기준).

설계 메모 §2 원칙 그대로:
- raw_quote는 청크 원문 그대로 (요약·변형 금지) → 후처리에서 substring 검증
- 원문에 없으면 null / 빈 리스트
- 다중 라벨 허용
- 명제 0개 가능 (잡담뿐인 청크)
"""

SYSTEM_PROMPT = """당신은 경제 유튜브 발언에서 분석 가능한 명제(proposition)를 추출하는 도구다.

핵심 규칙:
1. 모든 명제는 반드시 청크 안의 원문(raw_quote)과 페어로 출력한다.
2. raw_quote는 입력에 표시된 문장을 글자 그대로 복사한다. 요약·변형·번역 금지.
3. 청크가 광고·잡담·인사말·BGM·인트로뿐이라면 빈 리스트를 반환한다.
   분석 가능한 명제가 많아도 청크당 최대 6개까지만 추출(중요한 것 우선).
4. 모르는 필드는 null 또는 빈 리스트 [] 또는 "unspecified"로 둔다(환각 금지).
5. JSON 외의 텍스트는 출력하지 않는다.

각 명제 객체 스키마:
{
  "raw_quote": "<청크의 원문 한 문장을 그대로>",
  "proposition": "<중립적 1문장으로 정리>",
  "sentence_idx_in_chunk": <int, 원문이 등장한 문장 인덱스>,
  "types": [<다음 중 1개 이상: "fact_statement","causal_claim","prediction","conditional_prediction","interpretation","anecdote","meta_remark","promotion_chatter">],
  "evidence_mentioned": [<발화자가 근거로 든 항목들, 없으면 []>],
  "evidence_type": "none" | "data" | "anecdote" | "other_opinion" | "public_fact",
  "direction": "bullish" | "bearish" | "neutral" | "conditional",
  "time_horizon": "intraday" | "short" | "mid" | "long" | "unspecified",
  "conditions": [<조건절 문구들, 없으면 []>],
  "confidence_level": "high" | "medium" | "low" | "hedged",
  "verifiable": "yes_now" | "yes_after_time" | "no_opinion",
  "verification_hint": "<검증 방법 1줄, 없으면 null>",
  "topics": [<소문자 영어 키워드, 예: "semiconductor","fed","earnings">],
  "is_promotional": <bool>,
  "is_meta_remark": <bool>
}

최종 출력 형식 (JSON 객체):
{"propositions": [<위 객체 0개 이상>]}
"""

USER_PROMPT_TEMPLATE = """채널: {channel}
영상: {video_id} ({position} 구간)
청크 ID: {chunk_id} ({duration_s}초)

[청크 원문 — 문장 인덱스 / 타임스탬프 / 본문]
{sentences_block}

위 청크에서 분석 가능한 명제를 모두 추출하라.
잡담·인사말만 있으면 {{"propositions": []}} 를 반환하라."""


def format_user_prompt(chunk: dict) -> str:
    sentences_block = "\n".join(
        f"  [{s['sentence_idx']}] ({s['timestamp_start']}) {s['text']}"
        for s in chunk["sentences"]
    )
    return USER_PROMPT_TEMPLATE.format(
        channel=chunk["channel"],
        video_id=chunk["video_id"],
        position=chunk["position_in_video"],
        chunk_id=chunk["chunk_id"],
        duration_s=chunk["duration_s"],
        sentences_block=sentences_block,
    )
