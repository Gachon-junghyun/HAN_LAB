# FILE: projects/chart_pipeline/beta/gemini_analyst.py
"""
Gemini API 차트 분석기 (Beta)
data/{날짜}/ 폴더의 차트 txt 를 읽어 Gemini 로 분석 후 gemini_analysis.txt 저장.

사용법:
    python beta/gemini_analyst.py               # 오늘 날짜 분석
    python beta/gemini_analyst.py --date 2026-04-23
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from core.ai import GeminiClient

DATA_DIR = Path(__file__).parent.parent / "data"

SYSTEM_PROMPT = (
    "당신은 한국 주식 전문 트레이더입니다. "
    "텍스트 차트를 보고 핵심만 간결하게 분석합니다. "
    "모든 답변은 한국어로 작성하세요."
)

ANALYSIS_TEMPLATE = """\
아래는 {name} ({code}) 의 텍스트 차트입니다.
전문 트레이더 관점에서 분석해주세요.

[분석 항목]
1. 현재 추세 (상승 / 하락 / 횡보)
2. 주요 지지·저항 구간
3. 거래량 패턴 해석
4. RSI / OBV 신호
5. 매매 시그널 (매수 / 매도 / 관망)
6. 리스크 요인

[차트]
{chart_text}
"""


def parse_header(text: str) -> tuple[str, str]:
    """차트 파일 첫 줄에서 name, code 추출."""
    first = text.splitlines()[0].strip()  # 예: "삼성전자 (005930)"
    if "(" in first and ")" in first:
        name = first[: first.index("(")].strip()
        code = first[first.index("(") + 1 : first.index(")")].strip()
    else:
        name, code = first, first
    return name, code


def analyze_charts(target_date: str | None = None) -> None:
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    chart_dir = DATA_DIR / target_date
    if not chart_dir.exists():
        print(f"폴더 없음: {chart_dir}")
        print("먼저 main.py 를 실행해서 차트를 생성하세요.")
        return

    chart_files = sorted(chart_dir.glob("*_chart.txt"))
    if not chart_files:
        print(f"차트 파일 없음: {chart_dir}")
        return

    print("=" * 60)
    print(f"  Gemini 차트 분석 — {target_date} ({len(chart_files)}개 종목)")
    print("=" * 60)

    client = GeminiClient(system_instruction=SYSTEM_PROMPT)
    collected: list[str] = []

    for chart_file in chart_files:
        chart_text = chart_file.read_text(encoding="utf-8")
        name, code = parse_header(chart_text)
        print(f"\n분석 중: {name} ({code})")

        prompt = ANALYSIS_TEMPLATE.format(name=name, code=code, chart_text=chart_text)
        try:
            response = client.generate(prompt)
            print(response)
            block = f"{'='*60}\n{name} ({code})\n{'='*60}\n{response}\n"
        except Exception as e:
            print(f"  오류: {e}")
            block = f"{'='*60}\n{name} ({code})\n오류: {e}\n"

        collected.append(block)

    # ── 분석 결과 저장 ─────────────────────────────────────────────
    out_path = chart_dir / "gemini_analysis.txt"
    header = f"Gemini 분석 결과 — {target_date}\n모델: gemini-2.5-flash\n\n"
    out_path.write_text(header + "\n".join(collected), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"[완료]  분석 저장: {out_path.relative_to(ROOT)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini 차트 분석기")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="분석할 날짜 (YYYY-MM-DD, 기본: 오늘)",
    )
    args = parser.parse_args()
    analyze_charts(args.date)
