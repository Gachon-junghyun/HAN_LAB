# FILE: HAN_LAB/experiments/upload_yuhan_report.py
"""유한양행(000100) 2026Q2 바이오 리포트 산출물 6개를 마운트된 구글 드라이브 폴더로 퍼블리시.

주의:
- 이 스크립트는 Google Drive API를 호출하지 않는다.
- OS에 동기화된 드라이브 폴더(예: 윈도우 G:\내 드라이브\..., 맥 ~/Google Drive/...)에
  shutil로 단방향 복사할 뿐이다. 드라이브 데스크탑 앱이 설치/동기화되어 있어야 한다.
- 인증/토큰/시크릿 불필요.

사용법:
    # 1) 드라이브 루트 환경변수 설정 (예: 윈도우)
    set HAN_LAB_DRIVE_ROOT=G:\내 드라이브\HAN_LAB_PUBLISH

    # 2) 실행
    python experiments/upload_yuhan_report.py

    # 인자로 직접 줄 수도 있음:
    python experiments/upload_yuhan_report.py --drive-root "G:\내 드라이브\HAN_LAB_PUBLISH"
    python experiments/upload_yuhan_report.py --dest-name custom_folder_name
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core.publish import publish_to_drive

# 산출물 경로(고정) — 유한양행 리포트가 항상 떨어지는 위치
SOURCE_DIR = Path(
    r"C:\Users\fivep\OneDrive\Desktop\mvp\research_Mvp"
    r"\llm_outputs\2026-05-15\bio_2026q2"
)

# 드라이브상 목적 폴더명: <섹터_분기>_<종목>_<생성일>
DEFAULT_DEST_NAME = "bio_2026q2_yuhan_2026-05-15"

# 기대하는 산출물 파일명 — 누락 시 경고만(블로킹 X)
EXPECTED_FILES = {
    "industry_landscape.md",
    "state_report_yuhan.md",
    "upgrade_diff.md",
    "disclosure_000100.md",
    "valuation_000100.md",
    "business_000100.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="유한양행 리포트 → 드라이브 퍼블리시")
    parser.add_argument(
        "--drive-root",
        default=os.environ.get("HAN_LAB_DRIVE_ROOT"),
        help="드라이브 루트 폴더(환경변수 HAN_LAB_DRIVE_ROOT 대체 가능)",
    )
    parser.add_argument(
        "--dest-name",
        default=DEFAULT_DEST_NAME,
        help=f"드라이브 안 목적 폴더명 (기본: {DEFAULT_DEST_NAME})",
    )
    parser.add_argument(
        "--source",
        default=str(SOURCE_DIR),
        help=f"산출물 폴더 경로 (기본: {SOURCE_DIR})",
    )
    args = parser.parse_args()

    if not args.drive_root:
        print(
            "[ERROR] 드라이브 루트가 지정되지 않았습니다.\n"
            "  방법 1) 환경변수: set HAN_LAB_DRIVE_ROOT=<드라이브경로>\n"
            "  방법 2) 인자: --drive-root \"<드라이브경로>\"",
            file=sys.stderr,
        )
        return 2

    source = Path(args.source).expanduser()
    if not source.is_dir():
        print(f"[ERROR] 산출물 폴더가 없습니다: {source}", file=sys.stderr)
        return 2

    # 기대 파일 누락 체크(경고만)
    present = {p.name for p in source.glob("*.md")}
    missing = EXPECTED_FILES - present
    if missing:
        print(f"[WARN] 누락된 파일 {len(missing)}개: {sorted(missing)}")

    dest = Path(args.drive_root).expanduser() / args.dest_name

    print(f"[publish] source : {source}")
    print(f"[publish] dest   : {dest}")
    print(f"[publish] exts   : .md (6 files expected)")
    print()

    copied = publish_to_drive(
        source_dir=source,
        dest_dir=dest,
        exts=[".md"],
        recursive=False,
    )

    print(f"[publish] {len(copied)}개 파일 복사 완료 → {dest}")
    for p in copied:
        print(f"  - {p.name}")

    return 0 if copied else 1


if __name__ == "__main__":
    sys.exit(main())
