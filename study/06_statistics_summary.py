import pandas as pd

# [개념] Statistics: 요약 통계 정보 확인
# 금융 예시: 포트폴리오의 평균 수익률, 위험도(표준편차) 파악

df = pd.DataFrame({
    'Samsung_Ret': [0.5, -1.2, 2.3, 0.8, -0.5],
    'Hynix_Ret': [1.5, -2.0, 3.5, 1.2, -1.0]
})

print("--- 1. 전체 요약 통계 (Describe) ---")
print(df.describe())

print("\n--- 2. 개별 통계값 ---")
print(f"평균 수익률:\n{df.mean()}")
print(f"\n수익률 표준편차(변동성):\n{df.std()}")
print(f"\n최대 수익률: {df['Samsung_Ret'].max()}")

print("\n--- 3. 상관관계 (종목 간 커플링 확인) ---")
print(df.corr())
