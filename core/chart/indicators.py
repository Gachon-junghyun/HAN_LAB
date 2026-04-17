# FILE: core/chart/indicators.py
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict

from ._utils import _norm


def add_ma(df: pd.DataFrame, windows: list[int]) -> Dict[str, pd.Series]:
    """
    단순 이동평균(SMA) 딕셔너리 생성.

    Example
    -------
    indicators = add_ma(raw, [20, 60, 120])
    """
    _df = _norm(df)
    return {f"MA{w}": _df["close"].rolling(w).mean() for w in windows}


def add_bollinger(
    df: pd.DataFrame, window: int = 20, n_std: float = 2.0
) -> Dict[str, pd.Series]:
    """
    볼린저 밴드 딕셔너리 생성.

    Returns: {"BB_upper", "BB_mid", "BB_lower"}
    """
    _df = _norm(df)
    mid = _df["close"].rolling(window).mean()
    std = _df["close"].rolling(window).std()
    return {
        "BB_upper": mid + n_std * std,
        "BB_mid":   mid,
        "BB_lower": mid - n_std * std,
    }


def add_rsi_line(
    df: pd.DataFrame, window: int = 14, levels: list[float] = [30.0, 70.0]
) -> Dict[str, pd.Series]:
    """
    RSI 수평선을 가격 스케일로 변환해 오버레이용 딕셔너리로 반환.

    RSI 50 → 중간 가격, RSI 0/100 → 저가/고가 에 선형 매핑.
    LLM이 "RSI 30 아래 과매도 구간" 같은 시각적 맥락을 학습하도록 돕는 용도.
    실제 RSI 수치는 generate_metadata()가 텍스트로 별도 제공.
    """
    _df   = _norm(df)
    delta = _df["close"].diff()
    gain  = delta.clip(lower=0).rolling(window).mean()
    loss  = (-delta.clip(upper=0)).rolling(window).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - 100 / (1 + rs)

    close     = _df["close"]
    price_min = close.rolling(window * 3, min_periods=1).min()
    price_max = close.rolling(window * 3, min_periods=1).max()

    result = {}
    for lvl in levels:
        price_line = price_min + (lvl / 100.0) * (price_max - price_min)
        result[f"RSI{lvl:.0f}"] = price_line

    return result
