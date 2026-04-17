# FILE: experiments/finance_download_test.py
import logging
from core.finance.ohlcv import OHLCVDownloader
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    # 1. 다운로더 초기화 (3개월치 데이터, 테스트용 캐시 폴더)
    downloader = OHLCVDownloader(cache_dir="test_ohlcv_cache", period="3mo", workers=4)

    # 2. 개별 종목 테스트 (삼성전자)
    ticker = {"code": "005930", "name": "삼성전자"}
    print(f"--- 단일 종목 테스트: {ticker['name']} ---")
    code, ok, msg = downloader.download_one(ticker, force=True)
    if ok:
        print(f"성공: {msg}")
    else:
        print(f"실패: {msg}")

    # 3. 엑셀에서 티커 로드 테스트 (기존 경로가 있다면)
    excel_path = Path("../GIT_CHART/ChartWithLlm/data/kospi200.xlsx")
    if excel_path.exists():
        print(f"\n--- 엑셀 로드 테스트: {excel_path} ---")
        try:
            tickers = downloader.load_tickers_from_excel(excel_path)
            # 상위 3개만 테스트 다운로드
            downloader.download_all(tickers[:3], force=True)
        except Exception as e:
            print(f"엑셀 로드 중 오류: {e}")
    else:
        print(f"\n--- 엑셀 파일을 찾을 수 없어 로드 테스트 스킵 ({excel_path}) ---")

if __name__ == "__main__":
    main()
