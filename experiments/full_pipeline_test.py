# FILE: experiments/full_pipeline_test.py
import os
import sys
from pathlib import Path
import pandas as pd
import logging

# HAN_LAB 루트 추가
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.finance import OHLCVDownloader
from core.chart import plot_combined_chart
from core.ai import GeminiClient

# 로깅 설정 (INFO 레벨로 필요한 정보만 출력)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def load_system_prompt(prompt_path: Path) -> str:
    """archive/ex_prompt 파일 내용을 로드합니다."""
    if not prompt_path.exists():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def run_pipeline(ticker_code: str = "005930", ticker_name: str = "삼성전자"):
    print(f"\n=== [파이프라인 시작] 종목: {ticker_name}({ticker_code}) ===")

    # 1. 데이터 다운로드 (core.finance)
    cache_dir = _ROOT / "ohlcv_cache"
    downloader = OHLCVDownloader(cache_dir=cache_dir, period="1y")
    
    print("\n[Step 1] 데이터 확인 및 다운로드...")
    # auto_update=True 이므로 오늘 이미 받았다면 다시 받지 않음
    ok, success, msg = downloader.download_one({"code": ticker_code, "name": ticker_name})
    if not success:
        print(f"데이터 준비 실패: {msg}")
        return

    # 2. 차트 생성 (core.chart)
    print("\n[Step 2] ASCII 차트 생성 중...")
    pkl_path = cache_dir / f"{ticker_code}.pkl"
    df = pd.read_pickle(pkl_path)
    
    # 최근 42거래일 데이터 추출
    cols = 42
    x_df = df.iloc[-cols:].copy()
    
    # 차트 그리기 (문자열로 반환)
    chart_str = plot_combined_chart(
        x_df,
        rows=20, cols=cols,
        vol_rows=4,
        rsi_rows=15,
        obv_rows=10,
        save_meta={
            "ticker": ticker_code,
            "name": ticker_name,
            "start": str(x_df.index[0].date()),
            "end": str(x_df.index[-1].date())
        }
    )
    print("차트 생성 완료.")

    # 3. Gemini 분석 (core.ai + archive/ex_prompt)
    print("\n[Step 3] Gemini AI 분석 요청 중...")
    try:
        # 시스템 프롬프트 로드
        ex_prompt = load_system_prompt(_ROOT / "archive" / "ex_prompt")
        
        # AI 클라이언트 초기화
        ai = GeminiClient(system_instruction=ex_prompt)
        
        # 분석 요청 메시지 구성
        user_message = f"""## Stock: {ticker_name} ({ticker_code})
## Analysis Period: {x_df.index[0].date()} ~ {x_df.index[-1].date()}

### Combined ASCII Chart
{chart_str}

Please provide your technical analysis and prediction according to the rules in the system prompt.
"""
        # 결과 생성 (스트리밍으로 실시간 출력)
        print("-" * 50)
        print("AI 분석 결과:")
        for chunk in ai.generate(user_message, stream=True):
            print(chunk, end="", flush=True)
        print("\n" + "-" * 50)

    except Exception as e:
        print(f"AI 분석 중 오류 발생: {e}")

if __name__ == "__main__":
    # 실행 인자가 있으면 해당 종목 코드를 사용, 없으면 삼성전자
    target_code = sys.argv[1] if len(sys.argv) > 1 else "005930"
    target_name = sys.argv[2] if len(sys.argv) > 2 else "Samsung Electronics"
    
    run_pipeline(target_code, target_name)
