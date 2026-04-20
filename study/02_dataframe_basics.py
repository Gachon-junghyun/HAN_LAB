import pandas as pd

# [개념] DataFrame: 2차원 표 구조 (여러 개의 Series가 모인 형태)
# 금융 예시: 시가(Open), 고가(High), 저가(Low), 종가(Close) 표 생성

ohlc_data = {
    'Open': [71000, 72000, 72500, 73000, 73500],
    'High': [72500, 72500, 73500, 74000, 74500],
    'Low': [70500, 71500, 72000, 72500, 73000],
    'Close': [72000, 71500, 73000, 72500, 74000]
}
dates = pd.to_datetime(['2024-04-15', '2024-04-16', '2024-04-17', '2024-04-18', '2024-04-19'])

df = pd.DataFrame(ohlc_data, index=dates)

print("--- [DataFrame] 주가 OHLC 표 ---")
print(df)
print(f"\n전체 행/열 크기: {df.shape}")
print(f"컬럼명 확인: {df.columns}")
