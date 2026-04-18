import os
import sys
import json
import time
import psutil
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# 온도 경고 임계값 (설정 가능)
GPU_TEMP_LIMIT = 85.0  # 85도 이상 시 경고
CPU_TEMP_LIMIT = 90.0  # 90도 이상 시 경고

class ServerMonitor:
    def __init__(self, log_interval=5.0):
        self.log_interval = log_interval
        self.running = True
        self.script_dir = Path(__file__).resolve().parent
        self.log_file = self.script_dir / f"server_24h_log_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def get_gpu_data(self):
        """GPU 온도 및 사용량 가져오기"""
        try:
            cmd = "nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            temp, util, mem = result.split(',')
            return {
                "temp": float(temp),
                "util": float(util),
                "mem_mib": float(mem)
            }
        except Exception:
            return {"temp": 0, "util": 0, "mem_mib": 0, "error": "GPU Not Found"}

    def get_cpu_temp(self):
        """Windows WMI를 통한 CPU 온도 측정 시도 (지원 안될 시 0 반환)"""
        try:
            # PowerShell을 통해 WMI ThermalZone 정보 쿼리
            cmd = "powershell -NoProfile -Command \"Get-WmiObject -Namespace root\\wmi -Class MSAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature\""
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if result:
                # 결과값이 켈빈 단위(1/10 단위)인 경우가 많음: (value / 10) - 273.15
                temp_c = (float(result) / 10.0) - 273.15
                return round(temp_c, 2)
        except Exception:
            pass
        return 0  # 측정이 불가능한 경우

    def log_status(self):
        print(f"--- 24시간 모니터링 시작 (로그: {self.log_file.name}) ---")
        print("CTRL+C를 누르면 종료됩니다.\n")
        
        try:
            while self.running:
                gpu = self.get_gpu_data()
                cpu_temp = self.get_cpu_temp()
                ram = psutil.virtual_memory()
                cpu_usage = psutil.cpu_percent()

                status = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu": {"usage_percent": cpu_usage, "temp": cpu_temp},
                    "gpu": gpu,
                    "ram_percent": ram.percent
                }

                # 콘솔 출력
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"GPU: {gpu['temp']}°C ({gpu['util']}%) | "
                      f"CPU Usage: {cpu_usage}% | "
                      f"RAM: {ram.percent}%", end='\r')

                # 온도 경고 알림
                if gpu['temp'] > GPU_TEMP_LIMIT:
                    print(f"\n[경고] GPU 온도가 너무 높습니다! 현재: {gpu['temp']}°C")
                if cpu_temp > CPU_TEMP_LIMIT:
                    print(f"\n[경고] CPU 온도가 너무 높습니다! 현재: {cpu_temp}°C")

                # 파일 저장 (JSON Lines 포맷)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(status) + "\n")

                time.sleep(self.log_interval)
        except KeyboardInterrupt:
            print("\n모니터링을 종료합니다.")
            self.running = False

if __name__ == "__main__":
    # 5초 간격으로 서버 상태 기록
    monitor = ServerMonitor(log_interval=5.0)
    monitor.log_status()
