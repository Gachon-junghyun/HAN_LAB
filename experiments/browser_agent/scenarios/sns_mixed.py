# FILE: experiments/browser_agent/scenarios/sns_mixed.py
"""혼합 SNS 시나리오 묶음 — X / Reddit / YouTube / Bluesky / Mastodon 각 4개.
PoC 일반화 검증 + 트위터 패치(P1~P5) 회귀 검증.
형식: (id, mode, max_visits, url, goal). max_visits는 research에서만 사용.
"""

SCENARIOS = [
    # --- X (트위터) 4개 — 직전 run 회귀 ---
    (1, "action", 0, "https://x.com/AnthropicAI", "팔로워 수와 게시물 수를 done 요약에 적어"),
    (2, "action", 0, "https://x.com/explore", "트렌드 1위 항목 클릭"),
    (3, "research", 3, "https://x.com/AnthropicAI", "이 계정의 최근 트윗 본문을 모아줘"),
    (4, "research", 5, "https://x.com/explore/tabs/trending", "트렌드 상위 3개를 각각 방문해서 본문 수집"),

    # --- Reddit 4개 — SSR/하이브리드, 봇차단 약함 ---
    (5, "action", 0, "https://old.reddit.com/r/MachineLearning/", "첫 게시물의 제목을 done에 적어"),
    (6, "action", 0, "https://www.reddit.com/", "검색창에 'transformer architecture' 입력하고 검색 실행"),
    (7, "research", 3, "https://old.reddit.com/r/programming/", "최근 게시물 5개의 제목과 요약을 수집"),
    (8, "research", 4, "https://www.reddit.com/r/learnpython/search/?q=async&restrict_sr=1", "검색 결과에서 흥미로운 게시물 3개를 add_todo로 적고 본문 수집"),

    # --- YouTube 4개 — 가상스크롤 끝판왕 ---
    (9, "action", 0, "https://www.youtube.com/", "검색창에 '3blue1brown' 입력하고 검색 실행"),
    (10, "action", 0, "https://www.youtube.com/@3blue1brown", "이 채널의 'Videos' 탭을 클릭"),
    (11, "research", 2, "https://www.youtube.com/@veritasium/videos", "최근 영상 제목 10개를 수집"),
    (12, "research", 2, "https://www.youtube.com/watch?v=aircAruvnKk", "이 영상의 댓글 본문을 수집"),

    # --- Bluesky 4개 — 신생 SPA, 비로그인 OK ---
    (13, "action", 0, "https://bsky.app/profile/bsky.app", "공식 계정의 최근 게시물 첫 번째 클릭"),
    (14, "action", 0, "https://bsky.app/search?q=anthropic", "검색 결과 첫 게시물 클릭"),
    (15, "research", 3, "https://bsky.app/profile/bsky.app", "공식 계정 최근 게시물 본문 수집"),
    (16, "research", 2, "https://bsky.app/hashtag/AI", "AI 해시태그 페이지 본문 수집"),

    # --- Mastodon 4개 — 페디버스, 봇차단 없음 (가장 깨끗한 baseline) ---
    (17, "action", 0, "https://mastodon.social/explore", "공개 트렌딩 게시물 첫 번째를 클릭"),
    (18, "action", 0, "https://mastodon.social/tags/AI", "AI 해시태그 페이지에서 첫 toot 클릭"),
    (19, "research", 2, "https://mastodon.social/public/local", "로컬 타임라인 toot 본문을 수집"),
    (20, "research", 3, "https://mastodon.social/@Mastodon", "공식 계정 본문과 mention된 다른 계정 1개를 follow하여 수집"),
]
