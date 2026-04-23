# FILE: core/screener/screener.py
#
# KOSPI 200 전체 종목 스캔 엔진.
# OHLCVDownloader pkl 캐시가 있으면 우선 사용 → 없으면 yfinance 직접 다운로드.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

from .expression import (
    clear_cache,
    evaluate,
    parse_expression,
)
from .indicators import INDICATOR_REGISTRY, compute_indicator

# kospi200.xlsx 위치 — core/ 루트에 이미 존재
_KOSPI200_XLSX = Path(__file__).resolve().parent.parent / "kospi200.xlsx"


@dataclass
class ScreenResult:
    code: str
    name: str
    matched: bool
    indicator_values: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


class Screener:
    """
    KOSPI 200 전체 종목에 대해 수식 조건을 평가하는 스크리너.

    사용 예:
        screener = Screener()
        results = screener.screen("rsi(_, 14) < 30 && obv_change_pct(_) > 0")
        matched = screener.get_matched(results)
    """

    def __init__(self):
        self._kospi200: Optional[pd.DataFrame] = None

    # ── 종목 리스트 ────────────────────────────────────────────────────────
    @property
    def kospi200(self) -> pd.DataFrame:
        if self._kospi200 is None:
            self._kospi200 = self._load_kospi200()
        return self._kospi200

    def _load_kospi200(self) -> pd.DataFrame:
        if not _KOSPI200_XLSX.exists():
            raise FileNotFoundError(f"kospi200.xlsx not found: {_KOSPI200_XLSX}")
        df = pd.read_excel(
            _KOSPI200_XLSX,
            usecols="A,B",
            skiprows=1,
            nrows=200,
            header=None,
            names=["code", "name"],
        )
        df["code"] = df["code"].astype(str).str.zfill(6)
        df["name"] = df["name"].fillna(df["code"])
        return df.reset_index(drop=True)

    # ── OHLCV 로드 (pkl 캐시 우선 → yfinance 폴백) ───────────────────────
    def get_ohlcv(self, code: str) -> pd.DataFrame:
        """항상 yfinance 에서 최신 데이터 다운로드"""
        df = yf.download(f"{code}.KS", period="1y", progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        return df

    # ── 단일 종목 지표 조회 ────────────────────────────────────────────────
    def get_indicator(self, code: str, name: str, **kwargs) -> Optional[float]:
        df = self.get_ohlcv(code)
        if df.empty:
            return None
        return compute_indicator(name, df, **kwargs)

    def get_all_indicators(self, code: str) -> Dict[str, float | str]:
        df = self.get_ohlcv(code)
        if df.empty:
            return {}
        results = {}
        for name in INDICATOR_REGISTRY:
            try:
                results[name] = compute_indicator(name, df)
            except Exception:
                results[name] = "ERROR"
        return results

    # ── 전체 스캔 ──────────────────────────────────────────────────────────
    def screen(
        self,
        expression: str,
        show_indicators: Optional[List[str]] = None,
        verbose: bool = True,
    ) -> List[ScreenResult]:
        """
        수식 조건으로 KOSPI 200 전체 스캔.

        Args:
            expression:      평가할 수식 (예: "rsi(_, 14) < 30 && vwap(_) > close(_)")
            show_indicators: 매칭 종목에 추가로 계산할 지표 이름 목록
            verbose:         진행 상황 출력 여부
        """
        clear_cache()
        ast = parse_expression(expression)
        results: List[ScreenResult] = []
        stocks = self.kospi200
        total = len(stocks)

        for idx, row in stocks.iterrows():
            code, name = row["code"], row["name"]
            if verbose:
                print(f"\r  [{idx + 1}/{total}] {name}    ", end="", flush=True)

            try:
                matched = bool(evaluate(ast, target_code=code))
                sr = ScreenResult(code=code, name=name, matched=matched)
                if matched and show_indicators:
                    df = self.get_ohlcv(code)
                    for ind in show_indicators:
                        try:
                            sr.indicator_values[ind] = compute_indicator(ind, df)
                        except Exception:
                            sr.indicator_values[ind] = None
            except Exception as e:
                sr = ScreenResult(code=code, name=name, matched=False, error=str(e))

            results.append(sr)
            clear_cache()

        if verbose:
            print(f"\n[완료] {sum(r.matched for r in results)}개 종목 매칭")
        return results

    def screen_natural(
        self,
        query: str,
        api_key: Optional[str] = None,
        verbose: bool = True,
    ) -> Tuple[str, List[ScreenResult]]:
        """
        자연어 쿼리 → 수식 변환 → 스캔.

        Returns:
            (변환된_수식, 스캔_결과_리스트)
        """
        from .nlp import natural_to_expression, load_name_mapping
        load_name_mapping(self.kospi200)
        success, expression, _ = natural_to_expression(query, api_key=api_key)
        if not success:
            raise ValueError(f"수식 변환 실패: {expression}")
        print(f"[변환] {expression}")
        return expression, self.screen(expression, verbose=verbose)

    # ── 유틸리티 ───────────────────────────────────────────────────────────
    def get_matched(self, results: List[ScreenResult]) -> List[ScreenResult]:
        return [r for r in results if r.matched]

    def to_dataframe(
        self, results: List[ScreenResult], matched_only: bool = True
    ) -> pd.DataFrame:
        items = self.get_matched(results) if matched_only else results
        rows = []
        for r in items:
            row: dict = {"code": r.code, "name": r.name, "matched": r.matched}
            row.update(r.indicator_values)
            if r.error:
                row["error"] = r.error
            rows.append(row)
        return pd.DataFrame(rows)
