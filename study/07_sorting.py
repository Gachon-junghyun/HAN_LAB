import pandas as pd

# [개념] Sorting: 데이터 정렬
# 금융 예시: 수익률 순위 매기기

df = pd.DataFrame({
    'Ticker': ['A', 'B', 'C', 'D', 'E'],
    'Return': [5.2, -2.1, 0.0, 12.5, -4.3]
})

print("--- 1. 값 기준 내림차순 정렬 (수익률 높은 순) ---")
print(df.sort_values(by='Return', ascending=False))

print("\n--- 2. 인덱스 기준 정렬 ---")
# 무작위로 섞인 인덱스를 다시 정렬
df_shuffled = df.sample(frac=1) # 랜덤 셔플
print("[셔플된 데이터]\n", df_shuffled)
print("\n[다시 인덱스 정렬]\n", df_shuffled.sort_index())
