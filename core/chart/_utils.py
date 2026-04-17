# FILE: core/chart/_utils.py
from __future__ import annotations

import pandas as pd


def _price_to_row(price: float, min_p: float, max_p: float, rows: int) -> int:
    """가격 → 그리드 행 인덱스. row 0 = 상단 = 고가."""
    p_range = max_p - min_p
    if p_range == 0:
        return rows // 2
    ratio = (price - min_p) / p_range
    row   = int((1.0 - ratio) * (rows - 1))
    return max(0, min(rows - 1, row))


def _row_to_price(row: int, min_p: float, max_p: float, rows: int) -> float:
    """그리드 행 인덱스 → 가격 (_price_to_row 역함수)."""
    ratio = 1.0 - row / max(rows - 1, 1)
    return min_p + ratio * (max_p - min_p)


def _fmt_price(price: float) -> str:
    if abs(price) >= 10_000:
        return f"{price:,.0f}"
    if abs(price) >= 1:
        return f"{price:.2f}"
    return f"{price:.5f}"


def _fmt_vol(vol: float) -> str:
    if vol >= 1e9:
        return f"{vol/1e9:.1f}B"
    if vol >= 1e6:
        return f"{vol/1e6:.1f}M"
    if vol >= 1e3:
        return f"{vol/1e3:.1f}K"
    return f"{vol:.0f}"


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명 소문자 정규화."""
    out = df.copy()
    out.columns = [c.lower() for c in out.columns]
    return out
