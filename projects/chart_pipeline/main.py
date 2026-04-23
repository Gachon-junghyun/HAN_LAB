# FILE: projects/chart_pipeline/main.py
"""
차트 분석 파이프라인 메인
config.txt 조건 → KOSPI 200 스크리닝 → 텍스트 차트 생성 → data/{날짜}/{번호}/ 저장

config.txt 규칙:
  - # 로 시작하는 줄: 주석 (무시)
  - 빈 줄: 무시
  - 그 외 줄: 조건 하나 (여러 줄 작성 시 각각 별도 스크리닝)
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

CHART_COLS = 80


def load_expressions(config_path: Path) -> list[str]:
    """config.txt 에서 조건 목록 반환. 한 줄 = 조건 하나."""
    lines = config_path.read_text(encoding="utf-8").splitlines()
    exprs = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    if not exprs:
        raise ValueError("config.txt 에 유효한 조건이 없습니다.")
    return exprs


def run_single(
    screener: Screener,
    expression: str,
    out_dir: Path,
    idx: int,
    total: int,
) -> None:
    """조건 하나에 대해 스크리닝 → 차트 생성 → 저장."""
    label = f"조건 {idx}/{total}"
    print(f"\n{'='*60}")
    print(f"  [{label}]  {expression}")
    print(f"{'='*60}")

    print("  KOSPI 200 스크리닝 중...")
    all_results = screener.screen(expression, verbose=True)
    matched = screener.get_matched(all_results)

    cond_dir = out_dir / str(idx)
    cond_dir.mkdir(parents=True, exist_ok=True)

    # 조건 파일 저장
    (cond_dir / "condition.txt").write_text(expression, encoding="utf-8")

    if not matched:
        print(f"\n  → 매칭 종목 없음")
        (cond_dir / "screener_result.txt").write_text(
            f"조건: {expression}\n선별 종목: 0개", encoding="utf-8"
        )
        return

    # 스크리닝 요약 출력 & 저장
    summary_lines = [
        f"스크리너 결과 — {date.today()}",
        f"조건: {expression}",
        f"선별 종목: {len(matched)}개",
        "-" * 40,
    ]
    print(f"\n  선별된 종목 ({len(matched)}개)")
    for r in matched:
        line = f"  {r.code}  {r.name}"
        if r.indicator_values:
            vals = "  |  ".join(f"{k}={v:.2f}" for k, v in r.indicator_values.items())
            line += f"  [{vals}]"
        print(line)
        summary_lines.append(line.strip())

    (cond_dir / "screener_result.txt").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )

    # 차트 생성 & 저장
    print(f"\n  차트 생성 중...")
    for r in matched:
        print(f"    {r.name} ({r.code}) 처리 중...")
        try:
            df = screener.get_ohlcv(r.code)
            if df is None or df.empty:
                print(f"      → OHLCV 없음, 건너뜀")
                continue

            chart_text = plot_combined_chart(df, cols=CHART_COLS)

            print(f"\n{'='*60}")
            print(f"  {r.name} ({r.code})")
            print(f"{'='*60}")
            print(chart_text)

            chart_path = cond_dir / f"{r.code}_chart.txt"
            chart_path.write_text(
                f"{r.name} ({r.code})\n조건: {expression}\n\n{chart_text}",
                encoding="utf-8",
            )
            print(f"\n    → 저장: {chart_path.relative_to(ROOT)}")

        except Exception as e:
            print(f"      → 오류: {e}")

    print(f"\n  [{label}] 완료 — {cond_dir.relative_to(ROOT)}")


def run_pipeline() -> None:
    print("=" * 60)
    print("  차트 분석 파이프라인")
    print("=" * 60)

    expressions = load_expressions(CONFIG_FILE)
    total = len(expressions)
    print(f"\n조건 {total}개 로드됨")
    for i, expr in enumerate(expressions, 1):
        print(f"  [{i}] {expr}")

    out_dir = DATA_DIR / date.today().strftime("%Y-%m-%d")
    screener = Screener()

    for i, expr in enumerate(expressions, 1):
        run_single(screener, expr, out_dir, i, total)

    print(f"\n{'='*60}")
    print(f"[전체 완료]  저장 위치: {out_dir.relative_to(ROOT)}")
    print(f"  다음 단계: beta/gemini_analyst.py 실행으로 AI 분석 가능")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_pipeline()
