# FILE: core/screener/nlp.py
#
# 자연어 → 수식 변환 (GeminiClient 재사용)
# 예) "RSI 과매도이고 거래량 급증한 종목" → "rsi(_, 14) < 30 && volume_change_pct(_) > 50"

from __future__ import annotations

import os
from typing import Optional

from core.ai.gemini import GeminiClient
from .indicators import INDICATOR_REGISTRY

# 종목명 → 코드 매핑 (Screener.screen_natural() 에서 load_name_mapping 호출)
_NAME_TO_CODE: dict[str, str] = {}


def load_name_mapping(kospi200_df=None) -> None:
    """KOSPI 200 DataFrame 에서 종목명→코드 매핑 로드"""
    global _NAME_TO_CODE
    if kospi200_df is not None:
        for _, row in kospi200_df.iterrows():
            _NAME_TO_CODE[str(row["name"])] = str(row["code"])


def _build_system_prompt() -> str:
    indicator_lines = []
    for name, (_, defaults) in INDICATOR_REGISTRY.items():
        params = ", ".join(f"{k}={v}" for k, v in defaults.items())
        indicator_lines.append(f"  {name}(code, {params})" if params else f"  {name}(code)")

    stock_examples = "\n".join(
        f'  "{name}" → "{code}"' for name, code in list(_NAME_TO_CODE.items())[:50]
    )

    return f"""당신은 주식 기술적 분석 수식 변환기입니다.
사용자의 자연어 조건을 아래 수식 문법으로 변환하세요.

## 수식 문법
- 인디케이터 호출: indicator_name("종목코드", param1, param2, ...)
- N일 전 값: 모든 파라미터 뒤에 마지막 인자로 shift 추가
  예) obv(_, 17, 1) → 어제 기준 OBV(window=17)
- 비교: >, <, >=, <=, ==, !=
- 논리: && (AND), || (OR), ! (NOT)
- 스크리닝 모드 (전체 종목): 종목코드 자리에 _ 사용
- 배열 인덱싱([0] 등) 절대 사용 금지 — shift 사용

## 사용 가능한 인디케이터
{chr(10).join(indicator_lines)}

## 종목 코드 예시
{stock_examples}

## 규칙
1. 수식만 출력. 설명·마크다운 없이.
2. 종목명이 언급되면 종목코드로 변환.
3. "전체 종목", "모든 종목", "KOSPI200" 등이면 _ 사용.
4. 특정 종목 없이 조건만 말하면 _ 사용.
5. 파라미터 미명시 시 기본값 사용.
6. 수식은 한 줄로 출력.

## 예시
입력: "RSI 과매도이고 거래량 급증한 종목 찾아줘"
출력: rsi(_, 14) < 30 && volume_change_pct(_) > 50

입력: "MACD 골든크로스 종목"
출력: macd(_, 12, 26, 9) > macd_signal(_, 12, 26, 9) && macd_hist(_, 12, 26, 9) > 0

입력: "볼린저 하단 터치하면서 RSI 30 이하인 종목"
출력: close(_) <= bb_lower(_, 20, 2.0) && rsi(_, 14) <= 30

입력: "어제 OBV 음수였다가 오늘 양수로 전환한 종목"
출력: obv(_, 17) > 0 && obv(_, 17, 1) < 0
"""


def natural_to_expression(
    user_input: str,
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> tuple[bool, str, Optional[str]]:
    """
    자연어를 수식으로 변환.

    Returns:
        (success, expression_or_error, raw_response)
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return (False, "GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", None)

    try:
        client = GeminiClient(
            api_key=key,
            model_name=model,
            system_instruction=_build_system_prompt(),
        )
        text = client.generate(user_input).strip().replace("```", "").strip()
        if not text:
            return (False, "Gemini 빈 응답", None)
        return (True, text, text)
    except Exception as e:
        return (False, f"Gemini API 오류: {e}", None)
