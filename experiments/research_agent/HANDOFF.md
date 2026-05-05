# Research Agent — 인수인계서 (Handoff)

> **목적**: 다른 LLM 또는 새 세션이 이 프로젝트를 30초 안에 이어받는다.
> **작성**: 2026-05-03 / **작성자 컨텍스트**: HAN_LAB 모노레포, 가천대 AI 학부생.
> **이 문서 하나만 읽으면 바로 이어 작업 가능**해야 한다.

---

## 0. 30초 요약

- **무엇을 만들려 하는가**: 주제 하나를 입력하면 **로컬 LLM이 브라우저를 직접 돌면서 트위터/FRED/웹을 탐색**하고, 본 페이지를 raw md로 자동 저장하는 24h 무인 에이전트.
- **어디까지 왔나**: 모델 능력 측정(`quiz_solve.md`, `capability_map.md`) 끝. Browser-use 패턴으로 가기로 결정. 5개 축(Representation/Grounding/Architecture/Memory/도구) 정리 완료. **아직 코드는 한 줄도 안 짬** — 설계 단계.
- **다음 결정 필요한 것**: §9 미해결 결정사항 5개. 그 중 첫 1~2개만 정해지면 바로 코드 들어감.

---

## 1. 프로젝트 컨텍스트 (HAN_LAB 모노레포)

```
HAN_LAB/
├── core/                # 검증된 자산 (꼼꼼하게)
│   ├── ai/              # OllamaClient, GeminiClient
│   └── ChartLlm_Core/
├── experiments/         # 빠르게, 더럽게 OK   ← 지금 작업 위치
│   ├── quiz_solver.py
│   ├── quiz_data.json
│   ├── quiz_solve.md
│   ├── capability_map.md   ★ 가장 중요
│   └── research_agent/     ← 이 프로젝트
│       └── HANDOFF.md      (이 파일)
├── projects/            # 살아남은 실험 결합
└── archive/
```

- 설치: `pip install -e .` (core* 만)
- 환경: 맥북 M1 + 윈도우 데스크탑 병행, GitHub 동기화
- 작성자 수준: 파이썬 문법 OK, 구조 설계/리팩터링 약함

---

## 2. 사용자가 명시적으로 박은 제약 (절대 깨지 말 것)

| 제약 | 의미 |
|---|---|
| **외부 LLM API 절대 금지** | Gemini/Claude/OpenAI 호출 금지. 모든 LLM은 ollama 로컬. |
| 데이터 소스 API는 OK(추정) | FRED 무료 API 등은 사용 가능 (사용자 확인 필요) |
| **24시간 무인 운영** | 사람이 안 보는 시간 동안 알아서 돌아야 함 |
| **LLM은 사실 안 만든다** | 모델은 "어디 갈래?"만 결정. 본문/사실은 결정론 코드가 추출/저장. |
| 작은 로컬 모델 (`gemma4:e4b` 후보) | tool use·vision 능력에 한계 있음 |
| 코드 위치 | experiments/ 시작 → 살아남으면 projects/ |

---

## 3. 지금까지 만든 산출물

| 파일 | 역할 |
|---|---|
| [experiments/quiz_data.json](../quiz_data.json) | 20문제 시험지 (논리/수학/함정/언어/과학/역사/윤리/코딩/경제/추리/창의) |
| [experiments/quiz_solver.py](../quiz_solver.py) | 문제별 독립 chat 세션으로 풀고 md 저장 |
| [experiments/quiz_solve.md](../quiz_solve.md) | gemma4:e4b 풀이 결과 20개 |
| [experiments/capability_map.md](../capability_map.md) | **★ 모델 위임 결정 가이드** — 새 작업 시작 전 무조건 참조 |

---

## 4. capability_map 핵심 발견 (요약)

**점수**: 13✅ / 4⚠️ / 3❌ (정답률 ≈ 70%)

**위임해도 되는 것**:
- 수학 계산, 확률, 수론 (#3, #4, #5, #19)
- 코드 리뷰·복잡도 분석 (#14, #15)
- 표준 개념 설명 (과학/경제) (#10, #11, #16, #17, #20)
- 문법 교정·요약·분류 (#9)
- 표준 패턴 논리 추론 (#2)
- 사회 편견 함정(학습된 패턴) (#7)

**위임 금지**:
- 🔴 **긴 사실 리스트 생성** — #12 조선 27대 왕에서 환각 폭발, "모르면 모른다고 하라"는 시스템 프롬프트도 무력. **반드시 외부 DB**.
- 🔴 **정의·전제 의심 필요한 함정** — #6 살인자 방. 단어 정의 확장을 못 함.

**조건부**:
- ⚠️ 다단계 상호작용 추리 (#18) — verifier 필수
- ⚠️ 답이 모호한 문제 (#1) — N번 샘플링·다수결, 같은 문제 다른 답 나옴 (자기일관성 부족)

→ Research Agent 디자인의 핵심 지침: **LLM이 "사실 생산자"가 아닌 "행선지 결정자" 역할만 하도록 강제**. 이러면 위 위험들이 다 차단됨.

---

## 5. 진행 중 아이디어: Research Agent

### 패턴 이름
**Browser-use 에이전트** (Anthropic Computer Use, OpenAI Operator, browser-use 오픈소스 라이브러리, WebVoyager 등이 같은 결).

### 핵심 흐름 (제안)
```
URL → Playwright load → extractor가 인터랙티브 요소 N개 추출
   → LLM에 텍스트로 보여줌 ("[1] button '검색', [2] input ...")
   → LLM 응답: "ACTION: click 1" (DSL)
   → driver가 실행 → 다음 페이지
   → 본문은 raw/extracted/에 md로 자동 저장 (LLM 안 거침)
```

### LLM이 절대 안 하는 것
- 본문 요약·추출 (결정론 BeautifulSoup/Readability가 함)
- "트위터에서 X가 ~~라고 했다" 식의 사실 진술
- 픽셀 좌표 (x, y) 출력 (Playwright가 셀렉터로 처리)

### LLM이 하는 것
- "다음에 어디 갈래?" 결정 (요소 번호 출력)
- "더 파볼까 멈출까?" 라우팅
- (선택) 일1회 raw 모아서 요약 — capability_map ✅ 영역

---

## 6. 검토한 5개 축 (사용자에게 이미 정리해 보여줌)

### 축 1: Representation (페이지를 LLM에 어떻게 보여주나)
- ✅ 추천: **Reduced HTML(인터랙티브 요소만 + 번호)** + Readability(본문 추출)
- ❌ 비추: Raw HTML 통째 / 픽셀 스크린샷 단독 (작은 vision 모델 약함)

### 축 2: Action Grounding (어디 클릭할지)
- ✅ 추천: **Element index** (`click 5`) — Playwright가 좌표 처리
- ❌ 비추: 픽셀 좌표 직접 출력 (작은 모델 거의 불가)

### 축 3: Loop Architecture
- ✅ 추천: **ReAct + Recover-on-fail + (점진) Skill library**
- ❌ 비추: Tree of Thoughts (토큰 폭주) / Plan-then-Execute (작은 모델 계획력 약함)

### 축 4: Memory
- ✅ 추천: **Sliding window + Failure DB**
- 보조: Skill library (Voyager 식, 24h 누적에 강함)

### 축 5: 실제 도구
- ✅ 핵심: **Playwright**
- 보조 (선택): **`browser-use` 라이브러리** (DOM 추출 + 번호 매김 + ollama 지원, 가장 적합)

---

## 7. 권장 최소 조합 (현재 잠정)

```
Representation:  Reduced HTML(interactive only) + Readability(본문 결정론)
Grounding:       Element index 단독 (번호로 가리킴)
Architecture:    ReAct + Recover-on-fail
Memory:          Sliding window + Failure DB
LLM:             ollama / gemma4:e4b 또는 qwen2.5:3b (비교 측정 필요)
도구:            Playwright (선택: browser-use 라이브러리)
보조:            DOM mutation observer로 변화 diff 저장
```

→ 사용자가 이 조합 큰 틀에 동의했다고 보면 됨(명시적 확정은 안 함).

---

## 8. 24h 무인 운영 안정성 체크리스트

| 항목 | 우선순위 |
|---|---|
| Resume from crash (`state.json`) | 0 |
| Visited dedup (`visited.sqlite`) | 0 |
| Step/time budget 강제 | 0 |
| Trace jsonl (모든 결정 기록) | 0 |
| Watchdog (LLM hang timeout) | 1 |
| Heartbeat | 1 |
| Disk quota / 압축·삭제 정책 | 1 |
| Prompt injection 방어 (delimiter + 시스템 지시) | 1 |
| Rate limit 자체 관리 (sleep 지터, 일일 quota) | 2 |
| 봇 감지 우회 (Playwright stealth, headless=False) | 2 |
| CAPTCHA/로그인 만나면 스킵 + 로그 | 2 |
| 팝업·쿠키 배너 자동 dismiss | 2 |
| 무한 스크롤·자동 리다이렉트 가드 | 2 |

---

## 9. 미해결 결정사항 (★ 다음 액션)

새 세션이 가장 먼저 해결해야 할 것들:

- [ ] **D1. 첫 타겟 사이트 화이트리스트 1~2개 확정**
  - 후보: FRED(거의 확정), 뉴스(어디?), 트위터(접근 수단?)
  - "아무 데나 가도록"은 24h 무인에서 자살. 화이트리스트가 생존선.
- [ ] **D2. 트위터 접근 수단**
  - X API 유료 / nitter 스크래핑(불안정) / RSS / 수동 export — 어느 거?
- [ ] **D3. tool use 모델 선택**
  - `gemma4:e4b` (추론 ✅, tool use 약함) vs `qwen2.5:3b`(tool use ✅) — 짧은 비교 측정 필요
- [ ] **D4. browser-use 라이브러리 vs 직접 Playwright**
  - 직접 짜면서 원리 익힐지, 라이브러리 먼저 돌리고 한계 본 뒤 결정할지
- [ ] **D5. processed 정리 단계 둘지**
  - 옵션 A: raw만 쌓는다 (사용자가 한 말에 가장 가까움 — "결과 안 만든다")
  - 옵션 B: 자정에 1번 gemma4:e4b로 요약본 1장
- [ ] **D6. MVP 시작점**
  - `extractor.py`(요소 추출) 먼저 vs `driver.py`(브라우저 래퍼) 먼저
  - 추천: **extractor 먼저** (이게 안 되면 위 다 안 됨)

---

## 10. 폴더 구조 제안 (미생성, HANDOFF.md 외에는 비어있음)

```
experiments/research_agent/
├── HANDOFF.md                     ← 이 문서 (이미 존재)
├── topics/{날짜}_{주제}/           # 미생성
│   ├── raw/
│   │   ├── pages/                 # 페이지 HTML 스냅샷
│   │   ├── extracted/             # 본문 md
│   │   └── screenshots/           # (선택) 디버깅
│   ├── trace.jsonl
│   ├── visited.sqlite
│   ├── state.json
│   └── meta.json
├── browser/
│   ├── driver.py                  # Playwright 래퍼
│   ├── extractor.py               # 인터랙티브 요소 N개 추출
│   └── stealth.py
├── agent/
│   ├── loop.py                    # ReAct 루프 (ollama)
│   ├── parser.py                  # DSL 파싱
│   ├── prompts.py
│   └── safety.py                  # budget, watchdog
└── runner.py                      # 24h 데몬
```

---

## 11. 사용자 응답 스타일 (CLAUDE.md 핵심)

응답할 때 반드시 따른다:

1. **한국어**. 코드 주석도 한국어 OK. 함수명·변수명만 영어 스네이크.
2. **파일 경로 먼저**: 코드 제시 전 `HAN_LAB/어디/무엇.py` 명시.
3. **응답 포맷**: ① 한 줄 요약 → ② 2~3줄 근거 → ③ 코드(상단 `# FILE:` 주석) → ④ 다음 단계 1~2개.
4. **100줄 넘는 코드 한 번에 쏟기 전**: ① 파일 트리 → ② 각 파일 역할 한 줄 → ③ 그다음 코드.
5. **코드 짜기 전 질문 먼저**: experiments인지 core인지, 비슷한 함수 이미 있는지, 진짜 지금 만들 필요 있는지.
6. **복사 금지** — 다른 모듈 함수는 import. 불가피하면 헤더(COPIED FROM/AT/REASON/REMERGE) 강제.
7. **금지**: pytest/CI/Docker/로깅 프레임워크/`src/` 레이아웃 — 사용자가 요청 안 했으면 추가 금지.
8. **금지**: `git push/pull/init` — 사용자가 요청 안 했으면 실행 지시 금지.
9. 우선순위(충돌 시): 사용자 이해 가능 > 예쁨 / 지금 돌아감 > 확장성 / 기존 구조 유지 > 신규 도입.
10. **추천보다 사용자 명시 요청 우선**.

---

## 12. 새 LLM 시작 프롬프트 (이 md와 함께 던져라)

```
나는 HAN_LAB 모노레포에서 Research Agent를 만들고 있어.
experiments/research_agent/HANDOFF.md를 끝까지 읽고, 그 안의 §11(CLAUDE.md 응답 스타일)을 무조건 따라.

다음을 순서대로 해줘:

1. 5문장 이내로 현재 상황을 요약 (네가 제대로 이해했는지 보고 싶음)
2. §9 미해결 결정사항 6개 중 가장 먼저 해결해야 할 항목 3개를 우선순위 순으로 골라
3. 그 첫 항목에 대해 나에게 던질 질문 1개 (선택지 형식이면 더 좋음)

지금은 코드 짜지 마. 설계 단계야.
첫 코드를 짤 때가 와도 §11.4 규칙(파일 트리 → 역할 한 줄 → 코드) 따라.
```

---

## 13. 작업 재개 시 새 LLM이 추가로 봐야 할 파일

순서대로:

1. [experiments/capability_map.md](../capability_map.md) — 모델 능력·위임 가이드 (5분)
2. [experiments/quiz_solve.md](../quiz_solve.md) — 측정 원본 (필요 시 §6, §12, §18만 봐도 됨)
3. [HAN_LAB/CLAUDE.md](../../CLAUDE.md) — 프로젝트 전체 규칙
4. [core/ai/ollama.py](../../core/ai/ollama.py) — 재사용할 OllamaClient

---

## 14. 변경 로그

| 날짜 | 변경 | 작성 |
|---|---|---|
| 2026-05-03 | 최초 작성. 설계 단계, 코드 0줄. | 이전 세션 |
