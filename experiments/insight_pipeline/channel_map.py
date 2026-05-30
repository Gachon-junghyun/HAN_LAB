# FILE: experiments/insight_pipeline/channel_map.py
"""list.txt(채널 헤더 + URL) → video_id → 채널명 매핑.

list.txt 포맷 (youtube_whisper/_build_list.py 산물):
    # === 머니코믹스 (16개) ===
    https://www.youtube.com/watch?v=T9L5jSFarmc
    ...

    # === 김단테 월가아재 (16개) ===
    https://www.youtube.com/watch?v=ARn8WwEdieQ
    ...
"""
from __future__ import annotations

import re
from pathlib import Path

CHANNEL_HEADER_RE = re.compile(r"^#\s*===\s*(.+?)\s*\(\d+개\)\s*===\s*$")
VIDEO_ID_RE = re.compile(r"v=([a-zA-Z0-9_-]{11})")


def build_channel_map(list_txt: Path) -> dict[str, str]:
    """video_id → 채널명 dict 반환."""
    mapping: dict[str, str] = {}
    current_channel = "unknown"
    for line in list_txt.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        m = CHANNEL_HEADER_RE.match(line)
        if m:
            current_channel = m.group(1).strip()
            continue
        if line.startswith("#"):
            continue
        vm = VIDEO_ID_RE.search(line)
        if vm:
            mapping[vm.group(1)] = current_channel
    return mapping


if __name__ == "__main__":
    # smoke test
    src = Path(__file__).parent.parent / "youtube_whisper" / "list.txt"
    mp = build_channel_map(src)
    print(f"[OK] {len(mp)}개 video_id 매핑")
    by_channel: dict[str, int] = {}
    for ch in mp.values():
        by_channel[ch] = by_channel.get(ch, 0) + 1
    for ch, n in by_channel.items():
        print(f"  - {ch}: {n}개")
