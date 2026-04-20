import pandas as pd

# [개념] Indexing & Selection: 원하는 데이터만 쏙 뽑기
# 금융 예시: 특정 날짜나 특정 가격 컬럼만 선택하기

df = pd.DataFrame({
    'Samsung': [72000, 71500, 73000],
    'SK_Hynix': [180000, 178000, 182000]
}, index=['2024-04-15', '2024-04-16', '2024-04-17'])

print("--- 1. 컬럼 선택 (Series 반환) ---")
print(df['Samsung'])

print("\n--- 2. 여러 컬럼 선택 (DataFrame 반환) ---")
print(df[['Samsung', 'SK_Hynix']])

print("\n--- 3. loc: 이름을 사용한 행 선택 ---")
print(df.loc['2024-04-16'])

print("\n--- 4. iloc: 순서(숫자)를 사용한 행 선택 ---")
print(df.iloc[0]) # 첫 번째 행

print("\n--- 5. 특정 행과 열 동시에 뽑기 ---")
print(f"16일 삼성전자 가격: {df.loc['2024-04-16', 'Samsung']}")
