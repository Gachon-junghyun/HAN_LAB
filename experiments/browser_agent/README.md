# browser_agent — LLM 기반 브라우저 자동화 PoC

이미 사용자가 띄워둔 Chrome에 **CDP**로 붙어, 자연어 목표를 받아 페이지를
한 스텝씩 인덱싱-판단-행동하는 최소 구현.

스택: Python + Playwright(`connect_over_cdp`) + LLM(**Ollama 로컬** 또는 **Gemini API**).

LLM은 `core/ai/{gemini,ollama}.py` 의 클라이언트를 그대로 import해 쓴다.
기본은 `--llm ollama` (로컬). `--llm gemini` 로 클라우드로 전환.

모든 진행 정보는 `logs/run_<timestamp>.log` 와 콘솔에 동시에 기록된다.

---

## 1. 의존성 설치

`google-genai` / `python-dotenv` 는 루트 `pyproject.toml` 에 이미 들어가 있다.
모노레포 루트에서 한 번:

```bash
# 모노레포 루트 (HAN_LAB/) 에서
pip install -e .

# PoC 공통 의존성
pip install playwright
# CDP로 외부 Chrome에 붙기만 하므로 chromium 다운로드는 필수가 아님.
# 필요 시: playwright install chromium
```

### LLM 1) Ollama (기본 — 로컬)

```bash
pip install ollama
# Ollama 자체 설치는 https://ollama.com/download 참고
# 다른 터미널에서 서버 띄우기 (보통 자동 실행됨)
ollama serve
# 모델 한 번 받기 (기본: gemma4 — 로컬 GPU/RAM에 맞게 다른 모델로 바꿔도 됨)
ollama pull gemma4
```

`main.py` 가 기본으로 `gemma4` 를 부른다. 다른 모델이면:
```bash
python main.py --ollama-model qwen2.5:7b "..."
# 또는 환경변수
OLLAMA_MODEL=qwen2.5:7b python main.py "..."
```

### LLM 2) Gemini (클라우드)

GEMINI_API_KEY 설정 (https://aistudio.google.com/apikey):

```bash
# macOS / Linux
export GEMINI_API_KEY=...

# Windows PowerShell
$env:GEMINI_API_KEY="..."
```

`GOOGLE_API_KEY` 도 자동 인식하며, `core/ai/gemini.py` 가 `.env` 도 로드한다.
실행 시 `--llm gemini` 플래그를 붙이면 Gemini 사용:

```bash
python main.py --llm gemini "구글에서 'playwright cdp' 검색"
```

---

## 2. Chrome을 디버깅 포트로 띄우기

**기존 Chrome 창을 모두 닫은 뒤**, 디버깅 포트와 별도 user-data-dir을 지정해 띄운다.
스크립트는 Chrome을 직접 실행하지 않고 이 인스턴스에 붙기만 한다.

### macOS

```bash
# 별도 프로필(권장)
/Applications/Google\ Chrome.app/Contents/MacOS/Googexle\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-agent-profile"

# 기존 프로필 그대로 쓰고 싶다면 (다른 Chrome 창 모두 종료 필수)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome"
```

### Windows (PowerShell)

```powershell
# 별도 프로필(권장)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="C:\chrome-agent-profile"

# 기존 프로필 (모든 Chrome 창 종료 필수)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data"
```

### Linux

```bash
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-agent-profile"
```

브라우저가 뜨면 `http://localhost:9222/json/version` 을 한 번 열어 응답이
JSON으로 나오는지 확인하면 된다.

---

## 3. 실행

스크립트는 항상 **현재 활성 탭**을 조작한다. 원하는 페이지를 먼저 그 탭에서 열어두자.
`chrome://new-tab-page/` 같은 내부 페이지에서는 인덱스가 비어 동작 안 함.

```bash
cd experiments/browser_agent

# 기본 (Ollama, llama3)
python main.py "구글에서 'playwright cdp'를 검색해"

# Gemini로 전환
python main.py --llm gemini "구글에서 'playwright cdp'를 검색해"

# Ollama 다른 모델
python main.py --ollama-model qwen2.5:7b "..."

# 데모: bot.sannysoft.com 인덱싱 결과만 출력
python main.py --demo
```

매 스텝 콘솔과 `logs/run_<timestamp>.log` 에 동시에 기록되는 것:
- 현재 URL / TITLE
- 인덱싱 결과 (`[1]<button>로그인</button>` 형식)
- LLM의 `thought` / `action`
- 액션 실행 결과

최대 20스텝, 또는 LLM이 `done`을 반환하면 종료.

---

## 4. 구조

```
experiments/browser_agent/
├── main.py          # CDP 연결 + GeminiClient.chat() 루프 + logging
├── dom_indexer.py   # 가시성 판정 JS + 직렬화 (data-agent-idx로 안정 로케이터)
├── README.md
└── logs/            # 실행마다 run_YYYYMMDD_HHMMSS.log 자동 생성
```

- LLM 호출은 `core.ai.gemini.GeminiClient` / `core.ai.ollama.OllamaClient` 를 그대로 import해서 쓴다 (복사 금지 룰 준수). `--llm` 플래그로 선택.
- `dom_indexer.py`의 `JS_INDEX`는 큰 멀티라인 문자열 그대로 `page.evaluate`에 전달된다.
- 클릭/입력은 `data-agent-idx="N"` CSS 속성으로 만든 `page.locator(...)` 를 사용 — 인덱싱 후 DOM이 살짝 바뀌어도 안정적.

---

## 5. 알려진 한계 / 추측 금지 메모

- 스크립트는 Chrome을 띄우지 않는다. 사용자가 디버깅 포트를 잘못 띄우면 그냥 실패한다 (이는 의도된 분리).
- CDP 연결은 첫 번째 컨텍스트의 첫 번째 탭만 본다. 여러 창/탭을 한 번에 조율하려면 추가 작업 필요.
- iframe 내부 요소는 인덱싱하지 않는다 (필요해지면 frame 순회 추가).
- Shadow DOM도 미지원 (대부분의 일반 사이트엔 충분).
- 모델은 `main.py` 의 `GEMINI_MODEL` / `DEFAULT_OLLAMA_MODEL` 상수, 또는 CLI 플래그로 변경.
- JSON 강제는 system prompt 지시 + 강건한 파서(`parse_json_response`, 첫 `{` ~ 마지막 `}` 추출)로 흡수한다. Ollama 쪽은 instruction following이 약한 작은 모델일수록 JSON이 깨질 위험이 크니 충분한 크기(`gemma4`/`llama3`/`qwen2.5:7b` 정도) 권장. 실전에서 자주 깨지면 `core/ai/{gemini,ollama}.py` 에 `response_mime_type`/`format="json"` 옵션을 추가하는 게 깔끔.
