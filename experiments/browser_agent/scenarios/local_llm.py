# FILE: experiments/browser_agent/scenarios/local_llm.py
"""local LLM 단일 주제, 5 SNS × 4 시나리오 = 20개. 전부 research 모드.
TODO 역치 풀어 한 시나리오에서 많이 돌아다니도록 max_visits=6.
검증 포인트: 단일 주제 deep dive로 briefings/ 폴더에 사실 정리가 누적되는지.
형식: (id, mode, max_visits, url, goal).
"""

SCENARIOS = [
    # --- X (트위터) — 검색 위주 ---
    (1, "research", 6, "https://x.com/search?q=ollama&f=live", "ollama 관련 최근 트윗 본문 수집"),
    (2, "research", 6, "https://x.com/search?q=local%20llm&f=live", "local LLM 관련 최근 트윗 본문 수집"),
    (3, "research", 6, "https://x.com/search?q=llama.cpp&f=live", "llama.cpp 관련 최근 트윗 본문 수집"),
    (4, "research", 6, "https://x.com/search?q=mistral%207b&f=live", "mistral 7b 관련 최근 트윗 본문 수집"),

    # --- Reddit — local llm 핵심 sub들 ---
    (5, "research", 6, "https://old.reddit.com/r/LocalLLaMA/", "r/LocalLLaMA 최근 게시물 본문 수집"),
    (6, "research", 6, "https://old.reddit.com/r/ollama/", "r/ollama 최근 게시물 본문 수집"),
    (7, "research", 6, "https://old.reddit.com/r/LocalLLaMA/search/?q=ollama&restrict_sr=1", "r/LocalLLaMA에서 ollama 검색 결과 본문 수집"),
    (8, "research", 6, "https://old.reddit.com/r/MachineLearning/search/?q=local+model+inference&restrict_sr=1", "r/MachineLearning에서 local model inference 검색 결과 본문 수집"),

    # --- YouTube — 튜토리얼/리뷰 ---
    (9, "research", 6, "https://www.youtube.com/results?search_query=ollama+tutorial", "ollama tutorial 검색 결과 영상 제목과 채널 수집"),
    (10, "research", 6, "https://www.youtube.com/results?search_query=local+llm+setup", "local llm setup 검색 결과 수집"),
    (11, "research", 6, "https://www.youtube.com/results?search_query=llama.cpp+performance", "llama.cpp performance 검색 결과 수집"),
    (12, "research", 6, "https://www.youtube.com/results?search_query=mistral+ollama", "mistral ollama 검색 결과 수집"),

    # --- Mastodon — 페디버스 해시태그 ---
    (13, "research", 6, "https://mastodon.social/tags/ollama", "ollama 해시태그 본문 수집"),
    (14, "research", 6, "https://mastodon.social/tags/LocalLLM", "LocalLLM 해시태그 본문 수집"),
    (15, "research", 6, "https://mastodon.social/tags/llamacpp", "llamacpp 해시태그 본문 수집"),
    (16, "research", 6, "https://mastodon.social/tags/LLM", "LLM 해시태그에서 local 관련 toot 수집"),

    # --- Bluesky — 검색 ---
    (17, "research", 6, "https://bsky.app/search?q=ollama", "ollama 검색 결과 본문 수집"),
    (18, "research", 6, "https://bsky.app/search?q=local%20llm", "local llm 검색 결과 본문 수집"),
    (19, "research", 6, "https://bsky.app/search?q=llama.cpp", "llama.cpp 검색 결과 본문 수집"),
    (20, "research", 6, "https://bsky.app/search?q=mistral%207b", "mistral 7b 검색 결과 본문 수집"),
]
