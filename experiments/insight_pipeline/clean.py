# FILE: experiments/insight_pipeline/clean.py
"""SRT 파싱 + Whisper 환각 마킹.

설계 메모 §3: "동일 문장이 3회 이상 반복되면 Whisper 환각 후보"
구현은 윈도우 N=5 안에 동일 텍스트 threshold=4회 이상 등장(80%+) → suspected.
- 사용자 메모의 false-positive > false-negative 원칙 따라 일단 마킹만 하고 발화는 보존.
- 후처리에서 hallucination_suspected=True인 청크의 추출 결과를 별도로 검토 가능.
"""
from __future__ import annotations

import re
from pathlib import Path

_TS_RE = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})"
)


def parse_srt(path: Path) -> list[dict]:
    """SRT → [{idx, start, end, text}, ...]."""
    raw = path.read_text(encoding="utf-8")
    segments: list[dict] = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        ts_line_idx = 1 if _TS_RE.search(lines[1]) else (0 if _TS_RE.search(lines[0]) else None)
        if ts_line_idx is None:
            continue
        m = _TS_RE.search(lines[ts_line_idx])
        if not m:
            continue
        start, end = m.group(1), m.group(2)
        text = " ".join(lines[ts_line_idx + 1:]).strip()
        if not text:
            continue
        segments.append({
            "idx": len(segments),
            "start": start,
            "end": end,
            "text": text,
        })
    return segments


def mark_hallucinations(
    segments: list[dict], window: int = 5, threshold: int = 4
) -> set[int]:
    """슬라이딩 윈도우 안 동일 텍스트 threshold회 이상 → 의심 인덱스 set."""
    suspected: set[int] = set()
    for i in range(len(segments)):
        lo = max(0, i - window + 1)
        bucket: dict[str, list[int]] = {}
        for j in range(lo, i + 1):
            t = segments[j]["text"].strip()
            bucket.setdefault(t, []).append(j)
        for t, idxs in bucket.items():
            if len(idxs) >= threshold:
                suspected.update(idxs)
    return suspected


def srt_to_clean(path: Path) -> tuple[list[dict], set[int]]:
    segments = parse_srt(path)
    suspected = mark_hallucinations(segments)
    return segments, suspected


if __name__ == "__main__":
    # smoke test: transcripts/ 첫 .srt
    base = Path(__file__).parent.parent / "youtube_whisper" / "transcripts"
    sample = sorted(base.glob("*.srt"))[0]
    segs, susp = srt_to_clean(sample)
    print(f"[OK] {sample.name}")
    print(f"  segments: {len(segs)}")
    print(f"  suspected hallucinations: {len(susp)}")
    if susp:
        print(f"  의심 예시:")
        for idx in sorted(susp)[:3]:
            print(f"    [{segs[idx]['start']}] {segs[idx]['text'][:60]}")
