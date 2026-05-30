# FILE: experiments/youtube_whisper/channel_fetch.py
"""YouTube 채널 → 최신 영상 URL 목록 (yt-dlp 래퍼, 다운로드 없음).

사용 예:
    # 핸들/평문/전체 URL 모두 허용
    python channel_fetch.py "@MKBHD" -n 16
    python channel_fetch.py "슈카월드" -n 5
    python channel_fetch.py "https://www.youtube.com/@MKBHD" -n 10
"""
from __future__ import annotations

import argparse
import sys

from yt_dlp import YoutubeDL

# Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록 utf-8 강제
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VIDEO_URL_FMT = "https://www.youtube.com/watch?v={id}"


def _normalize_channel(channel: str) -> str:
    """채널 식별자를 /videos 탭 URL로 정규화.

    허용 입력:
      - 전체 URL (http...)  → 끝에 /videos 없으면 붙임
      - @핸들 (@MKBHD)      → https://www.youtube.com/@MKBHD/videos
      - 평문 이름 (MKBHD)   → https://www.youtube.com/@MKBHD/videos
    """
    c = channel.strip()
    if c.startswith(("http://", "https://")):
        c = c.rstrip("/")
        return c if c.endswith("/videos") else c + "/videos"
    if not c.startswith("@"):
        c = "@" + c
    return f"https://www.youtube.com/{c}/videos"


def _flatten_entries(info: dict | None) -> list[dict]:
    """yt-dlp가 가끔 entries 안에 entries를 중첩으로 반환 → 평탄화."""
    if not info:
        return []
    if "entries" in info and info["entries"] is not None:
        out: list[dict] = []
        for e in info["entries"]:
            out.extend(_flatten_entries(e))
        return out
    if info.get("id"):
        return [info]
    return []


def _resolve_via_search(channel: str) -> str | None:
    """직접 핸들이 안 먹힐 때 폴백: 검색 결과의 첫 영상 → 그 영상의 채널 /videos URL."""
    opts = {"quiet": True, "extract_flat": True, "skip_download": True, "ignoreerrors": True}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{channel}", download=False)
    entries = info.get("entries") if info else None
    if not entries:
        return None
    e = entries[0] or {}
    ch_url = e.get("channel_url")
    if not ch_url and e.get("channel_id"):
        ch_url = f"https://www.youtube.com/channel/{e['channel_id']}"
    if not ch_url:
        return None
    return ch_url.rstrip("/") + "/videos"


def fetch_latest_videos(channel: str, limit: int = 16) -> list[str]:
    """채널 최신 영상 URL을 limit 개수만큼 반환 (다운로드 X).

    1순위: @핸들/평문/URL을 /videos 페이지로 정규화 후 시도
    2순위: 1번이 0건이면 검색 결과의 첫 영상에서 채널 URL을 추출해 재시도
    """
    opts = {
        "extract_flat": True,   # 메타데이터만 — 실제 영상 다운로드 안 함
        "playlistend": limit,
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
    }

    def _try(url: str) -> list[dict]:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return _flatten_entries(info)

    entries = _try(_normalize_channel(channel))
    if not entries:
        fallback = _resolve_via_search(channel)
        if fallback:
            print(f"[..] '{channel}': 핸들 직매칭 실패 → 검색 폴백: {fallback}", file=sys.stderr)
            entries = _try(fallback)
    urls: list[str] = []
    for e in entries:
        # _type == 'url' (extract_flat 결과) 또는 'video' 둘 다 id 보유
        vid = e.get("id")
        if not vid:
            continue
        # 가끔 채널/플레이리스트가 entries에 섞임 → 11자리 영상 ID만 채택
        if len(vid) != 11:
            continue
        urls.append(VIDEO_URL_FMT.format(id=vid))
        if len(urls) >= limit:
            break
    return urls


def main() -> None:
    p = argparse.ArgumentParser(description="YouTube 채널 → 최신 영상 URL 목록")
    p.add_argument("channel", help="채널 핸들(@xxx), 평문 이름, 또는 채널 URL")
    p.add_argument("-n", "--limit", type=int, default=16,
                   help="가져올 영상 수 (기본 16)")
    args = p.parse_args()

    urls = fetch_latest_videos(args.channel, args.limit)
    if not urls:
        print(f"[!] 영상을 찾지 못함: {args.channel}")
        return
    for u in urls:
        print(u)


if __name__ == "__main__":
    main()
