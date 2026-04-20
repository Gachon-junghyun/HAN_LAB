<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 나 그거 pandas Series 랑 dataframe 뭐 그거 좀 개념 알려줘봐

판다스에서 Series는 “1차원 열 하나짜리 데이터”, DataFrame은 “Series 여러 개가 모인 2차원 표 구조”라고 생각하면 된다.[^1_1][^1_2][^1_3][^1_4]

## Series: 1차원 데이터

- 리스트에 “이름표(인덱스)”가 붙어 있는 1차원 배열이라고 보면 된다.[^1_5][^1_6][^1_1]
- 보통 엑셀로 치면 **열 하나**에 해당하고, 인덱스(행 번호 역할)와 값으로 구성된다.[^1_3][^1_7][^1_4]
- 예: `pd.Series([10, 20, 30], index=['a','b','c'])` 이런 식으로 “값 + 인덱스” 한 줄짜리 구조.[^1_1][^1_5]

간단히 말해: “행 인덱스가 달린 리스트 하나”라고 이해하면 편하다.[^1_6][^1_5]

## DataFrame: 2차원 표 구조

- 행과 열로 이루어진 2차원 테이블 구조, 엑셀 시트 한 장이랑 비슷하다.[^1_7][^1_5][^1_3]
- 여러 개의 Series가 같은 행 인덱스를 공유하면서 옆으로 붙어 있는 형태라고 보면 된다.[^1_2][^1_3][^1_7][^1_1]
- 각 열은 이름(컬럼명)을 가지고 있고, 열마다 타입이 달라도 된다 (숫자열, 문자열 섞어서 가능).[^1_2][^1_3][^1_1]

즉: “컬럼 이름과 행 인덱스가 붙어 있는, Series들의 묶음 표”가 DataFrame이다.[^1_4][^1_3][^1_2]

## 둘의 핵심 차이

| 구분 | Series | DataFrame |
| :-- | :-- | :-- |
| 차원 | 1차원 배열 구조[^1_1][^1_5][^1_6] | 2차원 테이블 구조[^1_2][^1_5][^1_3] |
| 컬럼 개수 | 열 1개만 존재 (자기 자신)[^1_8][^1_7] | 열이 1개 이상, 여러 개 가능[^1_8][^1_2] |
| 구성 요소 | 인덱스 + 값[^1_5][^1_4] | 행 인덱스 + 열 이름 + 값[^1_2][^1_3] |
| 관계 | DataFrame의 한 컬럼이라고 볼 수 있음[^1_1][^1_7] | 여러 Series가 모여서 만들어짐[^1_1][^1_2][^1_3] |

## 직관적 예시 한 번

- Series 느낌:
    - “학생들 키만 모아놓은 리스트” → `키` 열 하나.[^1_5][^1_1]
- DataFrame 느낌:
    - “학생 이름, 키, 몸무게, 학년까지 다 있는 표” → 이름/키/몸무게/학년 Series들이 옆으로 붙은 표.[^1_3][^1_1][^1_2]

원하면 `pd.Series`, `pd.DataFrame` 코드 예시랑 인덱싱(`loc`, `iloc`) 차이까지도 간단히 정리해줄게.
<span style="display:none">[^1_10][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://siloam72761.tistory.com/entry/Python-Series와-Dataframe의-개념-사용법-차이점-in-Pandas

[^1_2]: https://hyyoka-ling-nlp.tistory.com/3

[^1_3]: https://brownbears.tistory.com/640

[^1_4]: https://velog.io/@okorion/Pandas-입문과-SeriesDataFrame-기본기

[^1_5]: https://blog.naver.com/j7youngh/222802558038

[^1_6]: https://wikidocs.net/205999

[^1_7]: https://bloofer.net/124

[^1_8]: https://tbr74.tistory.com/entry/판다스-Dataframe과-Series의-차이점

[^1_9]: https://velog.io/@gggggeun1/Pandas-에-대해

[^1_10]: https://nittaku.tistory.com/110


---

# 많이 사용하는 문법으로 예시 들어줘

현업/실전에서 많이 쓰는 것들 위주로, Series / DataFrame 섞어서 예시로 보여줄게.[^2_1][^2_2][^2_3]

## 1. 기본 생성 \& 구조 보기

```python
import pandas as pd

# Series 만들기
s = pd.Series([10, 20, 30], index=['a', 'b', 'c'])

# DataFrame 만들기 (딕셔너리 → 표)
df = pd.DataFrame({
    'name': ['Cho', 'Kim', 'Sim', 'Joo'],
    'height': [170, 183, 189, 175]
})
```

```python
# 위에서부터 n개 / 아래에서부터 n개
df.head()      # 기본 5개[web:14][web:16]
df.tail(3)     # 마지막 3개[web:14][web:16]

# 행, 열 크기
df.shape       # (행 개수, 열 개수)[web:16]
```


## 2. 열/행 선택 (인덱싱 기본)

```python
# 열 선택 (Series 또는 DataFrame)
df['height']           # height 열 (Series)[web:12][web:13]
df[['name', 'height']] # 열 여러 개 (DataFrame)[web:12]

# 행 선택: loc(라벨), iloc(숫자 위치)
df.loc[^2_0]              # 인덱스 라벨이 0인 행[web:18]
df.iloc[^2_1]             # 두 번째 행 (0-based)[web:18]

# 행+열 같이
df.loc[0, 'name']      # 0번 행의 name 값[web:18]
df.iloc[1, 0]          # (1, 0) 위치 값[web:18]
```

Series도 비슷하게 인덱스/슬라이스해서 쓰면 된다.[^2_4][^2_5]

## 3. 조건 필터링 (자주 씀)

```python
# 키가 180 이상인 사람만
df[df['height'] >= 180][web:12][web:16]

# 여러 조건 & / |
df[(df['height'] >= 180) & (df['height'] <= 190)][web:16]
```

SQL WHERE 느낌으로 많이 쓰고, 로지컬 연산자 쓸 때 괄호 꼭 쳐야 한다.[^2_3][^2_6]

## 4. 열 추가 / 수정 / 삭제

```python
# 새 열 추가
df['age'] = [21, 23, 35, 27][web:1]
df['bmi'] = df['height'] / (1.75 ** 2)  # 예시 계산[web:13][web:16]

# 열 수정 (기존 열에 연산)
df['height'] = df['height'] + 1[web:16]

# 열 삭제
df = df.drop(columns=['bmi'])[web:16]
```

Series도 그냥 `s * 2`, `s + 10` 이런 식으로 연산 많이 한다.[^2_4]

## 5. 기본 통계 / 요약

```python
df['height'].mean()      # 평균[web:14][web:17]
df['height'].max()       # 최댓값[web:14][web:17]
df['height'].min()       # 최솟값[web:14]
df['height'].sum()       # 합계[web:14]
df['height'].describe()  # count, mean, std, min, quartile, max 한 번에[web:14]
```

DataFrame 전체에 `df.describe()` 걸면 숫자형 컬럼들에 대해 요약 통계를 한 번에 본다.[^2_7]

## 6. 정렬

```python
# height 기준 오름차순 / 내림차순 정렬
df.sort_values('height', ascending=True)[web:16]
df.sort_values('height', ascending=False)[web:16]

# 인덱스로 정렬
df.sort_index()[web:18]
```


## 7. 결측치 처리 (실전에서 필수)

```python
# 결측 여부 확인
df.isna()         # True/False 테이블[web:16]
df['height'].isna()[web:16]

# 결측 행/열 제거
df.dropna()       # 결측 있는 행 제거[web:16]

# 결측값 채우기
df['height'] = df['height'].fillna(df['height'].mean())[web:16]
```


## 8. groupby (집계)

```python
# 예시: 반별 평균 키
# df: columns = ['class', 'name', 'height']
df.groupby('class')['height'].mean()  # Series로 각 반 평균 키[web:16]

# 여러 통계 한 번에
df.groupby('class')['height'].agg(['mean', 'max', 'min'])[web:16]
```

이건 진짜 데이터 분석 쪽에서 제일 많이 쓰는 축에 든다.[^2_3]

## 9. 여러 데이터 합치기 (concat / merge)

```python
# 위아래로 붙이기 (row 방향)
result_row = pd.concat([df1, df2], axis=0)[web:15][web:16]

# 좌우로 붙이기 (column 방향)
result_col = pd.concat([df1, df2], axis=1)[web:15]

# SQL JOIN처럼 합치기
merged = pd.merge(df1, df2, how='left', on='id')[web:16]
```


***

실제로 코딩할 때 많이 쓰는 패턴은:

1. `pd.read_csv`로 DataFrame 읽기
2. `head()/info()/describe()`로 구조 파악
3. `[]`, `loc/iloc`, 조건 필터링으로 서브셋 뽑기
4. `assign` 또는 `df['새컬럼'] = ...` 으로 파생변수 만들기
5. `groupby().agg()`로 통계 뽑기
6. 필요하면 `merge/concat`으로 테이블 결합

이 흐름이 제일 자주 쓰이는 루틴이라 생각하면 된다.[^2_6][^2_1][^2_3]

원하면 너가 실제로 쓰고 싶은 케이스(예: 주가 데이터, 트레이딩 기록 csv 같은 거)로 예제 한 번 같이 짜보자.
<span style="display:none">[^2_10][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://codevang.tistory.com/337

[^2_2]: https://velog.io/@okorion/Pandas-입문과-SeriesDataFrame-기본기

[^2_3]: https://blog.naver.com/salboli_shw/222998908462

[^2_4]: https://deephive.tistory.com/26

[^2_5]: https://wikidocs.net/295453

[^2_6]: https://wikidocs.net/268952

[^2_7]: https://velog.io/@nochesita/Pandas-3-DataFrame-메소드

[^2_8]: https://siloam72761.tistory.com/entry/Python-Series와-Dataframe의-개념-사용법-차이점-in-Pandas

[^2_9]: https://sahayana.tistory.com/20

[^2_10]: https://blog.naver.com/ej_stage/223918183814


---

# 기본 더 있나?

앞에서 얘기한 것들 말고, “기본기”에서 자주 보는 것들 몇 개만 더 붙여볼게.[^3_1][^3_2][^3_3]

## 1. 파일 입출력 (csv 읽기/쓰기)

```python
import pandas as pd

# CSV 파일 읽기
df = pd.read_csv('data.csv')                  # 기본[web:19][web:20]
df = pd.read_csv('data.csv', encoding='utf-8')  # 한글 문제 날 때[web:19]

# CSV 파일로 저장
df.to_csv('out.csv', index=False)             # index=False 많이 씀[web:19][web:20]
```

데이터 분석 시작할 때 거의 무조건 `read_csv`부터 들어간다고 보면 된다.[^3_2][^3_4]

## 2. info, value_counts 같은 구조 파악

```python
df.info()                 # 컬럼 타입, 널 여부, 메모리 사용량[web:19][web:25]
df.describe()             # 숫자형 컬럼 통계 요약[web:12]

df['col'].value_counts()  # 카테고리 값 분포 (ex. 종목코드, 레이블 등)[web:20]
df['col'].unique()        # 유니크 값들[web:20]
df['col'].nunique()       # 유니크 개수[web:12]
```

EDA 시작할 때 info / describe / value_counts 이 세트로 많이 쓴다.[^3_1][^3_2]

## 3. sum(axis), 타입 변환

```python
# 행/열 방향 합계
df.sum()            # 열 기준 합계 (기본 axis=0)[web:12]
df.sum(axis=1)      # 행 기준 합계[web:12]

# 타입 변환
df['col'] = df['col'].astype(int)     # 정수형 변환[web:12]
df['col'] = df['col'].astype(str)     # 문자열 변환[web:12]
```

특히 금융 데이터에서 문자열 숫자(예: "1,000") 처리하고, 행 기준 수익률 합산 같은 거 할 때 axis 잘 써야 한다.[^3_3][^3_1]

## 4. 인덱스/컬럼 이름 다루기

```python
# 인덱스 / 컬럼 보기
df.index        # RangeIndex(...) 등[web:19]
df.columns      # Index([...]) 형태[web:19]

# 컬럼 이름 바꾸기
df = df.rename(columns={'old': 'new'})[web:19]

# 인덱스 리셋
df = df.reset_index(drop=True)        # 기존 인덱스 날리고 0,1,2,...로[web:19]
```

groupby나 merge 많이 하다 보면 인덱스 꼬여서 `reset_index(drop=True)` 엄청 자주 쓰게 된다.[^3_2][^3_3]

## 5. map / apply (가볍게)

```python
# Series 단위: map
df['cat_num'] = df['category'].map({'A': 0, 'B': 1, 'C': 2})[web:21]

# 한 컬럼에 함수 적용
df['name_len'] = df['name'].apply(len)[web:13]

# DataFrame 전체에 element-wise 적용하고 싶을 때는 applymap (자주 쓰진 않지만 개념)
df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)[web:21]
```

실전에서는 “라벨 → 숫자 매핑”, “문자열 전처리” 이런 데서 많이 쓰인다.[^3_5][^3_6]

***

여기까지가:

- 파일 입출력
- 구조/타입 확인
- 기본 통계/집계
- 인덱스/컬럼 조작
- map/apply로 가벼운 전처리

정도라서, 이 정도만 몸에 붙어 있으면 웬만한 데이터 핸들링은 다 된다.[^3_3][^3_1][^3_2]

다음 단계로 가고 싶으면,

- 시계열 인덱스(`pd.to_datetime`, `set_index`, resample)
- 피벗테이블(`pivot_table`)
쪽을 “주가 데이터” 예제로 같이 보면 좋을 것 같은데, 그걸로 예시 볼래?
<span style="display:none">[^3_10][^3_7][^3_8][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://codevang.tistory.com/337

[^3_2]: https://rubus0304.tistory.com/90

[^3_3]: https://gaussian37.github.io/python-pandas_snippets/

[^3_4]: https://programmerpsy.tistory.com/5

[^3_5]: https://sahayana.tistory.com/20

[^3_6]: https://titanumm.tistory.com/84

[^3_7]: https://dacon.io/forum/408106

[^3_8]: https://velog.io/@o_joon_/pandas-%EA%B8%B0%EB%B3%B8-%EB%AC%B8%EB%B2%95-%EC%97%B0%EC%8A%B5-1

[^3_9]: https://wikidocs.net/231739

[^3_10]: https://dev-hyonie.tistory.com/19

