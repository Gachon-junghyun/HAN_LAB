import pandas as pd

# [개념] Filtering: 조건에 맞는 데이터 찾기
# 금융 예시: 급등주 찾기 또는 특정 가격대 종목 필터링

df = pd.DataFrame({
    'Ticker': ['Samsung', 'SK_Hynix', 'Naver', 'Kakao', 'Hyundai'],
    'Price': [74000, 190000, 185000, 48000, 250000],
    'Change_Pct': [2.5, -1.2, 5.8, 0.5, -3.0]
})

print("--- 1. 단일 조건: 변동률 3% 이상인 종목 ---")
bullish = df[df['Change_Pct'] >= 3.0]
print(bullish)

print("\n--- 2. 복합 조건: 가격 10만 이상이면서 변동률이 양수인 종목 ---")
complex_filter = df[(df['Price'] >= 100000) & (df['Change_Pct'] > 0)]
print(complex_filter)

print("\n--- 3. query() 사용: 가독성 좋은 필터링 ---")
query_filter = df.query('Price < 50000 or Change_Pct > 5')
print(query_filter)
