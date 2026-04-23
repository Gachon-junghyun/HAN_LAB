# FILE: projects/chart_pipeline/main.py
"""
차트 분석 파이프라인 메인
config.txt 조건 → KOSPI 200 스크리닝 → 텍스트 차트 생성 → data/{날짜}/ 저장
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.screener import Screener
from core.chart import plot_combined_chart

CONFIG_FILE = Path(__file__).parent / "config.txt"
DATA_DIR = Path(__file__).parent / "data"

# 최근 캔들 표시 개수 (None = 전체)
CHART_COLS = 80


def load_expression(config_path: Path) -> str:
    """config.txt 에서 # 주석 제거 후 expression 반환."""
    lines = config_path.read_text(encoding="utf-8").splitlines()
    expr_lines = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    if not expr_lines:
        raise ValueError("config.txt 에 유효한 expression 이 없습니다.")
    return " ".join(expr_lines)


def make_output_dir() -> Path:
    """오늘 날짜 폴더 생성 후 반환."""
    out_dir = DATA_DIR / date.today().strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def run_pipeline() -> None:
    print("=" * 60)
    print("  차트 분석 파이프라인")
    print("=" * 60)

    # ── 1. 조건 로드 ──────────────────────────────────────────────
    expression = load_expression(CONFIG_FILE)
    print(f"\n[1] 스크리너 조건: {expression}\n")

    # ── 2. 스크리닝 ───────────────────────────────────────────────
    screener = Screener()
    print("[2] KOSPI 200 스크리닝 중... (수 분 소요될 수 있습니다)")
    all_results = screener.screen(expression, verbose=True)
    matched = screener.get_matched(all_results)

    if not matched:
        print("\n조건을 만족하는 종목이 없습니다.")
        return

    # ── 3. 출력 폴더 & 스크리닝 요약 저장 ─────────────────────────
    out_dir = make_output_dir()

    summary_lines = [
        f"스크리너 결과 — {date.today()}",
        f"조건: {expression}",
        f"선별 종목: {len(matched)}개",
        "-" * 40,
    ]
    print(f"\n[3] 선별된 종목 ({len(matched)}개)")
    for r in matched:
        line = f"  {r.code}  {r.name}"
        if r.indicator_values:
            vals = "  |  ".join(f"{k}={v:.2f}" for k, v in r.indicator_values.items())
            line += f"  [{vals}]"
        print(line)
        summary_lines.append(line.strip())

    summary_path = out_dir / "screener_result.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\n  → 저장: {summary_path.relative_to(ROOT)}")

    # ── 4. 차트 생성 & 저장 ───────────────────────────────────────
    print(f"\n[4] 텍스트 차트 생성 중...\n")
    for r in matched:
        print(f"  {r.name} ({r.code}) 처리 중...")
        try:
            df = screener.get_ohlcv(r.code)
            if df is None or df.empty:
                print(f"    → OHLCV 없음, 건너뜀")
                continue

            chart_text = plot_combined_chart(df, cols=CHART_COLS)

            # 콘솔 출력
            print(f"\n{'='*60}")
            print(f"  {r.name} ({r.code})")
            print(f"{'='*60}")
            print(chart_text)

            # 파일 저장
            chart_path = out_dir / f"{r.code}_chart.txt"
            chart_path.write_text(
                f"{r.name} ({r.code})\n조건: {expression}\n\n{chart_text}",
                encoding="utf-8",
            )
            print(f"\n  → 저장: {chart_path.relative_to(ROOT)}")

        except Exception as e:
            print(f"    → 오류: {e}")

    print(f"\n{'='*60}")
    print(f"[완료]  저장 위치: {out_dir.relative_to(ROOT)}")
    print(f"        총 {len(matched)}개 종목 차트 생성")
    print(f"\n  다음 단계: beta/gemini_analyst.py 실행으로 AI 분석 가능")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_pipeline()
