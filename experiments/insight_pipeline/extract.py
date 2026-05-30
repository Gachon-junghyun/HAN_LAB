# FILE: experiments/insight_pipeline/extract.py
"""청크 → LLM(ollama, gemma4:e4b) → Proposition 리스트.

핵심:
- format='json' 모드로 호출
- raw_quote가 청크 원문에 실제 들어가는지 substring 검증 → 통과 못 한 명제 reject
- LLM 응답 자체 실패 / JSON 파싱 실패 / 유효성 실패는 모두 reject 카운트로 분리 보존
"""
from __future__ import annotations

import json
import sys
from typing import Any

import ollama

from prompts import SYSTEM_PROMPT, format_user_prompt
from schema import Proposition

MODEL = "gemma2:9b"


def call_llm(chunk: dict, model: str = MODEL) -> list[dict]:
    """LLM 호출 → list[dict]. 실패 시 빈 리스트."""
    try:
        resp = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": format_user_prompt(chunk)},
            ],
            format="json",
            options={"temperature": 0.1, "num_ctx": 4096, "num_predict": 2500},
        )
    except Exception as e:
        print(f"  [ERR] ollama 호출 실패: {chunk['chunk_id']} -> {e!r}", file=sys.stderr)
        return []
    content = resp["message"]["content"]
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  [ERR] JSON 파싱 실패: {chunk['chunk_id']} -> {e!r}", file=sys.stderr)
        return []
    props = parsed.get("propositions", [])
    if not isinstance(props, list):
        return []
    return props


def _chunk_full_text(chunk: dict) -> str:
    return " ".join(s["text"] for s in chunk["sentences"])


def validate_raw_quote(raw: Any, chunk_text: str) -> bool:
    """raw_quote가 청크 원문에 substring으로 존재하는지."""
    if not raw or not isinstance(raw, str):
        return False
    needle = raw.strip()
    if len(needle) < 4:
        return False
    return needle in chunk_text


def to_proposition(p: dict, chunk: dict) -> Proposition:
    """LLM 응답 dict → Proposition dataclass."""
    return Proposition(
        speaker=chunk["channel"],
        video_id=chunk["video_id"],
        chunk_idx=chunk["chunk_idx"],
        sentence_idx_in_chunk=int(p.get("sentence_idx_in_chunk", -1) or -1),
        timestamp_start=chunk["start_ts"],
        raw_quote=p["raw_quote"].strip(),
        proposition=str(p.get("proposition", "")).strip(),
        types=list(p.get("types") or []),
        evidence_mentioned=list(p.get("evidence_mentioned") or []),
        evidence_type=p.get("evidence_type") or "none",
        direction=p.get("direction") or "neutral",
        time_horizon=p.get("time_horizon") or "unspecified",
        conditions=list(p.get("conditions") or []),
        confidence_level=p.get("confidence_level") or "medium",
        verifiable=p.get("verifiable") or "no_opinion",
        verification_hint=p.get("verification_hint"),
        topics=list(p.get("topics") or []),
        is_promotional=bool(p.get("is_promotional", False)),
        is_meta_remark=bool(p.get("is_meta_remark", False)),
    )


def extract_chunk(chunk: dict, model: str = MODEL) -> tuple[list[Proposition], int]:
    """청크 → (유효 명제, reject 개수)."""
    raw_props = call_llm(chunk, model)
    if not raw_props:
        return [], 0
    chunk_text = _chunk_full_text(chunk)
    valid: list[Proposition] = []
    rejected = 0
    for p in raw_props:
        if not isinstance(p, dict):
            rejected += 1
            continue
        if not validate_raw_quote(p.get("raw_quote"), chunk_text):
            rejected += 1
            continue
        try:
            valid.append(to_proposition(p, chunk))
        except Exception as e:
            rejected += 1
            print(f"  [ERR] Proposition 생성 실패: {chunk['chunk_id']} -> {e!r}", file=sys.stderr)
    return valid, rejected


if __name__ == "__main__":
    # smoke test: chunks.jsonl 첫 5개
    from pathlib import Path
    import time

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    chunks_path = Path(__file__).parent / "data" / "chunks.jsonl"
    chunks: list[dict] = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
            if len(chunks) >= 5:
                break

    for ch in chunks:
        print(f"\n=== {ch['chunk_id']} ({ch['channel']}, {ch['position_in_video']}, {ch['duration_s']}s) ===")
        t0 = time.time()
        props, rejected = extract_chunk(ch)
        dt = time.time() - t0
        print(f"  명제 {len(props)}개 / reject {rejected}개 / {dt:.1f}s")
        for p in props:
            print(f"\n  proposition: {p.proposition}")
            print(f"  raw_quote: {p.raw_quote}")
            print(f"  types={p.types} dir={p.direction} conf={p.confidence_level} topics={p.topics}")
