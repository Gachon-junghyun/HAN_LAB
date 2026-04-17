# FILE: experiments/gemini_test.py
import os
import sys
from pathlib import Path

# HAN_LAB 루트 추가
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.ai import GeminiClient

def main():
    print("--- GeminiClient 테스트 ---")
    
    # 1. 클라이언트 초기화
    # 환경변수(GEMINI_API_KEY)가 설정되어 있어야 합니다.
    try:
        gemini = GeminiClient(
            model_name="gemini-2.5-flash",
            system_instruction="너는 주식 분석 전문가야. 답변은 항상 '형식: [결론] - [이유]' 순서로 짧게 답변해줘."
        )
        
        # 2. 텍스트 생성 테스트
        prompt = "KOSPI 200 지수가 상승할 때 유리한 종목 3가지만 알려줘."
        print(f"질문: {prompt}")
        
        response = gemini.generate(prompt)
        print(f"응답:\n{response}")
        
        # 3. 스트리밍 테스트
        print("\n--- 스트리밍 테스트 ---")
        prompt_stream = "워렌 버핏의 투자 철학을 한 문장으로 말해줘."
        print(f"질문: {prompt_stream}")
        print("응답: ", end="", flush=True)
        for chunk in gemini.generate(prompt_stream, stream=True):
            print(chunk, end="", flush=True)
        print()

    except ValueError as e:
        print(f"오류: {e}")
    except Exception as e:
        print(f"기타 오류: {e}")

if __name__ == "__main__":
    main()
