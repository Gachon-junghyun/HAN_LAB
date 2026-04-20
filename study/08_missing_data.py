import pandas as pd
import numpy as np

# [개념] Missing Data: 결측치(NaN) 처리
# 금융 예시: 휴장일 또는 데이터 누락 처리

df = pd.DataFrame({
    'Price': [72000, np.nan, 73000, 72500, np.nan],
    'Volume': [1500000, 1200000, np.nan, 1100000, 2000000]
})

print("--- 1. 결측치 확인 ---")
print(df.isna().sum())

print("\n--- 2. 결측치 채우기 (fillna) ---")
# 가격은 이전 가격으로 채우고(ffill), 거래량은 0으로 채우기
df['Price_Filled'] = df['Price'].fillna(method='ffill')
df['Volume_Filled'] = df['Volume'].fillna(0)
print(df)

print("\n--- 3. 결측치 삭제 (dropna) ---")
print(df.dropna())
