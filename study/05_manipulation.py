import pandas as pd

# [개념] Manipulation: 데이터 수정 및 컬럼 추가/삭제
# 금융 예시: 수익률 계산 및 변동성 컬럼 생성

df = pd.DataFrame({
    'Close': [72000, 71500, 73000, 72500, 74000]
})

# 1. 컬럼 추가 (수익률)
df['Return'] = df['Close'].pct_change() * 100

# 2. 계산된 값으로 새 컬럼 추가 (이동평균)
df['MA3'] = df['Close'].rolling(window=3).mean()

# 3. 데이터 수정 (일괄 10% 할증 - 가상 상황)
df['Target_Price'] = df['Close'] * 1.1

# 4. 컬럼 삭제
df_dropped = df.drop(columns=['Target_Price'])

print("--- 데이터 수정 및 추가 결과 ---")
print(df)
