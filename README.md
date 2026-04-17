# HAN_LAB

개인 연구실 모노레포. 구글식 폴더 분리 스타일.

## 구조
- `core/` — 여러 프로젝트에서 재사용하는 모듈
- `experiments/` — 막 만들어도 되는 실험 (YYYY-MM-설명/)
- `projects/` — 살아남은 프로젝트
- `archive/` — 죽은 실험 보관 (삭제하지 않음)

## 설치
```bash
pip install -e .
```

## 사용
```python
from core.chart.text_chart import plot_text_chart
```
