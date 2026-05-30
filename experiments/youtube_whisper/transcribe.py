# FILE: experiments/youtube_whisper/transcribe.py
"""input/ 폴더의 동영상/오디오 → Whisper 스크립트 변환 (로컬 faster-whisper).

사용 예:
    # input/ 폴더의 모든 미디어 파일을 base 모델로 변환
    python transcribe.py

    # 모델 크기 키우고 한국어 강제
    python transcribe.py --model small --language ko

    # 특정 파일만
    python transcribe.py --file ../downloads/some_video.mp4
"""
from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel

BASE = Path(__file__).parent
INPUT_DIR = BASE / "input"
OUTPUT_DIR = BASE / "transcripts"

MEDIA_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".mp3", ".wav", ".m4a", ".flac", ".ogg"}


def _ts(sec: float) -> str:
    """초 → SRT 타임스탬프 (HH:MM:SS,mmm)."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec - h * 3600 - m * 60
    ms = int((s - int(s)) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"


def transcribe_one(media: Path, model: WhisperModel, language: str | None) -> Path:
    """단일 파일 → .txt(전사문) + .srt(자막) 저장."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    segments, info = model.transcribe(
        str(media),
        language=language,
        vad_filter=True,  # 무음 구간 자동 스킵 → 환각 방지
        beam_size=5,
    )

    txt_path = OUTPUT_DIR / f"{media.stem}.txt"
    srt_path = OUTPUT_DIR / f"{media.stem}.srt"

    with txt_path.open("w", encoding="utf-8") as ftxt, srt_path.open("w", encoding="utf-8") as fsrt:
        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            ftxt.write(text + "\n")
            fsrt.write(f"{i}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{text}\n\n")

    print(f"[OK] {media.name}  (lang={info.language}, prob={info.language_probability:.2f})")
    print(f"     -> {txt_path}")
    print(f"     -> {srt_path}")
    return txt_path


def main() -> None:
    p = argparse.ArgumentParser(description="input/ 동영상 → Whisper 스크립트")
    p.add_argument("--model", default="large-v3",
                   help="모델 크기: tiny / base / small / medium / large-v3 (기본: large-v3)")
    p.add_argument("--language", default=None, help="언어 강제 (예: ko, en). 미지정 시 자동 감지.")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본: cuda — RTX 3080)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본: float16 — GPU 최적)")
    p.add_argument("--file", default=None, help="단일 파일 경로 (지정 시 input/ 폴더 무시)")
    args = p.parse_args()

    INPUT_DIR.mkdir(exist_ok=True)

    if args.file:
        files = [Path(args.file)]
    else:
        files = sorted(f for f in INPUT_DIR.iterdir() if f.suffix.lower() in MEDIA_EXTS)

    if not files:
        print(f"[!] 변환할 파일이 없음 → {INPUT_DIR} 에 동영상을 넣고 다시 실행")
        return

    print(f"[..] 모델 로드: {args.model} (device={args.device}, compute_type={args.compute_type})")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    for f in files:
        transcribe_one(f, model, args.language)


if __name__ == "__main__":
    main()
