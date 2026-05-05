# FILE: experiments/browser_agent/main.py
# 사용법:
#   python main.py "구글에서 'playwright cdp'를 검색해"            # 기본: ollama
#   python main.py --llm gemini "구글에서 ... 검색해"
#   python main.py --llm ollama --ollama-model llama3 "..."
#   python main.py --demo
#
# 사전:
#   1) 루트에서 `pip install -e .` (core 패키지 인식용)
#   2) `pip install playwright`  (PoC 의존성)
#   3) ollama 사용 시: `pip install ollama` + 로컬에서 `ollama serve` + `ollama pull <model>`
#   4) 별도 터미널에서 Chrome을 --remote-debugging-port=9222 로 띄워둘 것
#   5) 환경변수: GEMINI_API_KEY (gemini 사용 시) / OLLAMA_MODEL (선택)

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright

from core.ai.gemini import GeminiClient
from dom_indexer import index_page


CDP_URL = "http://localhost:9222"
GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4")
DEFAULT_LLM = "ollama"
MAX_STEPS_ACTION = 20
MAX_STEPS_RESEARCH = 40

SYSTEM_PROMPT = """너는 브라우저 자동화 에이전트다.
사용자가 자연어 목표를 주면, 페이지에서 인덱싱된 인터랙티브 요소 목록을 보고 한 스텝씩 행동한다.

[응답 형식]
반드시 단일 JSON 객체. 코드블록/설명 없이 JSON 한 덩어리만 출력.
키:
- "thought": string. 현재 상황 판단을 한국어로 1~2줄.
- "action": "click" | "type" | "scroll" | "done"
- "index": int. click/type일 때만 필수. 현재 스텝의 인덱스 목록 안의 번호.
- "text":  string.
    * type일 때: 입력할 문자열
    * scroll일 때: "up" 또는 "down"
    * done일 때: 결과 요약(선택)

[행동 규칙]
- 인덱스는 매 스텝마다 새로 부여된다. 직전 스텝의 번호를 그대로 쓰지 말고, 항상 현재 목록을 보고 결정한다.
- 페이지가 변하지 않거나 같은 인덱스만 반복되면 "done"으로 종료한다.
- 목표 달성, 또는 더 이상 진행할 수 없다고 판단되면 "done".
- 입력은 가능한 한 한 번에 정확한 텍스트로 type. type 후 검색 제출이 필요하면 다음 스텝에서 Enter용 버튼을 클릭하거나 검색 버튼을 누른다.

[종료 판단 — 중요]
- 사용자 목표가 명백히 달성되면 **즉시 done**. 사용자가 명시적으로 요구하지 않은 추가 탐색/확인 행동은 하지 않는다.
- 예: 목표가 "X 링크를 클릭"이고 직전 스텝에서 X(또는 의미상 동등한 것)를 click했고 RESULT가 OK였다면, 다음 스텝은 무조건 done.
- 예: 목표가 "검색창에 X 입력하고 검색 실행"이고 검색 결과 페이지로 이미 이동했다면 done.
- "정말 맞나" 의심하지 말고, RESULT가 OK이고 페이지가 의도대로 바뀌었으면 done.

[매칭 원칙 — 중요]
- 사용자가 언급한 텍스트와 인덱싱된 요소의 텍스트가 정확히 일치하지 않아도, **의미적으로/기능적으로 가장 가까운 요소**를 선택한다.
  예: 목표가 'More information 링크 클릭'인데 목록에 [1]<a>Learn more</a> 만 있으면 그게 정답이다 (같은 의미).
  예: 목표가 '검색창에 입력'인데 [N]<input type="search"> 또는 <textarea aria-label="검색"> 이 있으면 그게 검색창이다.
- aria-label, name, type, role 같은 속성으로 의도를 추론할 것. text가 비어있어도 속성이 단서.
- 정확히 일치하는 게 없다고 섣불리 done 하지 말고, 가장 가까운 후보를 시도한다. 시도가 명백히 잘못된 결과를 낳으면 그때 다시 판단.
"""


RESEARCH_ADDITION = """

[research 모드 — 자료 수집]
이 모드에선 단순 자동화가 아니라 **페이지 본문을 모아두는 것이 핵심**이다.

추가 액션:
- "extract": 현재 페이지의 본문 텍스트를 노트 파일에 저장. Wikipedia/뉴스 기사 같은 정적 본문에 사용.
- "scroll_full": 끝까지 스크롤하면서 본문을 누적 캡처(가상 스크롤 페이지 대응). YouTube/Twitter/무한 스크롤에 사용.
- "add_todo": 조사 도중 더 살펴볼 가치가 있는 곳을 발견하면 큐에 추가. text에 URL 또는 자연어 항목.
  예: text="https://en.wikipedia.org/wiki/Foo" 또는 text="Foo의 역사 검색"
- "next_todo": 현재 항목에서 더 모을 게 없으면 종료하고 다음 TODO로 진행. (큐가 비면 자동 done.)

행동 우선순위:
- 새 페이지 도착 → 먼저 extract 또는 scroll_full로 본문 저장.
- 본문 저장 후, 페이지에서 관련 키워드/링크 발견 시 add_todo로 적어둘 것 (URL 우선).
- 한 페이지에서 모을 거 다 모았고 더 살펴볼 link도 다 add_todo했다면 next_todo.
- 큐 비고 자료 충분하면 done.
- "직전 스텝 결과"가 OK로 시작했다면 같은 페이지에서 같은 작업 반복하지 마라.
"""


def get_system_prompt(mode):
    if mode == "research":
        return SYSTEM_PROMPT + RESEARCH_ADDITION
    return SYSTEM_PROMPT


# ---------- logging ----------
# Windows 콘솔(cp949) 한글 깨짐 / UnicodeEncodeError 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
# google-genai의 INFO 로그 잠재우기 (AFC 메시지 등)
logging.getLogger("google_genai").setLevel(logging.WARNING)
log = logging.getLogger("browser_agent")


# ---------- 본문 추출 / 스크롤 끝까지 ----------
EXTRACT_JS = """
() => ({
  url: location.href,
  title: document.title || '',
  text: ((document.body && document.body.innerText) || '').slice(0, 20000)
})
"""

# 스크롤하며 매 단계 보이는 텍스트를 누적(중복 제거).
# YouTube 같은 가상 스크롤(화면 밖 DOM 제거) 페이지에서도 도중 본 항목 다 모은다.
# scrollHeight 안정화 + 페이지 끝 도달 + 최대 50회로 안전망.
SCROLL_COLLECT_JS = """
async () => {
  const STEP_PX = Math.max(400, window.innerHeight * 0.8);
  const seen = new Set();
  const collect = () => {
    const t = (document.body && document.body.innerText) || '';
    t.split('\\n').forEach(line => {
      const s = line.trim();
      if (s.length > 3) seen.add(s);
    });
  };
  collect();
  let lastH = -1;
  let stableCount = 0;
  for (let i = 0; i < 50; i++) {
    window.scrollBy(0, STEP_PX);
    await new Promise(r => setTimeout(r, 500));
    collect();
    const h = document.body.scrollHeight;
    const cur = window.scrollY + window.innerHeight;
    if (h === lastH) {
      stableCount++;
      if (stableCount >= 2 && cur >= h - 10) break;
    } else {
      stableCount = 0;
    }
    lastH = h;
  }
  // 시각 순서를 어느 정도 유지하기 위해 Set 삽입 순서 그대로
  const lines = Array.from(seen);
  return {
    url: location.href,
    title: document.title || '',
    text: lines.join('\\n').slice(0, 50000)
  };
}
"""


def append_note(note_file, info, goal=""):
    """research 모드: 추출한 페이지 본문을 노트 파일 끝에 append."""
    title = info.get("title") or "(no title)"
    url = info.get("url", "")
    body = info.get("text", "") or "(empty)"
    header = (
        f"\n\n---\n\n"
        f"## {title}\n"
        f"- URL: {url}\n"
        f"- 시각: {datetime.now().isoformat(timespec='seconds')}\n\n"
    )
    with open(note_file, "a", encoding="utf-8") as f:
        f.write(header + body + "\n")


# ---------- LLM 추상화 ----------
def make_llm(provider, ollama_model, system_prompt):
    """( provider_name, client_obj ) 반환."""
    if provider == "gemini":
        return ("gemini", GeminiClient(model_name=GEMINI_MODEL, system_instruction=system_prompt))
    if provider == "ollama":
        # lazy import — gemini 단독 사용자가 ollama 미설치여도 OK
        from core.ai.ollama import OllamaClient

        # 이 PoC 전용 override. core OllamaClient는 그대로 두고 여기서만
        # ollama format="json"을 강제 → 모델 디코더 단계에서 valid JSON 강제.
        # gemma4처럼 instruction following 약한 모델에서 JSON 깨짐이 사실상 0.
        # 결과: parse_json_response의 PARSE FAIL이 거의 안 일어나서 retry hint를
        # "사용자 메시지"로 오해해 작업 abandon하는 gemma4 패턴도 우회.
        class OllamaJsonClient(OllamaClient):
            def chat(self, messages, stream=False, options=None):
                response = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    format="json",
                    options=options,
                )
                return response["message"]["content"]

        return ("ollama", OllamaJsonClient(model_name=ollama_model))
    raise ValueError(f"unknown provider: {provider}")


def normalize_history(provider, history, system_prompt):
    """내부 history는 [{"role": "user|assistant", "content": str}] 통일.
    호출 직전 provider별로 변환.
    """
    if provider == "gemini":
        # Gemini chat은 role: user | model. system_instruction은 클라이언트 생성 시 분리됨.
        return [
            {"role": "model" if m["role"] == "assistant" else m["role"], "content": m["content"]}
            for m in history
        ]
    # ollama: role: user | assistant. system은 messages 첫 항목으로.
    return [{"role": "system", "content": system_prompt}] + history


def parse_json_response(text):
    """코드블록/앞뒤 잡설을 흡수하고 JSON 객체 부분만 떼어 json.loads.
    결과가 dict가 아니면 ValueError로 raise → 재시도 트리거.
    """
    text = (text or "").strip()
    if text.startswith("```"):
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        text = text[s:e + 1]
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError(f"expected JSON object, got {type(obj).__name__}: {str(obj)[:80]}")
    return obj


def call_llm(provider, client, history, system_prompt, max_retries=2):
    """LLM 호출 + JSON 파싱. 파싱 실패 시 직전 raw + JSON 예시를 hint로 붙여 재시도."""
    base_msgs = normalize_history(provider, history, system_prompt)
    msgs = base_msgs
    last_err = None
    for attempt in range(max_retries + 1):
        raw = client.chat(msgs) or ""
        preview = raw.replace("\n", " ")[:200]
        log.info(f"RAW (attempt {attempt + 1}): {preview!r}")
        try:
            obj = parse_json_response(raw)
            return obj, raw
        except Exception as e:
            last_err = e
            log.warning(f"[PARSE FAIL attempt {attempt + 1}/{max_retries + 1}] {e}")
            if attempt < max_retries:
                bad = (raw or "").replace("\n", " ").strip()[:160] or "(빈 응답)"
                hint = (
                    f"[SYSTEM-RETRY-NOTICE — 이 블록은 사용자 입력이 아니라 자동 재요청 신호다. "
                    f"GOAL과 페이지 인덱스는 그대로 유효하니, 진행 중이던 자동화 흐름을 끊지 말고 계속하라. "
                    f"여기에 응답하지 말고, 직전에 의도했던 동일한 행동을 JSON으로 다시 출력만 하라.]\n"
                    f"직전 응답이 JSON 객체로 파싱되지 않았다.\n"
                    f"받은 응답 일부: {bad}\n"
                    f"반드시 아래 형식의 단일 JSON 객체만 출력하라. 코드블록(```)도, 다른 설명도, 한국어 평문도 절대 금지.\n"
                    f'예: {{"thought":"현재 페이지에서 무엇을 할지 판단","action":"click","index":1,"text":""}}'
                )
                msgs = base_msgs + [{"role": "user", "content": hint}]
    raise last_err


# ---------- actions ----------
def execute_action(page, action_obj, mapping, note_file=None, goal="",
                   url_text_lens=None, todo_queue=None, todo_state=None):
    """url_text_lens: {url: 직전 추출 본문 길이} dict.
    todo_queue: list - 남은 TODO 항목들.
    todo_state: dict - {"next_requested": bool} 플래그. add_todo/next_todo가 mutate.
    """
    action = action_obj.get("action")
    if action == "add_todo":
        if todo_queue is None:
            return "FAIL: add_todo는 research 모드에서만 사용 가능"
        item = (action_obj.get("text") or "").strip()
        if not item:
            return "FAIL: add_todo에 text가 비어 있음"
        if item in todo_queue:
            return f"SKIP: 이미 큐에 있음: {item[:60]}"
        todo_queue.append(item)
        return f"OK: TODO 추가 ({len(todo_queue)}개 대기): {item[:60]}"
    if action == "next_todo":
        if todo_state is None:
            return "FAIL: next_todo는 research 모드에서만 사용 가능"
        todo_state["next_requested"] = True
        remaining = len(todo_queue or [])
        return f"OK: 현재 항목 종료, 다음 TODO로 ({remaining}개 대기)"
    if action == "extract":
        if note_file is None:
            return "FAIL: extract는 research 모드에서만 사용 가능"
        try:
            info = page.evaluate(EXTRACT_JS)
            cur_url = info.get("url", "")
            new_len = len(info.get("text", ""))
            if url_text_lens is not None and cur_url in url_text_lens:
                return f"SKIP: 이미 수집된 URL ({new_len} chars). 같은 페이지 더 모으려면 scroll_full 사용."
            append_note(note_file, info, goal)
            if url_text_lens is not None:
                url_text_lens[cur_url] = new_len
            t = (info.get("title") or "")[:40]
            return f"OK: extracted '{t}' ({new_len} chars)"
        except Exception as e:
            return f"FAIL: extract failed: {e}"
    if action == "scroll_full":
        if note_file is None:
            return "FAIL: scroll_full는 research 모드에서만 사용 가능"
        try:
            # 스크롤하면서 매 단계 본문 누적 (가상 스크롤 페이지 대응)
            info = page.evaluate(SCROLL_COLLECT_JS)
            cur_url = info.get("url", "")
            new_len = len(info.get("text", ""))
            prev_len = (url_text_lens or {}).get(cur_url, 0)
            if new_len <= prev_len:
                return f"SKIP: scroll_full 후에도 본문 길이 변동 없음 ({new_len} chars)."
            append_note(note_file, info, goal)
            if url_text_lens is not None:
                url_text_lens[cur_url] = new_len
            t = (info.get("title") or "")[:40]
            return f"OK: scroll_full '{t}' (+{new_len - prev_len} chars, 총 {new_len})"
        except Exception as e:
            return f"FAIL: scroll_full failed: {e}"
    if action == "click":
        idx = action_obj.get("index")
        loc = mapping.get(idx)
        if loc is None:
            return f"FAIL: index {idx} not in mapping"
        loc.first.click(timeout=5000)
        return f"OK: clicked [{idx}]"
    if action == "type":
        idx = action_obj.get("index")
        text = action_obj.get("text", "")
        loc = mapping.get(idx)
        if loc is None:
            return f"FAIL: index {idx} not in mapping"
        loc.first.fill(text, timeout=5000)
        return f"OK: typed into [{idx}] -> {text!r}"
    if action == "scroll":
        direction = (action_obj.get("text") or "down").lower()
        delta = 600 if direction == "down" else -600
        page.evaluate(f"window.scrollBy(0, {delta})")
        return f"OK: scrolled {direction}"
    if action == "done":
        return "DONE"
    return f"UNKNOWN ACTION: {action}"


# ---------- browser ----------
def attach_to_browser(p, fresh_url=None):
    """fresh_url이 주어지면, 새 탭을 만들어 그 URL로 navigate한 뒤 기존 탭들을 모두 close한다.
    직전 실행이 chrome-error로 frozen된 탭을 남겼을 때, 다음 실행이 그 frozen page를 잡아
    아무것도 못 하는 문제(인덱스 빈 채로 옴) 회피용. fresh_url=None이면 기존 동작.
    """
    browser = p.chromium.connect_over_cdp(CDP_URL)
    if not browser.contexts:
        raise RuntimeError("CDP 컨텍스트가 없다. Chrome이 --remote-debugging-port=9222 로 떠있는지 확인.")
    context = browser.contexts[0]
    if fresh_url:
        new_page = context.new_page()
        try:
            new_page.goto(fresh_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(1.5)
        except Exception as e:
            log.warning(f"fresh goto 실패: {e} (새 탭 그대로 진행)")
        for old in list(context.pages):
            if old is not new_page and not old.is_closed():
                try:
                    old.close()
                except Exception as e:
                    log.warning(f"기존 탭 close 실패: {e}")
        page = new_page
    else:
        page = context.pages[0] if context.pages else context.new_page()
    page.bring_to_front()
    return browser, context, page


def get_active_page(context, current):
    """target='_blank' 등으로 새 탭이 열렸으면 가장 최근 탭으로 전환.
    현재 탭이 닫혔으면 마지막 탭. 변화 없으면 current 그대로 반환.
    """
    pages = [pg for pg in context.pages if not pg.is_closed()]
    if not pages:
        return current
    if current in pages and pages[-1] is current:
        return current
    return pages[-1]


# ---------- runners ----------
def run_demo():
    log.info("=== DEMO MODE ===")
    log.info(f"log file: {LOG_FILE}")
    with sync_playwright() as p:
        _, _, page = attach_to_browser(p, fresh_url="https://bot.sannysoft.com")
        time.sleep(0.5)
        serialized, _ = index_page(page)
        log.info(f"URL  : {page.url}")
        log.info(f"TITLE: {page.title()}")
        log.info("--- INTERACTIVE ELEMENTS ---")
        log.info(serialized if serialized else "(보이는 인터랙티브 요소 없음)")


def run_loop(goal, provider, ollama_model, start_url=None, mode="action", max_visits=8):
    log.info("=== AGENT START ===")
    log.info(f"log file: {LOG_FILE}")
    log.info(f"GOAL    : {goal}")
    log.info(f"MODE    : {mode}")
    log.info(f"PROVIDER: {provider}")

    system_prompt = get_system_prompt(mode)
    max_steps = MAX_STEPS_RESEARCH if mode == "research" else MAX_STEPS_ACTION

    # research 모드: 노트 파일 초기화
    note_file = None
    if mode == "research":
        notes_dir = Path(__file__).parent / "notes"
        notes_dir.mkdir(exist_ok=True)
        note_file = notes_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(note_file, "w", encoding="utf-8") as f:
            f.write(
                f"# Research Notes\n"
                f"- Goal: {goal}\n"
                f"- Started: {datetime.now().isoformat(timespec='seconds')}\n"
            )
        log.info(f"NOTES   : {note_file}")

    try:
        provider_name, client = make_llm(provider, ollama_model, system_prompt)
    except Exception as e:
        log.error(f"LLM 초기화 실패: {e}")
        sys.exit(1)
    log.info(f"MODEL   : {getattr(client, 'model_name', '?')}")

    with sync_playwright() as p:
        if start_url:
            log.info(f"START URL: {start_url}")
        # fresh_url 주면 새 탭 만들고 기존 frozen 탭들 모두 close (chrome-error 누적 방지).
        _, context, page = attach_to_browser(p, fresh_url=start_url)
        history = []  # [{"role": "user|assistant", "content": str}] 내부 표준
        prev_result = ""
        url_text_lens = {}
        # TODO 큐 (research only). 첫 항목은 사용자 goal 자체.
        todo_queue = [goal] if mode == "research" else None
        todo_state = {"next_requested": False} if mode == "research" else None
        current_todo = None
        visited_urls = set()
        visit_count = 0

        def auto_extract():
            """research 모드일 때 현재 page 본문을 노트에 저장 (중복 URL은 skip)."""
            nonlocal prev_result
            if mode != "research" or note_file is None:
                return
            try:
                info = page.evaluate(EXTRACT_JS)
                cur_url = info.get("url", "")
                new_len = len(info.get("text", ""))
                if cur_url and cur_url not in url_text_lens:
                    append_note(note_file, info, goal)
                    url_text_lens[cur_url] = new_len
                    t = (info.get("title") or "")[:40]
                    msg = f"auto-extracted '{t}' ({new_len} chars)"
                    log.info(f"[AUTO EXTRACT] {msg}")
                    prev_result = "OK: " + msg
            except Exception as e:
                log.warning(f"자동 extract 실패: {e}")

        def visit_url_and_autoextract(url):
            """URL로 이동 + research 모드면 자동 extract. (next_todo에서 사용)"""
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(1.5)
            except Exception as e:
                log.warning(f"goto 실패: {e}")
                return
            auto_extract()

        if start_url:
            # attach_to_browser에서 이미 navigate 완료. research면 본문만 캡처.
            visited_urls.add(start_url)
            visit_count += 1
            auto_extract()

        for step in range(1, max_steps + 1):
            time.sleep(0.5)

            # research 모드: next_todo 요청됐으면 큐에서 다음 항목 처리
            if mode == "research" and todo_state and todo_state.get("next_requested"):
                todo_state["next_requested"] = False
                if not todo_queue:
                    log.info("[TODO] 큐 비어있음 — 종료")
                    break
                if visit_count >= max_visits:
                    log.warning(f"[TODO] max_visits({max_visits}) 도달 — 종료")
                    break
                current_todo = todo_queue.pop(0)
                log.info(f"[TODO] 다음 항목: {current_todo}")
                history = []  # 새 항목 시작 — 컨텍스트 리셋
                prev_result = ""
                if current_todo.startswith(("http://", "https://")):
                    if current_todo in visited_urls:
                        log.info(f"[TODO] 이미 방문: {current_todo} — 스킵")
                        todo_state["next_requested"] = True
                        continue
                    visit_url_and_autoextract(current_todo)
                    visited_urls.add(current_todo)
                    visit_count += 1
                # 자연어 TODO면 그냥 LLM이 다음 step에서 해결

            # 시작 시점에 첫 TODO 세팅 (start_url 없는 경우 등)
            if mode == "research" and current_todo is None and todo_queue:
                current_todo = todo_queue.pop(0)
                log.info(f"[TODO] 시작 항목: {current_todo}")

            new_page = get_active_page(context, page)
            if new_page is not page:
                log.info(f"[TAB SWITCH] {page.url} -> {new_page.url}")
                page = new_page
                page.bring_to_front()
            try:
                serialized, mapping = index_page(page)
            except Exception as e:
                log.error(f"[INDEX FAIL] {e}")
                break

            url = page.url
            try:
                title = page.title()
            except Exception:
                title = ""

            log.info(f"=== STEP {step} ===")
            log.info(f"URL  : {url}")
            log.info(f"TITLE: {title}")
            log.info("--- INDEX ---")
            log.info(serialized if serialized else "(없음)")

            obs_parts = [f"GOAL: {goal}", "", f"URL: {url}", f"TITLE: {title}", ""]
            if mode == "research":
                obs_parts.append(f"CURRENT TODO: {current_todo or '(none)'}")
                if todo_queue:
                    obs_parts.append(f"REMAINING TODOs: {len(todo_queue)}개")
                    for i, t in enumerate(todo_queue[:5]):
                        obs_parts.append(f"  - {t[:80]}")
                    if len(todo_queue) > 5:
                        obs_parts.append(f"  ... 외 {len(todo_queue) - 5}개")
                obs_parts.append(f"VISITED: {visit_count}/{max_visits}")
                obs_parts.append("")
            obs_parts.append(f"INTERACTIVE:\n{serialized if serialized else '(없음)'}")
            if prev_result:
                obs_parts += ["", f"[직전 스텝 결과] {prev_result}"]
            observation = "\n".join(obs_parts)
            history.append({"role": "user", "content": observation})

            try:
                action_obj, raw = call_llm(provider_name, client, history, system_prompt)
            except Exception as e:
                log.error(f"[LLM FAIL] {e}")
                break
            history.append({"role": "assistant", "content": raw})

            thought = action_obj.get("thought", "")
            log.info(f"THOUGHT: {thought}")
            log.info(
                "ACTION : "
                + json.dumps(
                    {k: v for k, v in action_obj.items() if k != "thought"},
                    ensure_ascii=False,
                )
            )

            if action_obj.get("action") == "done":
                log.info(f"RESULT : DONE — {action_obj.get('text', '')}")
                break

            try:
                result = execute_action(
                    page, action_obj, mapping,
                    note_file=note_file, goal=goal, url_text_lens=url_text_lens,
                    todo_queue=todo_queue, todo_state=todo_state,
                )
            except Exception as e:
                result = f"FAIL: {e}"
            log.info(f"RESULT : {result}")
            prev_result = result

            time.sleep(1)
        else:
            log.warning(f"MAX_STEPS({max_steps}) 도달. 종료.")

    log.info("=== AGENT END ===")
    if note_file:
        log.info(f"노트 파일: {note_file}")


def main():
    parser = argparse.ArgumentParser(description="LLM 기반 브라우저 자동화 PoC")
    parser.add_argument("--llm", choices=["gemini", "ollama"], default=DEFAULT_LLM,
                        help=f"LLM 제공자 (기본: {DEFAULT_LLM})")
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL,
                        help=f"ollama 모델명 (기본: {DEFAULT_OLLAMA_MODEL}, 환경변수 OLLAMA_MODEL 도 인식)")
    parser.add_argument("--demo", action="store_true", help="데모 모드 (인덱싱만 출력)")
    parser.add_argument("--url", default=None, help="시작 시 자동 이동할 URL")
    parser.add_argument("--mode", choices=["action", "research"], default="action",
                        help="action: 단순 자동화 (기본). research: 자료 수집 (extract/scroll_full + notes/ 저장)")
    parser.add_argument("--max-visits", type=int, default=8,
                        help="research 모드: TODO 큐로 방문할 최대 페이지 수 (기본 8)")
    parser.add_argument("goal", nargs="*", help="자연어 목표")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    goal = " ".join(args.goal).strip()
    if not goal:
        try:
            goal = input("목표(자연어): ").strip()
        except EOFError:
            goal = ""
    if not goal:
        log.error("목표가 비어 있다. 예: python main.py \"구글에서 'playwright cdp' 검색\"")
        return
    run_loop(goal, args.llm, args.ollama_model,
             start_url=args.url, mode=args.mode, max_visits=args.max_visits)


if __name__ == "__main__":
    main()
