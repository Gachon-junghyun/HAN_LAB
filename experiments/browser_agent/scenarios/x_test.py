# FILE: experiments/browser_agent/scenarios/x_test.py
"""X 검색 페이지 SPA timing 검증 — sleep 1.5 → 5초 효과 확인."""

SCENARIOS = [
    (1, "research", 3, "https://x.com/search?q=ollama&f=live", "ollama 관련 최근 트윗 본문 수집"),
    (2, "research", 3, "https://x.com/search?q=local%20llm&f=live", "local LLM 관련 최근 트윗 본문 수집"),
    (3, "research", 3, "https://x.com/search?q=llama.cpp&f=live", "llama.cpp 관련 최근 트윗 본문 수집"),
]
