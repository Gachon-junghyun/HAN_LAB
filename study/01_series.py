import pandas as pd

# [개념] Series: 1차원 열 데이터 (엑셀의 한 줄)
# 금융 예시: 특정 종목의 종가 리스트

prices = [72000, 71500, 73000, 72500, 74000]
dates = ['2024-04-15', '2024-04-16', '2024-04-17', '2024-04-18', '2024-04-19']

# 인덱스를 날짜로 지정한 Series 생성
samsung = pd.Series(prices, index=dates, name="Samsung_Close")

print("--- [Series] 삼성전자 종가 ---")
print(samsung)
print(f"\n데이터 타입: {samsung.dtype}")
print(f"인덱스 확인: {samsung.index}")
