# FILE: experiments/browser_agent/dom_indexer.py
# 현재 활성 페이지에서 "보이는 인터랙티브 요소"만 추출.
# 가시성: viewport 안 + 크기 > 0 + display/visibility/opacity OK + aria-hidden 아님 + 가려짐 검사
# 인터랙티브: a, button, input, select, textarea, [role=button], [onclick], [tabindex], contenteditable

import time

JS_INDEX = r"""
(() => {
  const SEL = 'a, button, input, select, textarea, [role="button"], [onclick], [tabindex], [contenteditable=""], [contenteditable="true"]';

  const isVisible = (el) => {
    const style = getComputedStyle(el);
    if (style.display === 'none') return false;
    if (style.visibility === 'hidden') return false;
    if (parseFloat(style.opacity || '1') <= 0.01) return false;
    if (el.getAttribute('aria-hidden') === 'true') return false;

    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    // viewport 교차 검사 (요소 일부라도 보이면 OK)
    if (rect.bottom < 0 || rect.top > window.innerHeight) return false;
    if (rect.right < 0 || rect.left > window.innerWidth) return false;

    // 가려짐 검사: 중심점이 viewport 밖이면 보이는 모서리로 보정
    const cx = Math.max(0, Math.min(window.innerWidth - 1, rect.left + rect.width / 2));
    const cy = Math.max(0, Math.min(window.innerHeight - 1, rect.top + rect.height / 2));
    const top = document.elementFromPoint(cx, cy);
    if (!top) return false;
    // 자기 자신이거나 자손이어야 함
    if (top !== el && !el.contains(top)) return false;
    return true;
  };

  // 이전 인덱스 클리어
  document.querySelectorAll('[data-agent-idx]').forEach(el => el.removeAttribute('data-agent-idx'));

  const results = [];
  const all = document.querySelectorAll(SEL);
  let idx = 1;
  for (const el of all) {
    let ok = false;
    try { ok = isVisible(el); } catch (e) { ok = false; }
    if (!ok) continue;

    const tag = el.tagName.toLowerCase();
    const id = el.getAttribute('id');
    const aria = el.getAttribute('aria-label');
    const name = el.getAttribute('name');
    const type = el.getAttribute('type');
    const role = el.getAttribute('role');
    const placeholder = el.getAttribute('placeholder');
    const title = el.getAttribute('title');

    // text 후보 우선순위: innerText → value → placeholder → title.
    // Reddit 등에서 <a title="진짜 제목">https://...</a> 패턴이 자주 나오므로 title도 폴백.
    let text = (el.innerText || el.value || el.placeholder || title || '').toString();
    text = text.trim().replace(/\s+/g, ' ').slice(0, 80);

    // 노이즈 필터: 라벨이라 부를 만한 게 전혀 없으면 스킵.
    // text/aria/name/placeholder/title 중 하나도 없는 빈 박스(<a></a>, <div role="button"></div> 등)는
    // 사용자가 식별할 수 없고 LLM이 헷갈리게만 함.
    const hasLabel = text || aria || name || placeholder || title;
    if (!hasLabel) continue;

    const attrs = [];
    if (id) attrs.push(`id="${id}"`);
    if (aria) attrs.push(`aria-label="${aria}"`);
    if (name) attrs.push(`name="${name}"`);
    if (type) attrs.push(`type="${type}"`);
    if (role) attrs.push(`role="${role}"`);
    if (title) attrs.push(`title="${title}"`);

    el.setAttribute('data-agent-idx', String(idx));
    results.push({ idx, tag, text, attrs: attrs.join(' ') });
    idx++;
  }
  return results;
})()
"""


def index_page(page, max_eval_retries=2):
    """현재 페이지를 인덱싱.
    반환: (직렬화 문자열, {idx: Locator} 매핑)
    SPA 등에서 evaluate가 navigation 도중 죽는 경우 짧게 대기 후 재시도.
    """
    items = None
    last_err = None
    for attempt in range(max_eval_retries + 1):
        try:
            items = page.evaluate(JS_INDEX)
            break
        except Exception as e:
            last_err = e
            msg = str(e)
            # navigation/context destroyed 류만 재시도. 다른 종류는 즉시 raise.
            recoverable = (
                "Execution context was destroyed" in msg
                or "navigating" in msg
                or "Target closed" in msg
            )
            if not recoverable or attempt >= max_eval_retries:
                raise
            time.sleep(1.0)

    lines = []
    mapping = {}
    for item in items or []:
        i = item["idx"]
        attrs = item["attrs"]
        head = f"<{item['tag']}" + (f" {attrs}" if attrs else "") + ">"
        tail = f"</{item['tag']}>"
        lines.append(f"[{i}]{head}{item['text']}{tail}")
        mapping[i] = page.locator(f'[data-agent-idx="{i}"]')
    return "\n".join(lines), mapping
