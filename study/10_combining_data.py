import pandas as pd

# [개념] Combining: 데이터 합치기
# 금융 예시: 주가 데이터와 기업 정보 데이터 결합

# 주가 데이터
prices = pd.DataFrame({
    'Ticker': ['Samsung', 'Hynix', 'Naver'],
    'Price': [74000, 190000, 185000]
})

# 기업 정보 데이터
info = pd.DataFrame({
    'Ticker': ['Samsung', 'Hynix', 'Kakao'],
    'Sector': ['Tech', 'Tech', 'Platform']
})

print("--- 1. Merge (SQL Join 방식) ---")
# how='left'는 왼쪽(prices) 기준, 'inner'는 교집합
merged = pd.merge(prices, info, on='Ticker', how='inner')
print(merged)

print("\n--- 2. Concat (단순 이어붙이기) ---")
df1 = prices.head(1)
df2 = prices.tail(1)
concated = pd.concat([df1, df2], axis=0).reset_index(drop=True)
print(concated)
