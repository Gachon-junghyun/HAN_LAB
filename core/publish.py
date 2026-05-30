# FILE: core/publish.py
"""작업 산출물(.md/.pptx/.pdf 등)을 외부 폴더(Google Drive 등)로 단방향 복사.

양방향 동기화가 아니라 "퍼블리시" 패턴 — 호출 시점에 한 번 push.
폰/태블릿에서 외부 디바이스로 작업 결과만 보고 싶을 때 사용.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

# 기본 확장자 — 문서/보고서/슬라이드만 (이미지, 로그, 임시 파일 제외)
DEFAULT_EXTS = (".md", ".txt", ".pptx", ".ppt", ".pdf", ".docx")


def publish_to_drive(
    source_dir: str | Path,
    dest_dir: str | Path,
    exts: Iterable[str] = DEFAULT_EXTS,
    recursive: bool = False,
) -> list[Path]:
    """source_dir 안의 지정 확장자 파일만 dest_dir로 복사 (덮어쓰기).

    - `~$` 접두 파일(Office 락 파일)은 자동 스킵
    - recursive=False(기본)면 최상위만, True면 하위 폴더까지 평탄화 복사
    - dest_dir이 없으면 생성

    Returns:
        복사된 파일의 목적지 경로 리스트
    """
    src = Path(source_dir).expanduser()
    dst = Path(dest_dir).expanduser()

    if not src.is_dir():
        raise FileNotFoundError(f"source_dir not found: {src}")

    dst.mkdir(parents=True, exist_ok=True)

    exts_set = {
        (e if e.startswith(".") else f".{e}").lower() for e in exts
    }
    pattern = "**/*" if recursive else "*"

    copied: list[Path] = []
    for path in src.glob(pattern):
        if not path.is_file():
            continue
        if path.name.startswith("~$"):  # 오피스 락 파일
            continue
        if path.suffix.lower() not in exts_set:
            continue
        target = dst / path.name
        shutil.copy2(path, target)
        copied.append(target)

    return copied


if __name__ == "__main__":
    # CLI: python -m core.publish <source> <dest> [--exts md,pptx] [--recursive]
    import argparse

    parser = argparse.ArgumentParser(description="작업 산출물 → 드라이브 퍼블리시")
    parser.add_argument("source", help="복사할 원본 폴더")
    parser.add_argument("dest", help="목적지 폴더 (예: G:\\내 드라이브\\GIC_DATA)")
    parser.add_argument(
        "--exts",
        default=",".join(e.lstrip(".") for e in DEFAULT_EXTS),
        help="복사할 확장자 (콤마 구분, 기본: md,txt,pptx,ppt,pdf,docx)",
    )
    parser.add_argument("--recursive", action="store_true", help="하위 폴더까지 검색")
    args = parser.parse_args()

    exts_list = [e.strip() for e in args.exts.split(",") if e.strip()]
    copied = publish_to_drive(
        args.source, args.dest, exts=exts_list, recursive=args.recursive
    )

    print(f"[publish] {len(copied)}개 파일 복사 완료 → {args.dest}")
    for p in copied:
        print(f"  - {p.name}")
