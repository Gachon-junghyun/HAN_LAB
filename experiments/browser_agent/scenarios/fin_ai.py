# FILE: experiments/browser_agent/scenarios/fin_ai.py
"""금융 + AI 주제, 인스타/X/여러 SNS 혼합. 브리핑 자동 생성 검증 + 비로그인 wall 검증.
대부분 research 모드 — briefing이 합성 결과물의 품질을 보여줌.
형식: (id, mode, max_visits, url, goal). max_visits는 research에서만 사용.
"""

SCENARIOS = [
    # --- AI 주제 ---
    (1, "action", 0, "https://x.com/AnthropicAI", "팔로워 수와 게시물 수를 done 요약에 적어"),
    (2, "research", 3, "https://x.com/karpathy", "이 계정의 최근 트윗 본문을 모아줘"),
    (3, "research", 3, "https://x.com/search?q=AI%20safety&f=live", "AI safety 관련 최근 트윗 본문 수집"),
    (4, "action", 0, "https://www.reddit.com/r/MachineLearning/", "최신 게시물의 제목을 done에 적어"),
    (5, "research", 3, "https://old.reddit.com/r/artificial/", "최근 게시물 5개 제목과 요약 수집"),
    (6, "action", 0, "https://www.youtube.com/", "검색창에 'transformer attention is all you need' 입력하고 검색 실행"),
    (7, "research", 2, "https://www.youtube.com/@YannicKilcher/videos", "최근 AI 논문 리뷰 영상 제목 10개 수집"),
    (8, "research", 2, "https://bsky.app/search?q=AI%20safety", "AI safety 검색 결과 본문 수집"),
    (9, "research", 2, "https://mastodon.social/tags/MachineLearning", "MachineLearning 해시태그 본문 수집"),
    (10, "action", 0, "https://www.instagram.com/anthropic/", "이 페이지에 무엇이 표시되는지 done에 요약"),

    # --- 금융 주제 ---
    (11, "research", 3, "https://x.com/ReutersBiz", "Reuters Business 계정의 최근 트윗 본문을 모아줘"),
    (12, "research", 3, "https://x.com/search?q=S%26P%20500&f=live", "S&P 500 관련 최근 트윗 본문 수집"),
    (13, "action", 0, "https://www.reddit.com/r/wallstreetbets/", "최신 게시물의 제목을 done에 적어"),
    (14, "research", 3, "https://old.reddit.com/r/finance/search/?q=inflation&restrict_sr=1", "inflation 검색 결과에서 흥미로운 게시물 3개 수집"),
    (15, "research", 2, "https://www.youtube.com/results?search_query=stock+market+today", "stock market today 검색 결과 첫 영상 제목과 채널 수집"),
    (16, "research", 2, "https://bsky.app/search?q=stocks", "stocks 검색 결과 본문 수집"),
    (17, "research", 2, "https://mastodon.social/tags/finance", "finance 해시태그 본문 수집"),
    (18, "action", 0, "https://www.instagram.com/wsj/", "이 페이지에 무엇이 표시되는지 done에 요약"),
    (19, "research", 2, "https://www.threads.net/@zuck", "이 계정의 최근 게시물 본문을 모아줘"),
    (20, "research", 2, "https://www.threads.net/search?q=bitcoin", "bitcoin 검색 결과 본문 수집"),
]
