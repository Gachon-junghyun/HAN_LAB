# CLAUDE.md — HAN_LAB 전용 지시서

> 이 파일은 HAN_LAB 디렉토리에서만 적용되는 규칙이다.
> 코드는 네(AI)가 쓴다. 나는 방향만 제시한다. 구조의 방향은 내가 정한다.

---

## 0. 프로젝트 개요

- **모노레포 이름**: `HAN_LAB`
- **작성자**: Gachon 대학교 AI 전공 학부생. 파이썬 문법은 알지만 구조 설계/리팩터링/패키징은 아직 약함.
- **환경**: 맥북(M1) + 윈도우 데스크탑 병행. 경로는 GitHub로 동기화.
- **설치 방식**: `pip install -e .` 만 사용. pip 배포 없음.
- **관심 도메인**: 금융 / 차트 / LLM / 뉴스 / DART 공시 / 퀀트

---

## 1. 폴더 구조

```
HAN_LAB/
├── core/                   # 재사용 가능한 검증된 모듈 (자산)
│   └── ChartLlm_Core/      # 차트+LLM 연동 핵심 모듈 (개발 중)
├── experiments/            # 버릴 수도 있는 실험 코드 (더럽게 써도 OK)
├── projects/               # 살아남은 실험 → 결합된 프로덕트
├── archive/                # 죽은 실험 보관소 (건드리지 않음)
├── pyproject.toml          # pip install -e . 설정 (core* 만 포함)
├── CLAUDE.md               # 이 파일
└── codingforme.md          # 원본 지시서 (전체 규칙)
```

### 폴더별 코딩 스타일

| 폴더 | 속도 | 타입힌트 | docstring | 재사용 고려 |
|------|------|----------|-----------|------------|
| `experiments/` | 빠르게 | 생략 OK | 생략 OK | ❌ |
| `core/` | 꼼꼼하게 | 필수 | 필수 | ✅ |
| `projects/` | 중간 | 권장 | 권장 | core에서 import |

### 의존성 방향 (단방향 강제)

```
experiments/ ──→ core/
projects/    ──→ core/
core/A       ──→ core/B  (한 방향만 OK)
core/A      ←──→ core/B  ← 즉시 경고, core/shared/로 추출 제안
```

---

## 2. 코드 작성 전 반드시 물어볼 것

코드를 짜기 전, 아래 중 애매한 게 있으면 **먼저 질문한다** (건너뛰면 안 됨):

1. **"이 코드는 `experiments/`야, `core/`야?"**
2. **"`core/` 안에 비슷한 함수 이미 있어?"** — 있으면 새로 만들지 않고 기존 걸 씀
3. **"이거 지금 만들 필요 진짜 있어? 기존 함수로 해결 안 돼?"**

---

## 3. 항상 지킬 규칙

### 파일 위치 명시
코드 제시 전에 반드시 `HAN_LAB/어디/무엇.py` 경로를 먼저 말한다.

### 복사 금지 — import로 연결
다른 모듈 함수가 필요하면 복붙 대신 `from core.chart.text_chart import plot_text_chart` 방식으로 import.
불가피하게 복사할 경우 파일 상단에 이 헤더 필수:
```python
# COPIED FROM : core/xxx/yyy.py
# COPIED AT   : YYYY-MM-DD
# REASON      : (왜 import로 안 됐는지)
# REMERGE?    : yes / no
```

### 함수명은 세션 중 바꾸지 않는다
바꿔야 한다면 기존 이름은 wrapper로 유지:
```python
def new_func(...): ...
def old_func(*args, **kwargs):
    """Deprecated: new_func으로 위임."""
    return new_func(*args, **kwargs)
```

### core 승격 기준
함수가 **2개 이상 프로젝트에서 쓰일 때** → `core/`로 승격 제안.
"언젠가 쓸 것 같아서" 미리 넣지 않는다.

### 자산 후보 표시
`core/` 후보 함수는 docstring 위에:
```python
# @core-candidate: 함수명, YYYY-MM, 용도 한 줄
```

### 커밋 메시지 타입
`feat:` / `fix:` / `exp:` / `stable:` — 이 4개만 사용.

---

## 4. 하지 말 것

- pytest, pre-commit, GitHub Actions, Dockerfile, CI/CD, 로깅 프레임워크 — **요청 없으면 추가 금지**
- `src/` 레이아웃 강요 금지 — 구글식 `core/` 루트 바로 아래 구조를 씀
- `git pull/push/init` — 내가 요청하지 않으면 실행 지시 금지
- pip 패키지화 — "재사용하고 싶어"만으로는 금지. `core/` 분리로 먼저 해결
- 100줄 넘는 코드를 한 번에 쏟기 전에: ① 파일 트리 먼저 ② 각 파일 역할 한 줄 ③ 그다음 코드

---

## 5. 응답 포맷

1. **뭘 할지 한 줄 요약**
2. **왜 이렇게 하는지 2~3줄 근거** (위치, 이름, 구조 이유)
3. **코드** — 블록 상단에 `# FILE: 경로` 주석
4. **다음 단계 제안** (있으면 1~2개만)

---

## 6. 언어

- 설명은 **한국어**
- 코드 주석도 한국어 OK
- 함수명/변수명은 영어 스네이크케이스 (`plot_text_chart`, `fetch_news`)

---

## 7. 우선순위 (충돌 시)

1. 내가 이해 가능한가 > 예쁜가
2. 지금 돌아가는가 > 확장 가능한가
3. 기존 구조 유지 > 새 구조 도입
4. 모노레포 안에서 해결 > 외부 패키지 도입
5. 내 명시적 요청 > 네 추천

---

> 전체 원본 규칙은 `codingforme.md` 참고.
