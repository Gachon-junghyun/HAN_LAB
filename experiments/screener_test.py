# FILE: experiments/screener_test.py
from core.screener import Screener

s = Screener(cache_dir="ohlcv_cache")

# ── 1. 단일 종목 지표 확인 ─────────────────────────────────────────────────
code = "005930"  # 삼성전자
print(f"\n[{code}] RSI:", s.get_indicator(code, "rsi"))
print(f"[{code}] VWAP:", s.get_indicator(code, "vwap"))
print(f"[{code}] OBV change %:", s.get_indicator(code, "obv_change_pct"))

# ── 2. 수식 직접 평가 ─────────────────────────────────────────────────────
from core.screener import eval_expression
expr = 'rsi("005930", 14) < 60'
print(f"\n수식 [{expr}] → {eval_expression(expr)}")

# ── 3. 전체 스캔 (조건 바꿔가며 테스트) ──────────────────────────────────
expression = "rsi(_, 14) < 35 && obv_change_pct(_) > 0"
print(f"\n스크리닝: {expression}")
results = s.screen(expression, show_indicators=["rsi", "vwap", "obv_change_pct"])

matched = s.get_matched(results)
print(f"\n매칭 종목 {len(matched)}개:")
for r in matched:
    vals = " | ".join(f"{k}={v:.2f}" for k, v in r.indicator_values.items() if isinstance(v, float))
    print(f"  {r.code} {r.name}  {vals}")

# DataFrame 으로 보기
df = s.to_dataframe(results)
if not df.empty:
    print(df.to_string(index=False))
