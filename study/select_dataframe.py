import pandas as pd
import numpy as np

# 6. NumPy를 활용한 랜덤 데이터 (연습용 대량 데이터)
# 구조 연습을 위해 가상의 데이터를 만들 때 사용합니다.
df5 = pd.DataFrame(
    np.random.randint(1, 100, size=(5, 4)), 
    columns=['Math', 'Eng', 'Sci', 'Art']
)
print("--- 6. NumPy Random Data ---")
print(df5)
print()

print(df5[['Math', 'Eng']])  # 특정 열 선택
print(df5[(df5['Math'] > 50) & (df5['Eng'] > 50)])  # 조건에 맞는 행 선택

df5['Total'] = df5.sum(axis=1)  # 새로운 열 추가
print(df5)