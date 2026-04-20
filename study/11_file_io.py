import pandas as pd

# [개념] File I/O: 파일 읽고 쓰기
# 금융 예시: 거래 기록 저장 및 불러오기

df = pd.DataFrame({
    'Date': ['2024-04-19', '2024-04-20'],
    'Action': ['Buy', 'Sell'],
    'Ticker': ['Samsung', 'Samsung'],
    'Quantity': [10, 10],
    'Price': [72000, 74000]
})

# 1. CSV로 저장
filename = 'study/trade_log.csv'
df.to_csv(filename, index=False)
print(f"--- 파일 저장 완료: {filename} ---")

# 2. CSV 읽기
loaded_df = pd.read_csv(filename)
print("\n--- 불러온 데이터 ---")
print(loaded_df)

# 3. 정보 확인
print("\n--- 데이터 구조 정보 (info) ---")
loaded_df.info()
