import pandas as pd
import numpy as np

# 1. Series (가장 기본적인 1차원 데이터)
s = pd.Series([1, 2, 3, 4, 5], index=['a', 'b', 'c', 'd', 'e'])
print("--- 1. Series ---")
print(s)
print()

# 2. DataFrame - 딕셔너리 방식 (열 중심)
# "이 컬럼에는 이런 데이터가 들어있다"고 정의할 때 씁니다.
df1 = pd.DataFrame({
    'name': ['Cho', 'Kim', 'Sim', 'Joo'],
    'height': [170, 183, 189, 175],
    'weight': [65, 78, 82, 70]
})
print("--- 2. Dictionary (Column-wise) ---")
print(df1)
print()

# 3. DataFrame - 리스트의 리스트 방식 (행 중심)
# "한 줄 한 줄" 데이터를 쌓고 마지막에 제목(columns)을 붙입니다.
data2 = [
    ['Samsung', 80000, 'KRX'],
    ['SK Hynix', 180000, 'KRX'],
    ['Apple', 250000, 'NASDAQ']
]
df2 = pd.DataFrame(data2, columns=['Stock', 'Price', 'Market'])
print("--- 3. List of Lists (Row-wise) ---")
print(df2)
print()

# 4. DataFrame - 리스트 내 딕셔너리 방식 (JSON 스타일)
# 데이터 하나하나가 완성된 객체 형태일 때 유용합니다.
data3 = [
    {'id': 1, 'task': 'Study Pandas', 'status': 'Doing'},
    {'id': 2, 'task': 'Exercise', 'status': 'Todo'},
    {'id': 3, 'task': 'Read Book', 'status': 'Done'}
]
df3 = pd.DataFrame(data3)
print("--- 4. List of Dictionaries (Object-style) ---")
print(df3)
print()

# 5. 빈 DataFrame 만들고 데이터 채우기
# 데이터가 실시간으로 들어오거나 반복문 안에서 추가할 때 씁니다.
df4 = pd.DataFrame(columns=['Time', 'Value'])
df4.loc[0] = ['12:00', 10.5]
df4.loc[1] = ['13:00', 11.2]
print("--- 5. Empty & Append ---")
print(df4)
print()

# 6. NumPy를 활용한 랜덤 데이터 (연습용 대량 데이터)
# 구조 연습을 위해 가상의 데이터를 만들 때 사용합니다.
df5 = pd.DataFrame(
    np.random.randint(1, 100, size=(5, 4)), 
    columns=['Math', 'Eng', 'Sci', 'Art']
)
print("--- 6. NumPy Random Data ---")
print(df5)
print()

# 💡 꿀팁: 데이터의 정보 확인하기
print("--- DataFrame Info ---")
print(f"모양(Shape): {df1.shape}") # 몇행 몇열인지
print(f"컬럼들(Columns): {df1.columns.tolist()}") # 제목들
print(df1.describe()) # 숫자 데이터의 통계 요약 (평균, 최소, 최대 등)
