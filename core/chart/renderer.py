# FILE: core/chart/renderer.py
from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ._constants import (
    EMPTY, WICK, BULL_BODY, BEAR_BODY, DOJI_BODY,
    VOL_BULL, VOL_BEAR, DEFAULT_IND_CHARS, _CANDLE_CHARS,
    RSI_DOT, RSI_OB, RSI_OS, RSI_REF, RSI_MID,
    OBV_BULL, OBV_BEAR, OBV_ZERO, _COMBINED_IND_CHARS,
)
from ._utils import _price_to_row, _row_to_price, _fmt_price, _fmt_vol, _norm
from .indicators import add_ma, add_bollinger
from .metadata import generate_metadata


# ── 캔들 렌더링 ────────────────────────────────────────────────────────────────

def _render_candle(
    col: list[str],
    o: float, h: float, l: float, c: float,
    min_p: float, max_p: float, rows: int,
) -> None:
    """단일 캔들을 col(길이=rows 리스트)에 인플레이스로 그린다."""
    high_row = _price_to_row(h, min_p, max_p, rows)
    low_row  = _price_to_row(l, min_p, max_p, rows)
    body_top = _price_to_row(max(o, c), min_p, max_p, rows)
    body_bot = _price_to_row(min(o, c), min_p, max_p, rows)

    is_doji = abs(c - o) / (abs(o) + 1e-10) < 0.0001
    body_ch = DOJI_BODY if is_doji else (BULL_BODY if c >= o else BEAR_BODY)

    for r in range(rows):
        if body_top <= r <= body_bot:
            col[r] = body_ch
        elif high_row <= r < body_top:
            col[r] = WICK
        elif body_bot < r <= low_row:
            col[r] = WICK


# ── RSI 서브차트 ───────────────────────────────────────────────────────────────

def _compute_rsi_arr(close: pd.Series, window: int = 14) -> np.ndarray:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(window).mean()
    loss  = (-delta.clip(upper=0)).rolling(window).mean()
    rs    = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).values


def _render_rsi_subplot(
    df: pd.DataFrame,
    lw: int,
    n: int,
    rows: int = 7,
    window: int = 14,
) -> list[str]:
    """RSI 서브차트를 문자열 라인 목록으로 반환."""
    _df   = _norm(df)
    close = _df["close"].astype(float)
    rsi   = _compute_rsi_arr(close, window)

    grid   = [[EMPTY] * n for _ in range(rows)]
    ob_row  = _price_to_row(70.0, 0.0, 100.0, rows)
    os_row  = _price_to_row(30.0, 0.0, 100.0, rows)
    mid_row = _price_to_row(50.0, 0.0, 100.0, rows)

    for ci in range(n):
        val = rsi[ci]
        if np.isnan(val):
            continue
        ri = _price_to_row(float(val), 0.0, 100.0, rows)
        ch = RSI_OB if val >= 70 else (RSI_OS if val <= 30 else RSI_DOT)
        grid[ri][ci] = ch

    for ref_row, ref_ch in [(ob_row, RSI_REF), (mid_row, RSI_MID), (os_row, RSI_REF)]:
        for ci in range(n):
            if grid[ref_row][ci] == EMPTY:
                grid[ref_row][ci] = ref_ch

    label_map: dict[int, str] = {
        0: "100", ob_row: " 70", mid_row: " 50", os_row: " 30", rows - 1: "  0"
    }

    sep = " " * lw + "-+" + "-" * n
    lines: list[str] = [sep, "RSI".rjust(lw) + " |" + " " * n]
    for ri in range(rows):
        row_str = "".join(grid[ri])
        lbl     = label_map.get(ri, "").rjust(lw)
        lines.append(f"{lbl} |{row_str}")

    return lines


# ── OBV 서브차트 ───────────────────────────────────────────────────────────────

def _render_obv_subplot(
    df: pd.DataFrame,
    lw: int,
    n: int,
    rows: int = 6,
    window: int = 20,
) -> list[str]:
    """Rolling OBV 서브차트를 문자열 라인 목록으로 반환."""
    _df = _norm(df)
    if "volume" not in _df.columns:
        return []

    close      = _df["close"].astype(float)
    vol        = _df["volume"].astype(float)
    signed_vol = np.sign(close.diff().fillna(0)) * vol
    obv_roll   = pd.Series(signed_vol).rolling(window, min_periods=1).sum().values

    obv_min = float(np.nanmin(obv_roll))
    obv_max = float(np.nanmax(obv_roll))
    if obv_max == obv_min:
        return []

    scale_min = min(obv_min, 0.0)
    scale_max = max(obv_max, 0.0)
    zero_row  = _price_to_row(0.0, scale_min, scale_max, rows)
    grid      = [[EMPTY] * n for _ in range(rows)]

    for ci in range(n):
        val = obv_roll[ci]
        if np.isnan(val):
            continue
        val_row = _price_to_row(float(val), scale_min, scale_max, rows)
        ch      = OBV_BULL if val >= 0 else OBV_BEAR
        r_top   = min(zero_row, val_row)
        r_bot   = max(zero_row, val_row)
        for r in range(r_top, r_bot + 1):
            grid[r][ci] = ch

    for ci in range(n):
        if grid[zero_row][ci] == EMPTY:
            grid[zero_row][ci] = OBV_ZERO

    sep   = " " * lw + "-+" + "-" * n
    lines = [sep, f"OBV{window}d".rjust(lw) + " |" + " " * n]
    for ri in range(rows):
        lines.append(" " * lw + " |" + "".join(grid[ri]))

    return lines


# ── 메인 차트 함수 ─────────────────────────────────────────────────────────────

def plot_text_chart(
    df: pd.DataFrame,
    rows: int = 30,
    cols: Optional[int] = None,
    vol_rows: int = 6,
    indicators: Optional[Dict[str, pd.Series]] = None,
    indicator_chars: Optional[Dict[str, str]] = None,
    labels: Optional[Dict[str, Tuple[int, int]]] = None,
    show_meta: bool = False,
) -> str:
    """
    OHLCV DataFrame → 캔들 텍스트 차트.

    Parameters
    ----------
    df              : OHLCV DataFrame (컬럼명 대소문자 무관)
    rows            : 가격 차트 높이 (기본 30)
    cols            : 표시할 최근 캔들 수 (None = 전체)
    vol_rows        : 거래량 차트 높이, 0 = 생략 (기본 6)
    indicators      : 오버레이 지표 dict {'MA20': Series, ...}
    indicator_chars : 지표별 문자 override {'MA20': '.', ...}
    labels          : 패턴 라벨 dict {'눌림목': (10, 25), '돌파': (26, 30)}
    show_meta       : True 이면 하단에 자동 메타데이터 출력

    Returns
    -------
    str  바로 print() 가능한 멀티라인 문자열
    """
    _df = _norm(df)

    if cols is not None:
        _df = _df.iloc[-cols:].reset_index(drop=True)
        if indicators:
            indicators = {
                k: v.iloc[-cols:].reset_index(drop=True)
                for k, v in indicators.items()
            }

    n = len(_df)
    if n == 0:
        raise ValueError("DataFrame이 비어 있습니다. cols 값을 확인하세요.")

    o_arr = _df["open"].values.astype(float)
    h_arr = _df["high"].values.astype(float)
    l_arr = _df["low"].values.astype(float)
    c_arr = _df["close"].values.astype(float)
    min_p = float(l_arr.min())
    max_p = float(h_arr.max())

    # ── 캔들 그리드 ────────────────────────────────────────────────────────────
    grid: list[list[str]] = [[EMPTY] * n for _ in range(rows)]
    for ci in range(n):
        col = [EMPTY] * rows
        _render_candle(col, o_arr[ci], h_arr[ci], l_arr[ci], c_arr[ci],
                       min_p, max_p, rows)
        for r in range(rows):
            grid[r][ci] = col[r]

    # ── 지표 오버레이 ──────────────────────────────────────────────────────────
    if indicators:
        if indicator_chars is None:
            indicator_chars = {}
        for idx, (name, series) in enumerate(indicators.items()):
            ch  = indicator_chars.get(name, DEFAULT_IND_CHARS[idx % len(DEFAULT_IND_CHARS)])
            arr = (series.values if hasattr(series, "values")
                   else np.asarray(series)).astype(float)
            for ci in range(min(n, len(arr))):
                v = arr[ci]
                if np.isnan(v):
                    continue
                ri = _price_to_row(v, min_p, max_p, rows)
                if grid[ri][ci] not in _CANDLE_CHARS:
                    grid[ri][ci] = ch

    # ── 가격 축 레이블 ─────────────────────────────────────────────────────────
    label_row_set = {0, rows // 4, rows // 2, 3 * rows // 4, rows - 1}
    label_prices  = {r: _row_to_price(r, min_p, max_p, rows) for r in label_row_set}
    lw = max(len(_fmt_price(p)) for p in label_prices.values())

    lines: list[str] = []
    for ri in range(rows):
        row_str = "".join(grid[ri])
        lbl = (_fmt_price(label_prices[ri]).rjust(lw)
               if ri in label_row_set else " " * lw)
        lines.append(f"{lbl} |{row_str}")

    lines.append(" " * lw + "-+" + "-" * n)

    # ── 거래량 차트 ────────────────────────────────────────────────────────────
    if vol_rows > 0 and "volume" in _df.columns:
        v_arr = _df["volume"].values.astype(float)
        max_v = v_arr.max()
        vgrid = [[" "] * n for _ in range(vol_rows)]
        for ci in range(n):
            if v_arr[ci] <= 0 or max_v == 0:
                continue
            bar  = max(1, round(v_arr[ci] / max_v * vol_rows))
            v_ch = VOL_BULL if c_arr[ci] >= o_arr[ci] else VOL_BEAR
            for r in range(vol_rows - bar, vol_rows):
                vgrid[r][ci] = v_ch
        vol_max_lbl = _fmt_vol(max_v)
        for ri, vrow in enumerate(vgrid):
            lbl = vol_max_lbl.rjust(lw) if ri == 0 else " " * lw
            lines.append(f"{lbl} |{''.join(vrow)}")

    # ── 패턴 라벨 행 ──────────────────────────────────────────────────────────
    if labels:
        _syms       = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        label_row   = [" "] * n
        label_legend: dict[str, str] = {}
        for sym_idx, (pat_name, (s, e)) in enumerate(labels.items()):
            sym = _syms[sym_idx % len(_syms)]
            label_legend[sym] = pat_name
            for ci in range(max(0, s), min(n, e + 1)):
                label_row[ci] = sym
        lines.append(" " * lw + " |" + "".join(label_row))
        leg_str = "  ".join(f"[{sym}]={name}" for sym, name in label_legend.items())
        lines.append(" " * (lw + 2) + leg_str)

    # ── 범례 ──────────────────────────────────────────────────────────────────
    c_leg = (f"{BULL_BODY}=양봉  {BEAR_BODY}=음봉  {DOJI_BODY}=도지  "
             f"{WICK}=꼬리  {EMPTY}=빈칸")
    lines.append("")
    lines.append("  캔들: " + c_leg)

    if indicators:
        if indicator_chars is None:
            indicator_chars = {}
        i_parts = [
            f"[{indicator_chars.get(nm, DEFAULT_IND_CHARS[i % len(DEFAULT_IND_CHARS)])}]{nm}"
            for i, nm in enumerate(indicators)
        ]
        lines.append("  지표: " + "  ".join(i_parts))

    # ── 메타데이터 ────────────────────────────────────────────────────────────
    if show_meta:
        lines.append("")
        lines.append("── 메타데이터 " + "─" * 44)
        lines.append(generate_metadata(_df))

    return "\n".join(lines)


# ── 통합 ASCII 차트 ────────────────────────────────────────────────────────────

def plot_combined_chart(
    df: pd.DataFrame,
    rows: int = 20,
    cols: Optional[int] = None,
    vol_rows: int = 4,
    rsi_rows: int = 15,
    rsi_window: int = 14,
    obv_rows: int = 10,
    obv_window: int = 20,
    save_path: Optional[str] = None,
    save_meta: Optional[Dict] = None,
) -> str:
    """
    가격 캔들 + 거래량 + RSI + Rolling OBV 를 하나의 ASCII 차트로 반환.

    Parameters
    ----------
    df          : OHLCV DataFrame (컬럼 대소문자 무관)
    rows        : 가격 차트 높이
    cols        : 표시할 최근 캔들 수 (None = 전체)
    vol_rows    : 거래량 차트 높이
    rsi_rows    : RSI 서브차트 높이
    rsi_window  : RSI 계산 기간 (기본 14)
    obv_rows    : OBV 서브차트 높이
    obv_window  : Rolling OBV 누적 기간 (기본 20)
    save_path   : JSON 저장 경로 (None = 저장 안 함)
    save_meta   : JSON에 추가할 메타 딕셔너리
    """
    _df = _norm(df)
    if cols is not None:
        _df = _df.iloc[-cols:].reset_index(drop=True)

    n = len(_df)
    if n == 0:
        raise ValueError("DataFrame이 비어 있습니다.")

    o_arr = _df["open"].values.astype(float)
    h_arr = _df["high"].values.astype(float)
    l_arr = _df["low"].values.astype(float)
    c_arr = _df["close"].values.astype(float)
    min_p = float(l_arr.min())
    max_p = float(h_arr.max())

    # ── 가격 그리드 ────────────────────────────────────────────────────────────
    grid: list[list[str]] = [[EMPTY] * n for _ in range(rows)]
    for ci in range(n):
        col = [EMPTY] * rows
        _render_candle(col, o_arr[ci], h_arr[ci], l_arr[ci], c_arr[ci],
                       min_p, max_p, rows)
        for r in range(rows):
            grid[r][ci] = col[r]

    # ── MA/볼린저 오버레이 ─────────────────────────────────────────────────────
    indicators = {**add_ma(_df, [20, 60]), **add_bollinger(_df)}
    for name, series in indicators.items():
        ch  = _COMBINED_IND_CHARS.get(name, ".")
        arr = series.values.astype(float)
        for ci in range(min(n, len(arr))):
            v = arr[ci]
            if np.isnan(v):
                continue
            ri = _price_to_row(v, min_p, max_p, rows)
            if grid[ri][ci] not in _CANDLE_CHARS:
                grid[ri][ci] = ch

    # ── 가격 축 레이블 ─────────────────────────────────────────────────────────
    label_row_set = {0, rows // 4, rows // 2, 3 * rows // 4, rows - 1}
    label_prices  = {r: _row_to_price(r, min_p, max_p, rows) for r in label_row_set}
    lw = max(len(_fmt_price(p)) for p in label_prices.values())

    lines: list[str] = []
    for ri in range(rows):
        row_str = "".join(grid[ri])
        lbl = (_fmt_price(label_prices[ri]).rjust(lw)
               if ri in label_row_set else " " * lw)
        lines.append(f"{lbl} |{row_str}")

    lines.append(" " * lw + "-+" + "-" * n)

    # ── 거래량 바 ─────────────────────────────────────────────────────────────
    if vol_rows > 0 and "volume" in _df.columns:
        v_arr  = _df["volume"].values.astype(float)
        max_v  = v_arr.max()
        vgrid  = [[" "] * n for _ in range(vol_rows)]
        for ci in range(n):
            if v_arr[ci] <= 0 or max_v == 0:
                continue
            bar  = max(1, round(v_arr[ci] / max_v * vol_rows))
            v_ch = VOL_BULL if c_arr[ci] >= o_arr[ci] else VOL_BEAR
            for r in range(vol_rows - bar, vol_rows):
                vgrid[r][ci] = v_ch
        vol_lbl = _fmt_vol(max_v)
        for ri, vrow in enumerate(vgrid):
            lbl = vol_lbl.rjust(lw) if ri == 0 else " " * lw
            lines.append(f"{lbl} |{''.join(vrow)}")

    # ── RSI / OBV 서브차트 ─────────────────────────────────────────────────────
    if rsi_rows > 0:
        lines.extend(_render_rsi_subplot(_df, lw, n, rsi_rows, rsi_window))
    if obv_rows > 0:
        lines.extend(_render_obv_subplot(_df, lw, n, obv_rows, obv_window))

    # ── 범례 ──────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(f"  캔들: {BULL_BODY}=양봉  {BEAR_BODY}=음봉  {DOJI_BODY}=도지  {WICK}=꼬리")
    lines.append("  지표: [.]MA20  [-]MA60  [^]BB상단  [·]BB중단  [v]BB하단")
    lines.append(f"  RSI:  [{RSI_DOT}]중립  [{RSI_OB}]과매수(>70)  [{RSI_OS}]과매도(<30)  [─]30/70선  [:]50선")
    lines.append(f"  OBV:  [{OBV_BULL}]매수압력  [{OBV_BEAR}]매도압력  [─]중립선  ({obv_window}일 롤링)")

    chart_str = "\n".join(lines)

    # ── JSON 저장 ─────────────────────────────────────────────────────────────
    if save_path is not None:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chart": chart_str,
            "params": {
                "rows": rows, "cols": cols,
                "vol_rows": vol_rows,
                "rsi_rows": rsi_rows, "rsi_window": rsi_window,
                "obv_rows": obv_rows, "obv_window": obv_window,
            },
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            **(save_meta or {}),
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return chart_str
