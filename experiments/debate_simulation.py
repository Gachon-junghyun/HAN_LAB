# FILE: experiments/debate_simulation.py
import sys
import random
import logging
from pathlib import Path
from typing import List, Dict

# 프로젝트 루트 경로 추가 (core 모듈 임포트용)
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.ai import OllamaClient

# 로그 설정 (실행 시 불필요한 로그 억제)
logging.basicConfig(level=logging.ERROR)

class DebateAgent:
    def __init__(self, name: str, role: str, model_name: str, personality_temp: float = 0.7):
        self.name = name
        self.role = role
        self.model_name = model_name
        self.client = OllamaClient(model_name=model_name)
        self.personality_temp = personality_temp # 성격에 따른 온도 조절

    def speak(self, topic: str, context: str, turn_type: str) -> str:
        # 시스템 프롬프트 강화: "절대로 타인의 논리에 동조하지 말 것" 명시
        system_prompt = (
            f"당신은 '{self.name}'({self.role})입니다.\n"
            f"토론 주제: '{topic}'\n"
            f"지침: 상대방의 논리에 휩쓸리지 말고, 반드시 자신의 캐릭터를 유지하며 {turn_type}을 하세요."
        )
        
        # 프롬프트에 현재 화자를 한 번 더 강조
        prompt = (
            f"이전 토론 내용:\n{context}\n\n"
            f"당신은 {self.name}입니다. {self.role}의 관점에서 답변을 생성하세요."
        )
        
        # options에 temperature 등을 넘길 수 있다면 추가 (OllamaClient 구현에 따라 다름)
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            # 모델의 '확증 편향'을 방지하기 위해 정제된 호출
            response = self.client.chat(messages) 
            return response.strip()
        except Exception as e:
            return f"(발언 오류: {e})"

def run_debate(topic: str, agent_configs: List[Dict[str, str]], default_model: str = "qwen3:0.6b", rounds: int = 5):
    """토론 시뮬레이션 실행 및 파일 저장"""
    
    agents = [
        DebateAgent(
            cfg['name'], 
            cfg['role'], 
            cfg.get('model', default_model)
        ) 
        for cfg in agent_configs
    ]
    
    debate_history = []
    output_lines = []

    def log_and_print(text: str):
        print(text)
        output_lines.append(text)

    log_and_print(f"\n{'='*50}")
    log_and_print(f"토론 주제: {topic}")
    log_and_print(f"참여자 및 모델:")
    for a in agents:
        log_and_print(f"- {a.name}: {a.client.model_name}")
    log_and_print(f"{'='*50}\n")

    last_speaker = None
    
    for i in range(rounds):
        if i == 0:
            current_agent = random.choice(agents)
            turn_type = "기조 연설 및 주장"
        else:
            current_agent = random.choice([a for a in agents if a != last_speaker])
            turn_type = "반박 및 추가 의견"

        context_str = "\n".join(debate_history[-3:])
        
        log_and_print(f"[{i+1}라운드] {current_agent.name} ({current_agent.role}) - {turn_type}:")
        content = current_agent.speak(topic, context_str, turn_type)
        log_and_print(f"> {content}\n")
        
        debate_history.append(f"{current_agent.name}: {content}")
        last_speaker = current_agent

    footer = f"{'='*50}\n토론이 종료되었습니다.\n{'='*50}"
    log_and_print(footer)

    # 파일 저장
    log_file = _ROOT / "experiments" / "debate_log.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"\n[알림] 토론 내용이 저장되었습니다: {log_file}")

if __name__ == "__main__":
    # 토론 주제 설정: 시뮬레이션 우주론
    topic = "우리가 살고 있는 이 현실은 고도로 발달된 외계 문명이 만든 시뮬레이션인가?"

    # 에이전트별 개성 있는 페르소나와 모델 할당
    participants = [
        {
            "name": "기술 거물 일론", 
            "role": "컴퓨터 그래픽의 발전 속도를 보아 우리가 기저 현실에 있을 확률은 거의 없다고 믿는 기술 낙관주의자",
            "model": "qwen3:0.6b"
        },
        {
            "name": "수행자 법정", 
            "role": "현실이든 가상이든 그것은 중요하지 않으며, 모든 것은 마음의 투영(일체유심조)일 뿐이라는 관점",
            "model": "gemma2:2b"
        },
        {
            "name": "회의주의 과학자", 
            "role": "관측 불가능한 가설은 과학적 가치가 없으며, 시뮬레이션 우주론은 현대판 창조론에 불과하다고 비판하는 실증주의자",
            "model": "gemma4:latest"
        },
        {
            "name": "시스템 해커", 
            "role": "데자뷔나 우연의 일치를 시스템의 '글리치'라고 믿으며, 이 가상 현실에서 탈출할 방법을 찾는 음모론자",
            "model": "qwen3:0.6b"
        }
    ]

    try:
        # 8라운드 동안 치열하게 토론 진행
        run_debate(topic, participants, rounds=8)
    except KeyboardInterrupt:
        print("\n토론이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")

