# FILE: core/chart/metadata.py
from __future__ import annotations

import numpy as np
import pandas as pd

from ._utils import _fmt_price, _norm


def generate_metadata(df: pd.DataFrame) -> str:
    """
    차트 구간의 시장 상태를 텍스트로 자동 생성.
    LLM 프롬프트에 차트 텍스트와 함께 붙여 문맥을 제공한다.

    항목: MA 상태 / 볼린저 수축·확장 / 거래량 추세 / 모멘텀 / RSI / 캔들힌트
    """
    _df   = _norm(df)
    close = _df["close"]
    vol   = _df["volume"] if "volume" in _df.columns else None
    lines: list[str] = []
    last  = float(close.iloc[-1])

    # ── MA 상태 ──────────────────────────────────────────────────────────────
    ma_parts: list[str] = []
    for w in [5, 20, 60, 120]:
        if len(close) >= w:
            ma_val = float(close.rolling(w).mean().iloc[-1])
            state  = "위" if last > ma_val else "아래"
            ma_parts.append(f"MA{w} {state}({_fmt_price(ma_val)})")
    if ma_parts:
        lines.append("이평선: " + " | ".join(ma_parts))

    # ── 볼린저 밴드 수축/확장 ───────────────────────────────────────────────
    if len(close) >= 20:
        mid = close.rolling(20).mean()
        std = close.rolling(20).std()
        bw      = std * 4 / mid * 100
        bw_now  = float(bw.iloc[-1])
        bw_prev = float(bw.iloc[-10]) if len(bw) > 10 else float(bw.iloc[0])
        bb_dir  = "수축 중 ▼" if bw_now < bw_prev else "확장 중 ▲"
        bb_pos  = ""
        upper = float((mid + std * 2).iloc[-1])
        lower = float((mid - std * 2).iloc[-1])
        if last >= upper * 0.98:
            bb_pos = " / 상단 밴드 접근"
        elif last <= lower * 1.02:
            bb_pos = " / 하단 밴드 접근"
        lines.append(f"볼린저: 밴드폭 {bw_now:.1f}% ({bb_dir}){bb_pos}")

    # ── 거래량 추세 ──────────────────────────────────────────────────────────
    if vol is not None and len(vol) >= 10:
        v_rec  = float(vol.iloc[-5:].mean())
        v_prev = float(vol.iloc[-10:-5].mean())
        ratio  = v_rec / (v_prev + 1e-10)
        if   ratio >= 1.5: vstatus = f"급증 ({ratio:.1f}x) ▲▲"
        elif ratio >= 1.1: vstatus = f"증가 ({ratio:.1f}x) ▲"
        elif ratio <= 0.5: vstatus = f"급감 ({ratio:.1f}x) ▼▼"
        elif ratio <= 0.9: vstatus = f"감소 ({ratio:.1f}x) ▼"
        else:              vstatus = "보합"
        lines.append(f"거래량: {vstatus}")

    # ── 가격 모멘텀 ──────────────────────────────────────────────────────────
    mom_parts: list[str] = []
    for n, label in [(5, "5일"), (20, "20일")]:
        if len(close) >= n:
            ret = (close.iloc[-1] / close.iloc[-n] - 1) * 100
            mom_parts.append(f"{label} {ret:+.1f}%")
    if mom_parts:
        lines.append("모멘텀: " + " | ".join(mom_parts))

    # ── RSI ──────────────────────────────────────────────────────────────────
    if len(close) >= 15:
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = float((100 - 100 / (1 + rs)).iloc[-1])
        if not np.isnan(rsi):
            rsi_label = "과매수 ⚠" if rsi >= 70 else ("과매도 ⚠" if rsi <= 30 else "중립")
            lines.append(f"RSI(14): {rsi:.1f} ({rsi_label})")

    # ── 최근 캔들 패턴 힌트 ──────────────────────────────────────────────────
    if len(_df) >= 3 and all(c in _df.columns for c in ["open", "high", "low", "close"]):
        hints: list[str] = []
        c0    = _df.iloc[-1]
        c1    = _df.iloc[-2]
        body0 = abs(float(c0["close"]) - float(c0["open"]))
        wick0 = float(c0["high"]) - float(c0["low"])
        if wick0 > 0 and body0 / wick0 < 0.2:
            hints.append("도지(우유부단)")
        if float(c0["close"]) < float(c0["open"]) and float(c1["close"]) > float(c1["open"]):
            hints.append("양→음 전환")
        if float(c0["close"]) > float(c0["open"]) and float(c1["close"]) < float(c1["open"]):
            hints.append("음→양 전환")
        if hints:
            lines.append("캔들힌트: " + " / ".join(hints))

    return "\n".join(lines) if lines else "(데이터 부족 — 메타데이터 생성 불가)"
