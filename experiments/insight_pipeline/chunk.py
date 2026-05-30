# FILE: experiments/insight_pipeline/chunk.py
"""segments → 청크(60초 + 문장 경계) → schema.Chunk 리스트.

설계 메모 §3 청크 단위:
    "청크로 자르되, 청크 내에서 명제를 추출할 때
     원문이 청크 내 어느 문장에서 나왔는지의 인덱스를 함께 저장한다."

intro/outro 태깅:
    영상 시작 30초 / 마지막 30초만 태깅(보존). 자동 컷 안 함.
    영상이 90초 미만이면 전부 body로 처리(짧은 영상에서 30초가 너무 큰 비중).
"""
from __future__ import annotations

import re
from pathlib import Path

from schema import Chunk, Sentence
from clean import srt_to_clean


def ts_to_sec(ts: str) -> float:
    """HH:MM:SS,mmm → seconds."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _position(start_s: float, total_s: float, edge_s: float = 30.0) -> str:
    if total_s < edge_s * 3:
        return "body"
    if start_s < edge_s:
        return "intro"
    if start_s >= total_s - edge_s:
        return "outro"
    return "body"


def chunk_video(
    video_id: str,
    channel: str,
    segments: list[dict],
    suspected: set[int],
    target_s: float = 60.0,
) -> list[Chunk]:
    """segments → 60초 + 문장 경계 청크."""
    if not segments:
        return []
    total_s = ts_to_sec(segments[-1]["end"])
    chunks: list[Chunk] = []
    cur_segs: list[dict] = []
    cur_start_s: float | None = None

    def flush() -> None:
        nonlocal cur_segs, cur_start_s
        if not cur_segs:
            return
        sentences = [
            Sentence(
                sentence_idx=i,
                timestamp_start=s["start"],
                timestamp_end=s["end"],
                text=s["text"],
            )
            for i, s in enumerate(cur_segs)
        ]
        start_ts = cur_segs[0]["start"]
        end_ts = cur_segs[-1]["end"]
        start_s = ts_to_sec(start_ts)
        end_s = ts_to_sec(end_ts)
        any_susp = any(s["idx"] in suspected for s in cur_segs)
        chunks.append(Chunk(
            chunk_id=f"{video_id}:{len(chunks):04d}",
            video_id=video_id,
            channel=channel,
            chunk_idx=len(chunks),
            start_ts=start_ts,
            end_ts=end_ts,
            duration_s=round(end_s - start_s, 3),
            sentences=sentences,
            position_in_video=_position(start_s, total_s),
            hallucination_suspected=any_susp,
        ))
        cur_segs = []
        cur_start_s = None

    for seg in segments:
        seg_start_s = ts_to_sec(seg["start"])
        if cur_start_s is None:
            cur_start_s = seg_start_s
        if (seg_start_s - cur_start_s) >= target_s and cur_segs:
            flush()
            cur_start_s = seg_start_s
        cur_segs.append(seg)
    flush()
    return chunks


_VID_RE = re.compile(r"\[([a-zA-Z0-9_-]{11})\]")


def video_id_from_path(p: Path) -> str | None:
    m = _VID_RE.search(p.stem)
    return m.group(1) if m else None


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from channel_map import build_channel_map

    base = Path(__file__).parent.parent / "youtube_whisper"
    channel_map = build_channel_map(base / "list.txt")

    sample_srt = sorted((base / "transcripts").glob("*.srt"))[0]
    vid = video_id_from_path(sample_srt) or "unknown"
    channel = channel_map.get(vid, "unknown")

    segs, susp = srt_to_clean(sample_srt)
    chunks = chunk_video(vid, channel, segs, susp)
    print(f"[OK] {sample_srt.name}")
    print(f"  채널: {channel} (video_id={vid})")
    print(f"  segments={len(segs)}, suspected={len(susp)}")
    print(f"  chunks={len(chunks)}")
    if chunks:
        c = chunks[0]
        print(f"\n  첫 청크:")
        print(f"    id={c.chunk_id} ts={c.start_ts}~{c.end_ts} ({c.duration_s}s)")
        print(f"    position={c.position_in_video}, sentences={len(c.sentences)}, hallu={c.hallucination_suspected}")
        for s in c.sentences[:3]:
            print(f"      [{s.timestamp_start}] {s.text[:60]}")
