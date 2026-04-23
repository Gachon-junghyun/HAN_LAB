# FILE: core/screener/indicators.py
#
# 스크리닝용 스칼라 지표 엔진 — 모든 함수는 df → float 반환.
# core/chart/indicators.py 와 목적이 다름:
#   chart/indicators.py  → 차트 오버레이용 Series 반환
#   screener/indicators.py → 최신 시점 스칼라 값 반환 (조건 비교용)

import numpy as np
import pandas as pd

# ── 트레이드 컨텍스트 (백테스트 전용) ─────────────────────────────────────
# peak_drawdown 이 진입 시점 정보를 읽기 위해 사용.
# backtest 루프에서 set_trade_context / clear_trade_context 호출.
_trade_context: dict = {}


def set_trade_context(entry_idx: int, entry_price: float) -> None:
    _trade_context["entry_idx"] = entry_idx
    _trade_context["entry_price"] = entry_price


def clear_trade_context() -> None:
    _trade_context.clear()


# ── OBV ────────────────────────────────────────────────────────────────────
def obv(df: pd.DataFrame, window: int = 10) -> float:
    """window 기간 내 OBV 누적값"""
    d = df.tail(window + 1).copy()
    close = d["close"].values
    vol = d["volume"].values
    vals = [0.0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            vals.append(vals[-1] + vol[i])
        elif close[i] < close[i - 1]:
            vals.append(vals[-1] - vol[i])
        else:
            vals.append(vals[-1])
    return float(vals[-1])


def obv_change_pct(df: pd.DataFrame, window: int = 10) -> float:
    """OBV 전일 대비 변화율 (%)"""
    d = df.tail(window + 2).copy()
    close = d["close"].values
    vol = d["volume"].values
    vals = [0.0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            vals.append(vals[-1] + vol[i])
        elif close[i] < close[i - 1]:
            vals.append(vals[-1] - vol[i])
        else:
            vals.append(vals[-1])
    if len(vals) < 2 or vals[-2] == 0:
        return 0.0
    return float((vals[-1] - vals[-2]) / abs(vals[-2]) * 100)


# ── RSI ────────────────────────────────────────────────────────────────────
def rsi(df: pd.DataFrame, period: int = 14) -> float:
    """RSI (Wilder's smoothing)"""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    val = (100 - 100 / (1 + rs)).iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


# ── CCI ────────────────────────────────────────────────────────────────────
def cci(df: pd.DataFrame, period: int = 20) -> float:
    """CCI = (TP - SMA(TP)) / (0.015 * MAD(TP))"""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    val = ((tp - sma) / (0.015 * mad)).iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


# ── MACD ───────────────────────────────────────────────────────────────────
def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    close = df["close"]
    val = (close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()).iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def macd_signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    close = df["close"]
    macd_line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    val = macd_line.ewm(span=signal, adjust=False).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def macd_hist(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    return macd(df, fast, slow, signal) - macd_signal(df, fast, slow, signal)


# ── Bollinger Bands ────────────────────────────────────────────────────────
def bb_upper(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> float:
    close = df["close"]
    val = (close.rolling(period).mean() + std * close.rolling(period).std()).iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def bb_lower(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> float:
    close = df["close"]
    val = (close.rolling(period).mean() - std * close.rolling(period).std()).iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def bb_mid(df: pd.DataFrame, period: int = 20) -> float:
    val = df["close"].rolling(period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def bb_pctb(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> float:
    """%B = (close - lower) / (upper - lower)"""
    upper = bb_upper(df, period, std)
    lower = bb_lower(df, period, std)
    curr = float(df["close"].iloc[-1])
    if upper == lower:
        return 0.5
    return (curr - lower) / (upper - lower)


# ── Stochastic ─────────────────────────────────────────────────────────────
def stoch_k(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> float:
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    val = (100 * (df["close"] - low_min) / (high_max - low_min)).iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


def stoch_d(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> float:
    low_min = df["low"].rolling(k_period).min()
    high_max = df["high"].rolling(k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    val = k.rolling(d_period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


# ── Williams %R ────────────────────────────────────────────────────────────
def williams_r(df: pd.DataFrame, period: int = 14) -> float:
    high_max = df["high"].rolling(period).max()
    low_min = df["low"].rolling(period).min()
    val = (-100 * (high_max - df["close"]) / (high_max - low_min)).iloc[-1]
    return float(val) if not np.isnan(val) else -50.0


# ── MFI ────────────────────────────────────────────────────────────────────
def mfi(df: pd.DataFrame, period: int = 14) -> float:
    """Money Flow Index (volume-weighted RSI)"""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0.0).rolling(period).sum()
    neg_mf = mf.where(delta <= 0, 0.0).rolling(period).sum()
    val = (100 - 100 / (1 + pos_mf / neg_mf)).iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


# ── ADX ────────────────────────────────────────────────────────────────────
def adx(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr_s
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    val = dx.ewm(alpha=1 / period, min_periods=period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


# ── 이동평균 ───────────────────────────────────────────────────────────────
def sma(df: pd.DataFrame, period: int = 20) -> float:
    val = df["close"].rolling(period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


def ema(df: pd.DataFrame, period: int = 20) -> float:
    val = df["close"].ewm(span=period, adjust=False).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


# ── ATR ────────────────────────────────────────────────────────────────────
def atr(df: pd.DataFrame, period: int = 14) -> float:
    close = df["close"]
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - close.shift()).abs(),
        (df["low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    val = tr.rolling(period).mean().iloc[-1]
    return float(val) if not np.isnan(val) else 0.0


# ── ROC ────────────────────────────────────────────────────────────────────
def roc(df: pd.DataFrame, period: int = 12) -> float:
    close = df["close"]
    val = (close.iloc[-1] - close.iloc[-1 - period]) / close.iloc[-1 - period] * 100
    return float(val) if not np.isnan(val) else 0.0


# ── VWAP ───────────────────────────────────────────────────────────────────
def vwap(df: pd.DataFrame, period: int = 20) -> float:
    d = df.tail(period)
    tp = (d["high"] + d["low"] + d["close"]) / 3
    vol_sum = d["volume"].sum()
    if vol_sum == 0:
        return float(d["close"].iloc[-1])
    return float((tp * d["volume"]).sum() / vol_sum)


# ── 가격/거래량 유틸 ────────────────────────────────────────────────────────
def close(df: pd.DataFrame) -> float:
    return float(df["close"].iloc[-1])


def close_change_pct(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    prev = float(df["close"].iloc[-2])
    curr = float(df["close"].iloc[-1])
    return (curr - prev) / prev * 100 if prev else 0.0


def volume(df: pd.DataFrame) -> float:
    return float(df["volume"].iloc[-1])


def volume_change_pct(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.0
    prev = float(df["volume"].iloc[-2])
    curr = float(df["volume"].iloc[-1])
    return (curr - prev) / prev * 100 if prev else 0.0


# ── 트레일링 스탑 (백테스트 sell_expression 전용) ───────────────────────────
def peak_drawdown(df: pd.DataFrame, threshold: float = -5.0) -> bool:
    """
    진입 이후 최고 종가 대비 현재 낙폭이 threshold(%) 이하이면 True.
    백테스트 루프에서 set_trade_context() 호출 후 사용.
    스크리닝 모드에서는 항상 False 반환.
    """
    if "entry_idx" not in _trade_context:
        return False
    entry_idx = _trade_context["entry_idx"]
    closes = df["close"]
    if len(closes) <= entry_idx:
        return False
    closes_from_entry = closes.iloc[entry_idx:]
    if closes_from_entry.empty:
        return False
    peak = float(closes_from_entry.max())
    curr = float(closes.iloc[-1])
    if peak <= 0:
        return False
    return (curr - peak) / peak * 100 <= threshold


# ── 레지스트리 ─────────────────────────────────────────────────────────────
INDICATOR_REGISTRY: dict[str, tuple] = {
    "obv":              (obv,              {"window": 10}),
    "obv_change_pct":   (obv_change_pct,   {"window": 10}),
    "rsi":              (rsi,              {"period": 14}),
    "cci":              (cci,              {"period": 20}),
    "macd":             (macd,             {"fast": 12, "slow": 26, "signal": 9}),
    "macd_signal":      (macd_signal,      {"fast": 12, "slow": 26, "signal": 9}),
    "macd_hist":        (macd_hist,        {"fast": 12, "slow": 26, "signal": 9}),
    "bb_upper":         (bb_upper,         {"period": 20, "std": 2.0}),
    "bb_lower":         (bb_lower,         {"period": 20, "std": 2.0}),
    "bb_mid":           (bb_mid,           {"period": 20}),
    "bb_pctb":          (bb_pctb,          {"period": 20, "std": 2.0}),
    "stoch_k":          (stoch_k,          {"k_period": 14, "d_period": 3}),
    "stoch_d":          (stoch_d,          {"k_period": 14, "d_period": 3}),
    "williams_r":       (williams_r,       {"period": 14}),
    "mfi":              (mfi,              {"period": 14}),
    "adx":              (adx,              {"period": 14}),
    "sma":              (sma,              {"period": 20}),
    "ema":              (ema,              {"period": 20}),
    "atr":              (atr,              {"period": 14}),
    "roc":              (roc,              {"period": 12}),
    "vwap":             (vwap,             {"period": 20}),
    "close":            (close,            {}),
    "close_change_pct": (close_change_pct, {}),
    "volume":           (volume,           {}),
    "volume_change_pct":(volume_change_pct,{}),
    # 백테스트 sell_expression 전용
    "peak_drawdown":    (peak_drawdown,    {"threshold": -5.0}),
}


def compute_indicator(name: str, df: pd.DataFrame, shift: int = 0, **kwargs) -> float:
    """
    이름으로 지표 계산. shift=N이면 N일 전 시점 기준.

    예) compute_indicator("rsi", df, period=14)
        compute_indicator("obv", df, window=17, shift=1)  # 어제 기준
    """
    if name not in INDICATOR_REGISTRY:
        raise ValueError(f"Unknown indicator: {name}. Available: {list(INDICATOR_REGISTRY)}")
    func, defaults = INDICATOR_REGISTRY[name]
    params = {**defaults, **kwargs}
    if shift > 0:
        if len(df) <= shift:
            return 0.0
        df = df.iloc[:-shift]
    return func(df, **params)


def list_indicators() -> list[str]:
    return list(INDICATOR_REGISTRY.keys())
