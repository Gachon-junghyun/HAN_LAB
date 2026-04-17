# FILE: experiments/chart_demo.py
# test_chart.py의 함수화 버전.
# ohlcv_cache/*.pkl 을 로드해서 통합 ASCII 차트를 출력한다.
#
# 사용법:
#   python experiments/chart_demo.py                          # 첫 번째 pkl, 42일
#   python experiments/chart_demo.py 005930                   # 특정 종목
#   python experiments/chart_demo.py 005930 60                # 종목 + 기간
#   python experiments/chart_demo.py 005930 60 --rows 25 --rsi 20 --obv 12
#   python experiments/chart_demo.py 005930 60 --save         # JSON 저장

import argparse
import pickle
import sys
from pathlib import Path

import pandas as pd

# HAN_LAB 루트를 sys.path에 추가 (pip install -e . 없이도 동작)
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.chart import plot_combined_chart

# ohlcv_cache 기본 경로 (GIT_CHART 레포 기준)
_DEFAULT_CACHE = Path("C:/Users/joyps/Desktop/GIT_CHART/ChartWithLlm/ohlcv_cache")


def load_pkl(code: str | None, cache_dir: Path = _DEFAULT_CACHE) -> tuple[pd.DataFrame, str]:
    """
    ohlcv_cache/ 에서 pkl 로드 후 정규화된 DataFrame과 종목 코드를 반환.

    Parameters
    ----------
    code      : 종목 코드 (예: "005930"). None 이면 첫 번째 pkl 사용.
    cache_dir : pkl 파일이 있는 폴더 경로.
    """
    if code:
        pkl_path = cache_dir / f"{code.zfill(6)}.pkl"
        if not pkl_path.exists():
            sys.exit(f"캐시 없음: {pkl_path}")
    else:
        pkls = sorted(cache_dir.glob("*.pkl"))
        if not pkls:
            sys.exit(f"캐시 폴더에 pkl 파일이 없습니다: {cache_dir}")
        pkl_path = pkls[0]

    with open(pkl_path, "rb") as f:
        df = pickle.load(f)

    # 컬럼 정규화
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = df.columns.str.lower()
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_index()

    return df, pkl_path.stem


def run_chart(
    code: str | None = None,
    cols: int = 42,
    rows: int = 20,
    vol: int = 4,
    rsi: int = 15,
    rsi_w: int = 14,
    obv: int = 10,
    obv_w: int = 20,
    save: bool = False,
    cache_dir: Path = _DEFAULT_CACHE,
) -> str:
    """
    단일 진입점: pkl 로드 → 통합 차트 생성 → 문자열 반환.

    다른 실험 코드에서 import 해서 쓸 때는 이 함수를 호출한다.
    """
    df, detected_code = load_pkl(code, cache_dir)
    cols = min(cols, len(df))
    x_df = df.iloc[-cols:].copy()

    print(f"종목: {detected_code}  |  기간: {x_df.index[0].date()} ~ {x_df.index[-1].date()}  |  {cols}거래일")
    print(f"설정: rows={rows}  vol={vol}  rsi={rsi}(w={rsi_w})  obv={obv}(w={obv_w})")
    print()

    save_path = None
    if save:
        save_dir = Path(__file__).parent / "chart_save"
        save_dir.mkdir(exist_ok=True)
        save_path = str(save_dir / f"{detected_code}_{x_df.index[-1].date()}.json")

    chart = plot_combined_chart(
        x_df,
        rows=rows, cols=cols,
        vol_rows=vol,
        rsi_rows=rsi, rsi_window=rsi_w,
        obv_rows=obv, obv_window=obv_w,
        save_path=save_path,
        save_meta={
            "ticker":  detected_code,
            "x_start": str(x_df.index[0].date()),
            "x_end":   str(x_df.index[-1].date()),
        },
    )

    if save_path:
        print(f"\n저장: {save_path}")

    return chart


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ohlcv_cache pkl → 통합 ASCII 차트 출력")
    parser.add_argument("code",    nargs="?", default=None,  help="종목 코드 (예: 005930)")
    parser.add_argument("cols",    nargs="?", type=int, default=42, help="표시 거래일 수 (기본 42)")
    parser.add_argument("--rows",  type=int, default=20,  help="가격 차트 높이 (기본 20)")
    parser.add_argument("--vol",   type=int, default=4,   help="거래량 높이 (기본 4)")
    parser.add_argument("--rsi",   type=int, default=15,  help="RSI 높이 (기본 15)")
    parser.add_argument("--rsi-w", type=int, default=14,  help="RSI 기간 (기본 14)")
    parser.add_argument("--obv",   type=int, default=10,  help="OBV 높이 (기본 10)")
    parser.add_argument("--obv-w", type=int, default=20,  help="OBV 롤링 기간 (기본 20)")
    parser.add_argument("--save",  action="store_true",   help="experiments/chart_save/ 에 JSON 저장")
    parser.add_argument("--cache", default=str(_DEFAULT_CACHE), help="ohlcv_cache 폴더 경로")
    args = parser.parse_args()

    chart = run_chart(
        code=args.code,
        cols=args.cols,
        rows=args.rows,
        vol=args.vol,
        rsi=args.rsi,
        rsi_w=args.rsi_w,
        obv=args.obv,
        obv_w=args.obv_w,
        save=args.save,
        cache_dir=Path(args.cache),
    )
    print(chart)
