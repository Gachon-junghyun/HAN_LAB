# FILE: core/chart/sampler.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd

from .indicators import add_bollinger
from .metadata import generate_metadata
from .renderer import plot_text_chart


def make_training_samples(
    df: pd.DataFrame,
    pattern_labels: Dict[str, List[Tuple[int, int]]],
    context_before: int = 30,
    context_after: int = 10,
    rows: int = 25,
    vol_rows: int = 5,
    include_indicators: bool = True,
) -> List[Dict]:
    """
    패턴 라벨 구간을 기준으로 LLM 학습 샘플(chart + meta + label)을 생성한다.

    Parameters
    ----------
    df              : 전체 OHLCV DataFrame
    pattern_labels  : 패턴명 → [(절대 인덱스 start, end), ...] 리스트
                      예: {"눌림목": [(50, 70), (120, 135)], "돌파": [(71, 80)]}
    context_before  : 패턴 시작 전 추가 캔들 수 (기본 30)
    context_after   : 패턴 끝 후 추가 캔들 수 (기본 10)
    rows            : 차트 높이 (기본 25)
    vol_rows        : 거래량 차트 높이 (기본 5)
    include_indicators : True 이면 MA20/MA60/볼린저 자동 추가

    Returns
    -------
    list[dict]  각 항목: pattern, start_idx, end_idx, chart, meta

    JSONL 저장 예시
    ───────────────
        import json
        samples = make_training_samples(raw, {"눌림목": [(50, 70)]})
        with open("train.jsonl", "w", encoding="utf-8") as f:
            for s in samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\\n")
    """
    from ._utils import _norm
    _df = _norm(df)
    samples: list[dict] = []

    for pat_name, intervals in pattern_labels.items():
        for abs_start, abs_end in intervals:
            sl_start = max(0, abs_start - context_before)
            sl_end   = min(len(_df), abs_end + context_after + 1)
            win      = _df.iloc[sl_start:sl_end].reset_index(drop=True)

            rel_s   = abs_start - sl_start
            rel_e   = abs_end   - sl_start
            lbl_map = {pat_name: (rel_s, rel_e)}

            inds: Optional[Dict[str, pd.Series]] = None
            ind_chars: Optional[Dict[str, str]]  = None
            if include_indicators:
                inds, ind_chars = {}, {}
                for w, ch in [(20, "."), (60, "-")]:
                    if len(win) >= w:
                        inds[f"MA{w}"]      = win["close"].rolling(w).mean()
                        ind_chars[f"MA{w}"] = ch
                if len(win) >= 20:
                    bb = add_bollinger(win)
                    inds.update(bb)
                    ind_chars.update({"BB_upper": "^", "BB_mid": "·", "BB_lower": "v"})

            chart_txt = plot_text_chart(
                win,
                rows=rows, cols=None, vol_rows=vol_rows,
                indicators=inds, indicator_chars=ind_chars,
                labels=lbl_map, show_meta=False,
            )
            meta_txt = generate_metadata(win)

            samples.append({
                "pattern":   pat_name,
                "start_idx": abs_start,
                "end_idx":   abs_end,
                "chart":     chart_txt,
                "meta":      meta_txt,
            })

    return samples
