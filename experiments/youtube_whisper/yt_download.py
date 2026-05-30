# FILE: experiments/youtube_whisper/yt_download.py
"""YouTube URL/제목 → 동영상(또는 mp3) 다운로드 (yt-dlp 래퍼).

사용 예:
    python yt_download.py "https://www.youtube.com/watch?v=xxxx"
    python yt_download.py "노이즈 캔슬링 작동 원리"
    python yt_download.py "lofi hip hop" --audio
"""
from __future__ import annotations

import argparse
from pathlib import Path

from yt_dlp import YoutubeDL

OUTPUT_DIR = Path(__file__).parent / "downloads"


def download(query: str, audio_only: bool = False) -> Path:
    """링크면 그대로, 제목이면 ytsearch1로 첫 결과를 받는다."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    is_url = query.startswith(("http://", "https://"))
    target = query if is_url else f"ytsearch1:{query}"

    opts: dict = {
        "outtmpl": str(OUTPUT_DIR / "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "restrictfilenames": True,  # 한글/특수문자 → 안전한 파일명
    }
    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target, download=True)
        if "entries" in info:  # ytsearch 결과는 entries로 감싸짐
            info = info["entries"][0]
        filename = ydl.prepare_filename(info)
        if audio_only:
            filename = str(Path(filename).with_suffix(".mp3"))

    saved = Path(filename)
    print(f"\n[OK] saved: {saved}")
    return saved


def main() -> None:
    p = argparse.ArgumentParser(description="YouTube 다운로드 (URL 또는 제목)")
    p.add_argument("query", help="YouTube URL 또는 검색할 제목")
    p.add_argument("--audio", action="store_true", help="mp3로만 받기 (영상 X)")
    args = p.parse_args()
    download(args.query, audio_only=args.audio)


if __name__ == "__main__":
    main()
