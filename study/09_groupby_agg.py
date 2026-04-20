import pandas as pd

# [개념] Groupby: 그룹별 집계
# 금융 예시: 섹터별 평균 수익률 또는 월별 실적 집계

df = pd.DataFrame({
    'Sector': ['Tech', 'Tech', 'Bio', 'Bio', 'Finance'],
    'Ticker': ['Samsung', 'Hynix', 'Celltrion', 'S_Bio', 'KB'],
    'Return': [2.5, 3.8, -1.2, 0.5, 1.5]
})

print("--- 1. 섹터별 평균 수익률 ---")
sector_avg = df.groupby('Sector')['Return'].mean()
print(sector_avg)

print("\n--- 2. 섹터별 여러 통계 한 번에 보기 (agg) ---")
sector_stats = df.groupby('Sector')['Return'].agg(['mean', 'count', 'max', 'min'])
print(sector_stats)
