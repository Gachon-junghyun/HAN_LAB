import pandas as pd

# [개념] Transformations: 데이터 변환 (map, apply)
# 금융 예시: 종목 코드 포맷팅, 수익률 구간 라벨링

df = pd.DataFrame({
    'Ticker': ['Samsung', 'Hynix', 'Naver'],
    'Return': [2.5, -1.2, 5.8]
})

# 1. apply: 함수를 적용하여 새로운 값 생성
def get_label(x):
    if x > 3: return '급등'
    elif x > 0: return '상승'
    else: return '하락'

df['Status'] = df['Return'].apply(get_label)

# 2. map: 딕셔너리를 사용한 치환
sector_map = {'Samsung': '반도체', 'Hynix': '반도체', 'Naver': '플랫폼'}
df['Sector'] = df['Ticker'].map(sector_map)

# 3. astype: 데이터 타입 변환
df['Return_Int'] = df['Return'].astype(int)

print("--- 데이터 변환 결과 ---")
print(df)
