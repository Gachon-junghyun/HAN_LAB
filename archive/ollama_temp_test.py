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

class TempResourceMonitor:
    def __init__(self, interval=0.5):
        self.interval = interval
        self.data = []
        self.stop_event = threading.Event()
        self.thread = None

    def _get_gpu_data(self):
        """GPU 온도, 사용률, 메모리 한 번에 가져오기"""
        try:
            cmd = "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            temp, util, mem_used, mem_total = result.split(',')
            return {
                "temp_c": float(temp),
                "util_percent": float(util),
                "mem_used_mib": float(mem_used),
                "mem_total_mib": float(mem_total)
            }
        except Exception:
            return {"error": "GPU info not available"}

    def _get_cpu_temp(self):
        """Windows WMI를 통한 CPU 온도 측정 시도"""
        try:
            cmd = "powershell -NoProfile -Command \"Get-WmiObject -Namespace root\\wmi -Class MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature\""
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if result:
                # 결과값이 켈빈 단위(1/10 단위)인 경우가 많음: (value / 10) - 273.15
                return round((float(result) / 10.0) - 273.15, 2)
        except Exception:
            pass
        return None

    def _monitor(self):
        while not self.stop_event.is_set():
            sample = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(),
                "cpu_temp_c": self._get_cpu_temp(),
                "ram_percent": psutil.virtual_memory().percent,
                "gpu": self._get_gpu_data()
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

def run_temp_experiment(model_name="gemma4"):
    url = "http://localhost:11434/api/generate"
    script_dir = Path(__file__).resolve().parent
    
    # 모델 체크
    try:
        tags_response = requests.get("http://localhost:11434/api/tags")
        if tags_response.status_code == 200:
            models = [m['name'] for m in tags_response.json().get('models', [])]
            if not any(model_name in m for m in models):
                model_name = models[0]
    except Exception:
        pass

    prompt = """
    [연애 심리 정밀 분석 요청]
    "사귄 지 1년 된 남자친구가 최근 들어 연락 횟수가 눈에 띄게 줄어들고, 만나서도 핸드폰만 봐요. 
    하지만 헤어지자고 하면 또 붙잡으면서 미안하다고 합니다. 
    이 남자의 심리 상태는 어떤 것이며, 제가 관계를 개선하기 위해 시도해볼 수 있는 대화법이나 행동 3가지를 아주 구체적으로 알려주세요."
    """
    
    monitor = TempResourceMonitor(interval=1.0) # 1초 단위로 온도 체크
    print(f"--- [온도 모니터링 모드] 실험 시작 (모델: {model_name}) ---")
    print(f"답변 생성 중 CPU/GPU 온도를 추적합니다.\n")
    
    monitor.start()
    
    start_time = time.time()
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_gpu": -1,
                "temperature": 0.75,
                "num_ctx": 4096
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
        print(f"\n오류 발생: {e}")
    finally:
        monitor.stop()
        end_time = time.time()
    
    duration = end_time - start_time
    print(f"--- 실험 종료 ({duration:.2f}초 소요) ---")
    
    # 결과 요약 출력
    if monitor.data:
        gpu_temps = [s['gpu']['temp_c'] for s in monitor.data if 'temp_c' in s['gpu']]
        if gpu_temps:
            print(f"GPU 온도: 시작 {gpu_temps[0]}°C -> 최대 {max(gpu_temps)}°C")

    # 로그 저장
    log_file = script_dir / f"temp_resource_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "duration_seconds": duration,
            "samples": monitor.data
        }, f, indent=4, ensure_ascii=False)
    
    print(f"온도 변화 로그 저장 완료: {log_file}")

if __name__ == "__main__":
    run_temp_experiment("gemma4")
