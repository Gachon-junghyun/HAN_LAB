# FILE: experiments/youtube_whisper/_preview_channels.py
"""ad-hoc: 채널 리스트의 최신 영상 제목/URL 미리보기 (전사 전 확인용, 임시 스크립트)."""
from __future__ import annotations

import sys
from yt_dlp import YoutubeDL

from channel_fetch import _normalize_channel, _resolve_via_search, _flatten_entries

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
LIMIT = 5  # 미리보기는 5개씩만

OPTS = {
    "extract_flat": True,
    "playlistend": LIMIT,
    "quiet": True,
    "skip_download": True,
    "ignoreerrors": True,
}


def preview(name: str) -> None:
    print(f"\n=== {name} ===")
    with YoutubeDL(OPTS) as ydl:
        info = ydl.extract_info(_normalize_channel(name), download=False)
    entries = _flatten_entries(info)
    if not entries:
        fb = _resolve_via_search(name)
        if fb:
            print(f"(검색 폴백: {fb})")
            with YoutubeDL(OPTS) as ydl:
                info = ydl.extract_info(fb, download=False)
            entries = _flatten_entries(info)
    if not entries:
        print("  [!] 못 찾음")
        return
    for e in entries[:LIMIT]:
        vid = e.get("id", "?")
        title = e.get("title", "?")
        if len(vid) != 11:
            continue
        print(f"  - https://www.youtube.com/watch?v={vid}  |  {title}")


if __name__ == "__main__":
    for c in CHANNELS:
        preview(c)
