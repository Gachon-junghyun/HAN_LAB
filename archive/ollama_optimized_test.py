import os
import sys
import json
import time
import requests
import threading
import psutil
import subprocess
from pathlib import Path
from datetime import datetime

# HAN_LAB 루트 추가
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

class ResourceMonitor:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.data = []
        self.stop_event = threading.Event()
        self.thread = None

    def _get_gpu_info(self):
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            gpu_util, mem_used, mem_total = result.split(',')
            return {
                "gpu_util_percent": float(gpu_util),
                "gpu_mem_used_mib": float(mem_used),
                "gpu_mem_total_mib": float(mem_total)
            }
        except Exception:
            return {"error": "GPU info not available"}

    def _monitor(self):
        while not self.stop_event.is_set():
            sample = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(),
                "ram_percent": psutil.virtual_memory().percent,
                "ram_used_gb": psutil.virtual_memory().used / (1024**3),
                "gpu": self._get_gpu_info()
            }
            self.data.append(sample)
            time.sleep(self.interval)

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()

def run_optimized_experiment(model_name="gemma2"):
    url = "http://localhost:11434/api/generate"
    script_dir = Path(__file__).resolve().parent
    
    # 모델 체크 및 자동 선택
    try:
        tags_response = requests.get("http://localhost:11434/api/tags")
        if tags_response.status_code == 200:
            models = [m['name'] for m in tags_response.json().get('models', [])]
            if not any(model_name in m for m in models):
                model_name = models[0]
    except Exception:
        pass

    # [수정] 연애 심리 주제 프롬프트
    prompt = """
    당신은 10년 경력의 베테랑 자산관리사이자 금융 심리 전문가입니다. 시장의 파동 속에서도 흔들리지 않는 **'투자의 본질'과 '자산 관리의 철학'**을 다양한 관점에서 아주 상세하고 깊이 있게 설명해 주세요.
    """
    
    monitor = ResourceMonitor(interval=0.5)
    print(f"--- [최적화 모드] 실험 시작 (모델: {model_name}) ---")
    print(f"최적화 설정 적용: GPU 가속 강제, 컨텍스트 최적화, 금융 투자 모드\n")
    
    monitor.start()
    
    start_time = time.time()
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_gpu": -1,        # [최적화] 모든 레이어를 GPU로 전송 시도
                "num_ctx": 4096,      # [최적화] 컨텍스트 크기 고정
                "temperature": 0.8,   # [최적화] 상담에 적합한 창의성/공감도
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("상담사 답변: ", end="", flush=True)
        for line in response.iter_lines():
            if line:
                body = json.loads(line)
                chunk = body.get("response", "")
                print(chunk, end="", flush=True)
                if body.get("done"):
                    break
        print("\n")
    except Exception as e:
        print(f"\n실행 중 오류 발생: {e}")
    finally:
        monitor.stop()
        end_time = time.time()
    
    duration = end_time - start_time
    print(f"--- 실험 종료 (총 소요 시간: {duration:.2f}초) ---")
    
    log_filename = f"optimized_resource_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file = script_dir / log_filename
    
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "optimized": True,
            "duration_seconds": duration,
            "samples": monitor.data
        }, f, indent=4, ensure_ascii=False)
    
    print(f"최적화 로그 저장 완료: {log_file}")

if __name__ == "__main__":
    # gemma4 혹은 설치된 최신 모델 사용
    run_optimized_experiment("gemma4")
