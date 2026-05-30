# FILE: experiments/youtube_whisper/_build_list.py
"""1회용: 지정한 5채널의 최신 16편 URL을 list.txt에 작성 (채널별 # 주석 헤더 포함)."""
from __future__ import annotations

import sys
from channel_fetch import fetch_latest_videos

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CHANNELS = [
    "머니코믹스",
    "김단테 월가아재",
    "머니그라피",
    "지식부장관",
    "오선의 미국 증시 라이프",
]
PER_CHANNEL = 16

total = 0
with open("list.txt", "w", encoding="utf-8") as f:
    for c in CHANNELS:
        urls = fetch_latest_videos(c, PER_CHANNEL)
        total += len(urls)
        f.write(f"# === {c} ({len(urls)}개) ===\n")
        for u in urls:
            f.write(u + "\n")
        f.write("\n")
print(f"[OK] list.txt 작성: {total}개 URL")
