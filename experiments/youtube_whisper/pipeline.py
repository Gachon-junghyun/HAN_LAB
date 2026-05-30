# FILE: experiments/youtube_whisper/pipeline.py
"""URL/제목/채널 → 다운로드 → Whisper 스크립트까지 한 번에.

사용 예:
    # 단건
    python pipeline.py "https://www.youtube.com/watch?v=xxxx"
    python pipeline.py "노이즈 캔슬링 작동 원리" --language ko

    # 배치 (한 줄당 URL 또는 제목, # 주석 가능)
    python pipeline.py -r list.txt --language ko

    # 채널 최신 N개 자동 큐잉 (기본 16개)
    python pipeline.py -c "@MKBHD" --language en
    python pipeline.py -c "슈카월드" -n 8 --language ko
"""
from __future__ import annotations

import argparse
from pathlib import Path

from faster_whisper import WhisperModel

from yt_download import download
from transcribe import transcribe_one
from channel_fetch import fetch_latest_videos


def load_queries(path: Path) -> list[str]:
    """리스트 파일 파싱: 한 줄당 1쿼리, '#' 주석 / 빈 줄 무시."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [s for line in lines if (s := line.strip()) and not s.startswith("#")]


def run_batch(
    queries: list[str],
    audio_only: bool = False,
    model_size: str = "large-v3",
    language: str | None = None,
    device: str = "cuda",
    compute_type: str = "float16",
) -> list[Path]:
    """여러 쿼리를 모델 1회 로드로 처리. 실패한 항목은 스킵.

    1) Whisper 모델을 먼저 1번만 로드
    2) 각 쿼리: yt-dlp 다운로드 → 전사 → .txt/.srt 저장
    """
    print(f"[init] 모델 로드: {model_size} (device={device}, compute_type={compute_type})")
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    results: list[Path] = []
    failed: list[tuple[str, str]] = []
    total = len(queries)
    for i, q in enumerate(queries, 1):
        print(f"\n=== [{i}/{total}] {q} ===")
        try:
            print("[1/2] 다운로드")
            media = download(q, audio_only=audio_only)
            print(f"\n[2/2] 전사: {media.name}")
            txt = transcribe_one(media, model, language)
            results.append(txt)
        except Exception as e:  # 한 항목 실패가 배치 전체를 막지 않게
            print(f"[ERR] {q} -> {e!r}")
            failed.append((q, repr(e)))
            continue

    print(f"\n[DONE] {len(results)}/{total} 완료")
    if failed:
        print(f"[FAILED] {len(failed)}건:")
        for q, err in failed:
            print(f"  - {q}  ({err})")
    return results


def run(query: str, **kwargs) -> Path:
    """단건 처리. 내부적으로 run_batch에 위임."""
    return run_batch([query], **kwargs)[0]


def main() -> None:
    p = argparse.ArgumentParser(description="YouTube → 다운로드 → Whisper 스크립트 파이프라인")
    p.add_argument("query", nargs="?", default=None,
                   help="YouTube URL 또는 검색할 제목 (단건). -r/-c 사용 시 생략.")
    p.add_argument("-r", "--from-file", type=Path, default=None,
                   help="리스트 파일 경로 (한 줄당 URL/제목, # 주석 가능)")
    p.add_argument("-c", "--channel", default=None,
                   help="채널 핸들/평문/URL: 최신 영상 N개를 자동 큐잉 (-n으로 개수 조정)")
    p.add_argument("-n", "--limit", type=int, default=16,
                   help="--channel 사용 시 가져올 영상 수 (기본 16)")
    p.add_argument("--keep-audio-only", action="store_true",
                   help="영상 대신 mp3로만 받기 (용량 절감)")
    p.add_argument("--model", default="large-v3",
                   help="whisper 모델: tiny / base / small / medium / large-v3 (기본: large-v3)")
    p.add_argument("--language", default=None, help="언어 강제 (예: ko, en). 미지정 시 자동 감지.")
    p.add_argument("--device", default="cuda", help="cuda / cpu / auto (기본: cuda)")
    p.add_argument("--compute-type", default="float16",
                   help="float16 / int8_float16 / int8 / float32 (기본: float16)")
    args = p.parse_args()

    # 입력 모드: query / -r / -c 중 정확히 하나만
    modes = [bool(args.query), bool(args.from_file), bool(args.channel)]
    if sum(modes) != 1:
        p.error("query / -r/--from-file / -c/--channel 중 정확히 하나만 지정할 것")

    batch_kwargs = dict(
        audio_only=args.keep_audio_only,
        model_size=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type,
    )

    if args.channel:
        print(f"[..] 채널 '{args.channel}' 최신 {args.limit}개 영상 조회 중...")
        queries = fetch_latest_videos(args.channel, args.limit)
        if not queries:
            print(f"[!] 채널에서 영상을 가져오지 못함: {args.channel}")
            return
        print(f"[..] {len(queries)}개 영상 큐잉:")
        for u in queries:
            print(f"   - {u}")
        run_batch(queries, **batch_kwargs)
    elif args.from_file:
        if not args.from_file.exists():
            p.error(f"리스트 파일 없음: {args.from_file}")
        queries = load_queries(args.from_file)
        if not queries:
            print(f"[!] 리스트 파일이 비어있음: {args.from_file}")
            return
        print(f"[..] 리스트 {len(queries)}건 로드: {args.from_file}")
        run_batch(queries, **batch_kwargs)
    else:
        run(query=args.query, **batch_kwargs)


if __name__ == "__main__":
    main()
