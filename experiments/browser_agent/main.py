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
import re
import sys
import json
import time
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

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
- "action": "click" | "type" | "scroll" | "back" | "done"
- "index": int. click/type일 때만 필수. 현재 스텝의 인덱스 목록 안의 번호.
- "text":  string.
    * type일 때: 입력할 문자열
    * scroll일 때: "up" 또는 "down"
    * done일 때: 결과 요약(선택)
    * back일 때: 비워둠

[back 액션 사용 시점]
- 직전 액션 후 외부 도메인으로 이탈했거나, 의도한 페이지가 아닌 곳으로 이동했다면 'back'으로 되돌아가라.
- 매 스텝 시작 시 OBS의 [직전 변화] 라인을 먼저 보고, URL/TITLE이 의도와 어긋났으면 'back'.
- 'back' 후엔 다시 인덱스 목록을 보고 다른 후보를 클릭한다.

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
_RUN_TS = datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_FILE = LOG_DIR / f"run_{_RUN_TS}.log"
# 검증자(다른 Claude 세션) first-pass용 경량 요약 — STEP/URL/ACTION/RESULT 만.
# 큰 SPA 로그는 한 줄당 수백KB라 grep도 까다로워서, 같은 흐름을 TSV로 따로 떨군다.
SUMMARY_FILE = LOG_DIR / f"run_{_RUN_TS}.summary.tsv"
# runner 같은 외부 wrapper와의 계약. 컬럼 추가/순서 변경 시 이 상수와 write_summary_header
# 를 함께 수정해야 wrapper의 헤더 검증에서 즉시 잡힌다.
SUMMARY_COLUMNS = ("step", "url", "action", "result")
SUMMARY_FILE_GLOB = "run_*.summary.tsv"
# 매 step의 LLM input/output + 페이지 텍스트 풀 dump. .log와 .summary.tsv로는 잡히지 않는
# 사후 검증용 트레일. 한 줄에 한 step의 JSON record가 들어간다.
STEPS_FILE = LOG_DIR / f"run_{_RUN_TS}.steps.jsonl"
STEPS_FILE_GLOB = "run_*.steps.jsonl"
# research 모드의 구조화 자료. 한 record = 한 페이지 (url + title + text excerpt + goal + platform).
# 모든 run 누적 → run_id로 필터해 브리핑 생성에 사용. 노트 .md(자유 본문)와 보완 관계.
RESEARCH_DIR = Path(__file__).parent / "research"
RESEARCH_DIR.mkdir(exist_ok=True)
RESEARCH_FILE = RESEARCH_DIR / "records.jsonl"
# 목표 단위 합성 브리핑. run 끝에 LLM이 records 모아 "알아낸 것"으로 정리.
BRIEFINGS_DIR = Path(__file__).parent / "briefings"
BRIEFINGS_DIR.mkdir(exist_ok=True)

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


def log_index(serialized):
    """INDEX 결과를 한 라인씩 logger.info로 분리 출력.
    원래 한 번에 log.info(serialized) 했더니 SPA에서 한 줄 길이 600KB+ 폭주 → grep -A/-B
    무용 + 큰 로그를 Read 시 컨텍스트 폭파. 줄 단위로 끊어 두 문제 모두 회피.
    """
    if not serialized:
        log.info("(없음)")
        return
    for line in serialized.split("\n"):
        log.info(line)


def _tsv_safe(s):
    """TSV 필드용 sanitize — tab/newline은 \\t / \\n 리터럴로 치환."""
    return str(s).replace("\t", "\\t").replace("\r", "").replace("\n", "\\n")


def write_summary_header():
    """run_loop 시작 시 한 번 호출. summary tsv 헤더 초기화."""
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("\t".join(SUMMARY_COLUMNS) + "\n")


def write_step_record(record):
    """매 step의 풀 트레일을 jsonl로 한 줄 append. record는 dict.
    필드: step, url, title, llm_input_msgs, llm_output_raw, llm_attempts,
          action, result, page_text_excerpt(옵션). default=str로 직렬화 안 되는 객체 안전하게.
    """
    with open(STEPS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def append_summary(step, url, action_obj, result):
    """매 STEP 끝에 한 줄 append. action_obj는 thought 빼고 압축해서 기록."""
    if action_obj is None:
        action_str = ""
    else:
        compact = {k: v for k, v in action_obj.items() if k != "thought"}
        action_str = json.dumps(compact, ensure_ascii=False)
    row = "\t".join(_tsv_safe(x) for x in (step, url, action_str, result))
    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(row + "\n")


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


def _slugify(s, maxlen=60):
    """파일/디렉토리명 안전 변환. 한글 유지, 공백/슬래시는 _, 다른 특수문자는 제거."""
    s = re.sub(r"[\\/:*?\"<>|]", "", s or "")
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:maxlen] or "untitled"


def append_research_record(goal, info, run_id, start_domain=""):
    """info: EXTRACT_JS / SCROLL_COLLECT_JS의 반환 dict (url, title, text).
    P16: 외부 도메인이면 record["is_external"]=True로 표시만 — 차단하지 않음 (정보 많을수록 좋음).
    """
    text = info.get("text", "") or ""
    cur_dom = urlparse(info.get("url", "")).netloc
    is_external = bool(start_domain and cur_dom and cur_dom != start_domain)
    if is_external:
        log.info(f"[RECORD-EXT] 외부 도메인 record 저장 (시작 {start_domain} → {cur_dom})")
    record = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "goal": goal,
        "platform": cur_dom,
        "url": info.get("url", ""),
        "title": info.get("title", ""),
        "text_excerpt": text[:3000],
        "text_len": len(text),
        "is_external": is_external,
    }
    with open(RESEARCH_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def generate_briefing(goal, run_id, provider, client):
    """RESEARCH_FILE에서 이 run_id의 records를 읽고, LLM에게 합성 브리핑 요청.
    briefings/{date}_{slug}/briefing.md 에 저장. records 0개면 skip.
    """
    if not RESEARCH_FILE.exists():
        return None
    records = []
    with open(RESEARCH_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("run_id") == run_id:
                    records.append(r)
            except Exception:
                continue
    if not records:
        log.info("[BRIEFING] records 0개 — skip")
        return None
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = BRIEFINGS_DIR / f"{date_str}_{_slugify(goal)}"
    out_dir.mkdir(exist_ok=True, parents=True)
    out_file = out_dir / "briefing.md"
    # LLM 입력: 각 record의 본문 2500자(저장된 3000자 거의 풀)까지 포함 — 정보 누락 최소화.
    sources_md = []
    llm_blocks = []
    for i, r in enumerate(records, 1):
        ext_tag = " (외부)" if r.get("is_external") else ""
        sources_md.append(f"{i}. [{r.get('title') or '(no title)'}]({r['url']}) — {r['platform']}{ext_tag}")
        excerpt = (r.get("text_excerpt") or "")[:2500]
        llm_blocks.append(f"[{i}] {r['platform']}{ext_tag} | {r.get('title','')} | {r['url']}\n{excerpt}")
    prompt = (
        f'사용자 목표: "{goal}"\n\n'
        f"수집한 자료 (총 {len(records)}개 페이지):\n\n"
        + "\n\n---\n\n".join(llm_blocks) + "\n\n"
        + "---\n\n"
        f"위 자료에서 알아낸 사실을 한국어 markdown으로 정리하라.\n"
        f"규칙:\n"
        f"- 자료에 명시된 사실을 **누락 없이** 모두 포함. 압축하거나 생략 금지. 풍부하게.\n"
        f"- **중복 제거**: 동일 사실이 여러 출처에 있으면 한 번만 적고 출처를 [출처:1, 3, 5] 식으로 합쳐라.\n"
        f"- 주제/카테고리별로 그룹핑(`## 소제목` 사용) 권장.\n"
        f"- 각 항목은 1~3 문장으로 구체적으로. 너무 짧게 자르지 말 것.\n"
        f"- 자료에 없는 추측/일반론 절대 금지.\n"
        f"- 인용은 [출처:N] 또는 [출처:N, M] 형식.\n"
        f"출력은 markdown bullet/heading 자유. 제목 줄(# ...) 없이 바로 본문부터."
    )
    try:
        msgs = [{"role": "system", "content": "너는 수집된 웹 자료를 사실 위주로 정리하는 어시스턴트다."},
                {"role": "user", "content": prompt}]
        # ollama는 PoC에서 format="json"이 기본이지만, briefing은 자유 markdown 원함 → format=None.
        if provider == "ollama":
            bullets = client.chat(msgs, format=None) or "(LLM 빈 응답)"
        else:
            bullets = client.chat(msgs) or "(LLM 빈 응답)"
    except Exception as e:
        bullets = f"(LLM 호출 실패: {e})"
    md = (
        f"# 브리핑: {goal}\n\n"
        f"- 날짜: {date_str}\n"
        f"- run_id: {run_id}\n"
        f"- 수집 페이지 수: {len(records)}\n"
        f"- 플랫폼: {', '.join(sorted({r['platform'] for r in records if r['platform']}))}\n\n"
        f"## 알아낸 것\n\n{bullets.strip()}\n\n"
        f"## 출처\n\n" + "\n".join(sources_md) + "\n"
    )
    out_file.write_text(md, encoding="utf-8")
    log.info(f"[BRIEFING] saved: {out_file}")
    return out_file


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
            def chat(self, messages, stream=False, options=None, format="json"):
                # format 기본 "json" — agent 응답용. briefing 같은 자유 markdown은 format=None.
                response = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    format=format,
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


def call_llm(provider, client, history, system_prompt, max_retries=2, step_record=None):
    """LLM 호출 + JSON 파싱. 파싱 실패 시 직전 raw + JSON 예시를 hint로 붙여 재시도.
    step_record(dict)이 주어지면 매 step의 LLM input/output 풀을 채워 사후 검증용 트레일을 남김.
    """
    base_msgs = normalize_history(provider, history, system_prompt)
    if step_record is not None:
        # 입력 msgs는 retry hint 추가 전 base만 저장 — retry hint는 .log의 PARSE FAIL 라인으로도 추적 가능.
        step_record["llm_input_msgs"] = base_msgs
    msgs = base_msgs
    last_err = None
    for attempt in range(max_retries + 1):
        raw = client.chat(msgs) or ""
        # preview 1000자: 짧은 응답이면 그대로 다 보임. 디버깅용.
        preview = raw.replace("\n", " ")[:1000]
        log.info(f"RAW (attempt {attempt + 1}): {preview!r}")
        try:
            obj = parse_json_response(raw)
            if step_record is not None:
                step_record["llm_output_raw"] = raw
                step_record["llm_attempts"] = attempt + 1
            return obj, raw
        except Exception as e:
            last_err = e
            log.warning(f"[PARSE FAIL attempt {attempt + 1}/{max_retries + 1}] {e}")
            # PARSE FAIL 케이스에서만 풀 raw를 별도 라인으로 dump.
            # preview에서 잘리면 무엇이 잘못된 응답인지 알 수가 없어서.
            full = raw.replace("\n", "\\n")  # tab/newline 안 깨지게
            log.warning(f"[PARSE FAIL raw-full] {full!r}")
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
                   url_text_lens=None, todo_queue=None, todo_state=None,
                   start_domain=""):
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
            append_research_record(goal, info, _RUN_TS, start_domain=start_domain)
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
            append_research_record(goal, info, _RUN_TS, start_domain=start_domain)
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
    if action == "back":
        try:
            page.go_back(timeout=5000, wait_until="domcontentloaded")
            return "OK: navigated back"
        except Exception as e:
            return f"FAIL: back failed: {e}"
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
            time.sleep(5)  # SPA 비동기 fetch 대기 — X 검색 결과 같은 페이지가 1.5s에 미완 (#1~3 텍스트 빈 본문 진단 결과)
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
        log_index(serialized)


def run_loop(goal, provider, ollama_model, start_url=None, mode="action", max_visits=8):
    log.info("=== AGENT START ===")
    log.info(f"log file: {LOG_FILE}")
    log.info(f"summary : {SUMMARY_FILE}")
    log.info(f"steps   : {STEPS_FILE}")
    log.info(f"GOAL    : {goal}")
    log.info(f"MODE    : {mode}")
    log.info(f"PROVIDER: {provider}")
    write_summary_header()

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
    except Exception:
        log.exception("LLM 초기화 실패")
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
        # P1: UNKNOWN ACTION 연속 streak — gemma4가 알 수 없는 액션 키(tool_code/end/{}) 환각 시
        # 같은 짓 매 step 반복하며 timeout 도달하는 패턴 가드. 3회 누적 시 강제 종료.
        unknown_streak = 0
        # P10: UNKNOWN 누적 카운트 — streak이 정상 액션 사이에 reset되어 못 잡는 패턴.
        # 누적은 reset 없이 5회 도달 시 강제 종료.
        unknown_total = 0
        # P2: 동일 액션 반복 streak — 같은 (action, index, text) 시퀀스가 N회 OK로 반복되면
        # 무한 scroll 루프 등으로 판단해 강제 종료.
        last_action_sig = None
        repeat_streak = 0
        UNKNOWN_LIMIT = 3
        UNKNOWN_TOTAL_LIMIT = 5
        REPEAT_LIMIT = 6
        # P9: 페이지 무변화 가드. (URL, INDEX 앞 5000자 hash) sig가 N회 연속 동일하면
        # 비로그인 wall에서 무한 시도하는 패턴(#20 Mastodon)으로 보고 강제 종료.
        last_state_sig = None
        no_change_streak = 0
        NO_CHANGE_LIMIT = 4
        # P16/P17/P19: 시작 URL의 도메인. record는 외부도 그대로 저장(표시만).
        # P19: 외부에서 N step 머무르면 자동으로 시작 URL로 복귀 — "재귀적으로 시작으로 들어옴".
        start_domain = urlparse(start_url).netloc if start_url else ""
        domain_alerted = False
        external_step_count = 0
        EXTERNAL_RETURN_LIMIT = 4
        # P6: 직전 액션 전후 상태 비교용. observation에 [직전 변화] 한 줄을 넣어 LLM이
        # 의도와 다른 페이지로 이탈했는지 명시적으로 자각하고 back으로 회복하도록 한다.
        prev_url = None
        prev_title = None

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
                    append_research_record(goal, info, _RUN_TS, start_domain=start_domain)
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
                time.sleep(5)  # SPA 비동기 fetch 대기 — X 검색 결과 같은 페이지가 1.5s에 미완 (#1~3 텍스트 빈 본문 진단 결과)
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
                # 카운터도 새 항목과 함께 리셋 — 직전 항목의 streak이 다음 항목에 전이되어
                # 잘못된 강제 종료를 일으키지 않도록.
                unknown_streak = 0
                unknown_total = 0
                repeat_streak = 0
                last_action_sig = None
                prev_url = None
                prev_title = None
                no_change_streak = 0
                last_state_sig = None
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
                old_url, new_url = page.url, new_page.url
                log.info(f"[TAB SWITCH] {old_url} -> {new_url}")
                # P3: 외부 도메인으로 이동하면 prev_result에 ALERT prefix.
                # X 트윗 안 외부 링크가 "탭"으로 잘못 인식되어 클릭되는 트랩 — agent가 자각하도록.
                old_dom = urlparse(old_url).netloc
                new_dom = urlparse(new_url).netloc
                if old_dom and new_dom and old_dom != new_dom:
                    alert = (f"[ALERT] 외부 도메인으로 이동했음: {old_dom} → {new_dom}. "
                             f"의도와 다르면 done으로 종료하고 사용자에게 보고할 것.")
                    prev_result = alert + (f" | 직전: {prev_result}" if prev_result else "")
                    log.warning(alert)
                page = new_page
                page.bring_to_front()
            try:
                serialized, mapping = index_page(page)
            except Exception:
                log.exception("[INDEX FAIL]")
                break

            url = page.url
            try:
                title = page.title()
            except Exception:
                title = ""

            # P17/P19: 시작 도메인을 벗어났으면 ALERT + 카운트.
            # 외부에서 EXTERNAL_RETURN_LIMIT step 머무르면 자동으로 시작 URL로 복귀
            # — "외부에서 좀 보다가 재귀적으로 시작으로 다시 들어옴".
            cur_dom = urlparse(url).netloc
            if start_domain and cur_dom and cur_dom != start_domain:
                external_step_count += 1
                if not domain_alerted:
                    redirect_alert = (
                        f"[REDIRECT-ALERT] 시작 도메인({start_domain})에서 벗어남 → 현재: {cur_dom}. "
                        f"외부에서 자료 좀 보다가 다시 시작 URL로 복귀할 수도 있음."
                    )
                    prev_result = redirect_alert + (f" | 직전: {prev_result}" if prev_result else "")
                    domain_alerted = True
                    log.warning(redirect_alert)
                if external_step_count >= EXTERNAL_RETURN_LIMIT and start_url:
                    try:
                        page.goto(start_url, wait_until="domcontentloaded", timeout=15000)
                        time.sleep(5)  # SPA 비동기 fetch 대기 — X 검색 결과 같은 페이지가 1.5s에 미완 (#1~3 텍스트 빈 본문 진단 결과)
                        external_step_count = 0
                        domain_alerted = False
                        prev_result = (f"[AUTO-RETURN] 외부에서 {EXTERNAL_RETURN_LIMIT} step 머물러 "
                                       f"시작 URL({start_domain})로 자동 복귀했음. 다른 인덱스/링크 시도하라.")
                        log.warning(prev_result)
                        continue
                    except Exception as e:
                        log.warning(f"[AUTO-RETURN 실패] {e}")
            elif start_domain and cur_dom == start_domain:
                # 시작 도메인으로 복귀 — 다음에 또 벗어나면 alert + 카운트 다시.
                domain_alerted = False
                external_step_count = 0

            log.info(f"=== STEP {step} ===")
            log.info(f"URL  : {url}")
            log.info(f"TITLE: {title}")
            log.info("--- INDEX ---")
            log_index(serialized)

            # 매 step의 풀 트레일 record. call_llm + 결과 처리 단계에서 점진 채움.
            step_record = {"step": step, "url": url, "title": title, "mode": mode}

            obs_parts = [f"GOAL: {goal}", "", f"URL: {url}", f"TITLE: {title}"]
            # P6: 직전 변화 한 줄. URL/TITLE이 변했으면 명시. 변화 없으면 그것도 신호 (액션이 효과 없었음).
            if prev_url is not None:
                if prev_url == url and prev_title == title:
                    obs_parts.append("[직전 변화] (URL/TITLE 동일 — 직전 액션이 페이지를 바꾸지 않음)")
                else:
                    obs_parts.append(f"[직전 변화] URL: {prev_url} → {url} | TITLE: {prev_title} → {title}")
            obs_parts.append("")
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
                action_obj, raw = call_llm(provider_name, client, history, system_prompt,
                                           step_record=step_record)
            except Exception:
                log.exception("[LLM FAIL]")
                step_record["error"] = "LLM_FAIL"
                write_step_record(step_record)
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
                # P5+P8: done text에 retry hint leak 검사. 정규식으로 변형 흡수
                # ("자동 재시도 요청", "재시도 상황", "재요청 신호" 등 어순/조사 변형 다 잡음).
                # 일반 단어("재시도 후 성공") 오인 회피 위해 키워드 인접 패턴만.
                done_text = action_obj.get("text", "") or ""
                LEAK_RE = re.compile(
                    r"재시도\s*(지침|요청|상황|신호)"
                    r"|재요청\s*(신호|지침)"
                    r"|SYSTEM[-_]?RETRY"
                    r"|자동\s*재(시도|요청)"
                    r"|시스템\s*재(시도|요청)"
                )
                if LEAK_RE.search(done_text):
                    log.warning(f"[LEAK] done text에 retry hint 패턴 검출, 텍스트 비움: {done_text[:120]!r}")
                    action_obj["text"] = "(retry hint leak이 감지되어 텍스트를 비웠음 — 실제 결과 미확정)"
                result_msg = f"DONE — {action_obj.get('text', '')}"
                log.info(f"RESULT : {result_msg}")
                append_summary(step, page.url, action_obj, result_msg)
                step_record["action"] = action_obj
                step_record["result"] = result_msg
                write_step_record(step_record)
                break

            try:
                result = execute_action(
                    page, action_obj, mapping,
                    note_file=note_file, goal=goal, url_text_lens=url_text_lens,
                    todo_queue=todo_queue, todo_state=todo_state,
                    start_domain=start_domain,
                )
            except Exception as e:
                result = f"FAIL: {e}"
            log.info(f"RESULT : {result}")
            append_summary(step, page.url, action_obj, result)
            step_record["action"] = action_obj
            step_record["result"] = result
            # 실제 페이지 본문 6000자 — INDEX 텍스트로는 안 보이는 본문/오류 페이지 텍스트 검증용.
            try:
                step_record["page_text_excerpt"] = page.evaluate(
                    "() => ((document.body && document.body.innerText) || '').slice(0, 6000)"
                )
            except Exception as e:
                step_record["page_text_excerpt"] = f"(evaluate failed: {e})"
            write_step_record(step_record)
            # P6: 다음 step에서 [직전 변화]를 만들 수 있도록 현재 상태 저장.
            prev_url, prev_title = url, title

            # P1+P10: UNKNOWN ACTION 가드. streak(연속) + total(누적) 두 카운트.
            # streak은 빠른 검출(3회 연속), total은 정상 액션 사이에 끼어들어 reset되는 패턴 잡음.
            if result.startswith("UNKNOWN ACTION"):
                unknown_streak += 1
                unknown_total += 1
                allowed = "click, type, scroll, back, done"
                if mode == "research":
                    allowed += ", extract, scroll_full, add_todo, next_todo"
                hint = (f"직전 응답이 알 수 없는 액션이었다. 사용 가능한 'action' 값은 "
                        f"오직 [{allowed}] 중 하나. JSON 키는 반드시 'action'.")
                prev_result = result + " | " + hint
                if unknown_streak >= UNKNOWN_LIMIT:
                    log.warning(f"[GUARD] UNKNOWN ACTION {unknown_streak}회 연속 → 강제 종료")
                    break
                if unknown_total >= UNKNOWN_TOTAL_LIMIT:
                    log.warning(f"[GUARD] UNKNOWN ACTION 누적 {unknown_total}회 → 강제 종료")
                    break
            else:
                unknown_streak = 0
                prev_result = result

            # P2: 동일 액션 반복 streak. 같은 (action, index, text)가 OK로 K번 반복되면
            # 무한 scroll/click 루프로 판단. 정상 동작에서는 같은 행위가 그렇게 자주 반복되지 않음.
            sig = (action_obj.get("action"), action_obj.get("index"), action_obj.get("text"))
            if sig == last_action_sig and result.startswith("OK"):
                repeat_streak += 1
                if repeat_streak >= REPEAT_LIMIT:
                    log.warning(f"[GUARD] 같은 액션 {repeat_streak}회 반복({sig}) → 강제 종료")
                    break
            else:
                repeat_streak = 0
            last_action_sig = sig

            # P9+P15: 페이지 무변화 가드. INDEX 기반은 SPA 미세변화로 우회되는 사례가 있어
            # (#7 YannicKilcher TIMEOUT 진단), 이번 step 끝에 잡힌 page_text_excerpt 앞 3000자 hash로
            # 비교한다. page text는 INDEX보다 안정적 — 진짜 페이지 내용이 같은지 직접 봄.
            cur_page_text = (step_record.get("page_text_excerpt", "") or "")[:3000]
            cur_state_sig = (url, hashlib.md5(cur_page_text.encode("utf-8")).hexdigest())
            if cur_state_sig == last_state_sig:
                no_change_streak += 1
                if no_change_streak >= NO_CHANGE_LIMIT:
                    log.warning(f"[GUARD] 페이지 무변화 {no_change_streak}회 → 강제 종료")
                    break
            else:
                no_change_streak = 0
            last_state_sig = cur_state_sig

            time.sleep(1)
        else:
            log.warning(f"MAX_STEPS({max_steps}) 도달. 종료.")

    log.info("=== AGENT END ===")
    if note_file:
        log.info(f"노트 파일: {note_file}")
    # research 모드면 이번 run의 records 모아 LLM 합성 브리핑 한 장 생성.
    if mode == "research":
        try:
            generate_briefing(goal, _RUN_TS, provider_name, client)
        except Exception:
            log.exception("[BRIEFING] 생성 실패")


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

    # 명령 인자 dump — 다른 세션이 같은 시나리오를 reproduce할 수 있게.
    log.info(f"ARGS    : {vars(args)}")

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
