# FILE: experiments/insight_pipeline/_smoke_extract.py
"""1회용: extract smoke test.
오선(짧음) + 머니그라피(가장 토큰 클 만한 채널) 각각 1청크씩 → 속도/응답 확인."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from extract import extract_chunk, call_llm, MODEL
from prompts import format_user_prompt, SYSTEM_PROMPT

chunks_path = Path(__file__).parent / "data" / "chunks.jsonl"

# 채널별 1청크씩 (body 위치 우선)
samples: dict[str, dict] = {}
with chunks_path.open(encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        if c["channel"] not in samples and c["position_in_video"] == "body":
            samples[c["channel"]] = c
        if len(samples) >= 5:
            break

# 오선 + 머니그라피 우선
priority = ["오선의 미국 증시 라이프", "머니그라피"]
targets = [samples[ch] for ch in priority if ch in samples]

for c in targets:
    # 토큰 추정 (대략): char 수
    user = format_user_prompt(c)
    sys_chars = len(SYSTEM_PROMPT)
    user_chars = len(user)
    print(f"\n=== {c['chunk_id']} ({c['channel']}, {c['duration_s']}s) ===")
    print(f"  prompt chars: system={sys_chars}, user={user_chars}, total={sys_chars+user_chars}")
    t0 = time.time()
    props, rejected = extract_chunk(c)
    dt = time.time() - t0
    print(f"  명제 {len(props)}개 / reject {rejected}개 / {dt:.1f}s")
    for p in props[:3]:
        print(f"\n  raw_quote: {p.raw_quote[:80]}")
        print(f"  proposition: {p.proposition[:80]}")
        print(f"  types={p.types} dir={p.direction} conf={p.confidence_level}")
