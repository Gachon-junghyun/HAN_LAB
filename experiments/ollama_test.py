import os
import sys
import json
import requests
from pathlib import Path

# HAN_LAB 루트 추가 (core 모듈 등을 import 할 경우 대비)
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

def main():
    prompt = """
    2. 수학·논리 추론 문제
        문제 4. (속도 비교)

        자동차 A는 1시간에 60km를 간다.
        자동차 B는 1시간 30분에 80km를 간다.

        어느 자동차가 더 빠른지

        시속 기준으로 속도가 얼마나 차이 나는지
        계산 과정을 모두 적어서 설명해라.

        문제 5. (확률 – 적어도 한 개)

        상자에 빨간 공 5개, 파란 공 3개가 있다.
        공 2개를 중복 없이 동시에 뽑을 때,
        “적어도 한 개는 빨간 공”일 확률을 계산 과정을 포함해서 구해라.

        문제 6. (논리 퍼즐)

        세 사람 A, B, C가 있다.

        A: “B가 했다.”

        B: “C가 했다.”

        C: “나는 안 했다.”
        세 사람 중 단 한 명만 진실을 말한다.
        누가 했는지, 가능한 경우를 모두 따져보면서 논리적으로 결론을 내라.

        문제 7. (함정 논리)

        한 방에 살인자 세 명이 있다.
        누군가 방에 들어와 그 중 한 명을 죽였다.
        방에서 나간 사람은 아무도 없다.
        지금 이 방 안에는 살인자가 몇 명 있는지, 이유와 함께 설명하라.


    """
    
    # 설정값
    OLLAMA_URL = "http://localhost:11434/api/generate"
    # 사용자가 명시한 모델명. (일반적으로 gemma2:9b 등이 쓰이지만 요청에 따라 gemma4로 설정)
    MODEL_NAME = "qwen3:0.6b" 

    
    print(f"--- Ollama 테스트 (모델: {MODEL_NAME}) ---")
    print(f"질문: {prompt}\n")
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True  # 스트리밍 활성화
    }
    
    try:
        # 스트리밍 방식으로 요청
        response = requests.post(OLLAMA_URL, json=payload, stream=True)
        response.raise_for_status()
        
        print("응답: ", end="", flush=True)
        for line in response.iter_lines():
            if line:
                # Ollama는 각 라인마다 JSON 객체를 반환합니다.
                body = json.loads(line)
                chunk = body.get("response", "")
                print(chunk, end="", flush=True)
                
                if body.get("done"):
                    break
        print("\n\n--- 테스트 완료 ---")
        
    except requests.exceptions.ConnectionError:
        print("\n[오류] Ollama 서버에 연결할 수 없습니다. Ollama 서비스가 실행 중인지 확인하세요.")
        print(f"URL: {OLLAMA_URL}")
    except Exception as e:
        print(f"\n[오류] 실행 중 예외 발생: {e}")

if __name__ == "__main__":
    main()
