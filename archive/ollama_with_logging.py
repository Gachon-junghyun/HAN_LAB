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
        """nvidia-smi를 사용하여 GPU 정보를 가져옵니다."""
        try:
            # CSV 포맷으로 필요한 정보만 추출
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

def run_experiment(model_name="gemma2"):
    url = "http://localhost:11434/api/generate"
    # 파일 저장 경로를 스크립트 위치 기준으로 절대 경로화
    script_dir = Path(__file__).resolve().parent
    
    # 먼저 모델이 있는지 확인
    try:
        tags_response = requests.get("http://localhost:11434/api/tags")
        if tags_response.status_code == 200:
            models = [m['name'] for m in tags_response.json().get('models', [])]
            # gemma2:latest 등 풀네임 대응
            if not any(model_name in m for m in models):
                print(f"[경고] '{model_name}' 모델을 찾을 수 없습니다. 설치된 모델: {models}")
                print(f"가장 먼저 검색된 모델 '{models[0]}'으로 시도합니다.")
                model_name = models[0]
    except Exception as e:
        print(f"Ollama 서버 확인 실패: {e}")

    prompt = "데이터 과학과 머신러닝의 차이점을 GPU와 메모리 관점에서 아주 길게 설명해줘."
    
    monitor = ResourceMonitor(interval=0.5)
    print(f"--- Experiment Start (Model: {model_name}) ---")
    print(f"Monitoring resources while generating response...\n")
    
    monitor.start()
    
    start_time = time.time()
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True
        }
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("Response: ", end="", flush=True)
        for line in response.iter_lines():
            if line:
                body = json.loads(line)
                chunk = body.get("response", "")
                print(chunk, end="", flush=True)
                if body.get("done"):
                    break
        print("\n")
    except Exception as e:
        print(f"\nError during inference: {e}")
    finally:
        monitor.stop()
        end_time = time.time()
    
    duration = end_time - start_time
    print(f"--- Experiment Finished (Duration: {duration:.2f}s) ---")
    
    # 로그 저장 (절대 경로 사용)
    log_filename = f"resource_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file = script_dir / log_filename
    
    log_data = {
        "model": model_name,
        "duration_seconds": duration,
        "samples": monitor.data
    }
    
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4, ensure_ascii=False)
    
    print(f"Log saved to: {log_file}")

if __name__ == "__main__":
    # 사용자가 설치한 모델명으로 실행 (예: gemma2, gemma2:2b 등)
    # 설치된 모델이 없다면 'ollama run gemma2'를 먼저 실행하세요.
    target_model = "gemma4"
    run_experiment(target_model)
