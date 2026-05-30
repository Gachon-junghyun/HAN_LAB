# FILE: experiments/browser_agent/scenarios/twitter.py
"""트위터(X) 시나리오 묶음. 직전 run의 회귀 검증용.
형식: (id, mode, max_visits, url, goal). max_visits는 research에서만 사용.
"""

SCENARIOS = [
    (1, "action", 0, "https://x.com/explore", "트렌드 1위 항목 클릭"),
    (2, "action", 0, "https://x.com/search?q=Anthropic&src=typed_query", "검색 결과에서 Anthropic 공식 계정 프로필로 들어가"),
    (3, "action", 0, "https://x.com", "검색창에 'claude AI' 입력하고 검색 실행"),
    (4, "action", 0, "https://x.com/AnthropicAI", "팔로워 수와 게시물 수를 done 요약에 적어"),
    (5, "action", 0, "https://x.com/AnthropicAI", "핀 고정된 트윗 클릭"),
    (6, "action", 0, "https://x.com/AnthropicAI/with_replies", "Media 탭으로 전환"),
    (7, "action", 0, "https://x.com/AnthropicAI/media", "첫 이미지 트윗을 클릭"),
    (8, "action", 0, "https://x.com/notifications", "이 페이지에 무엇이 표시되는지 done에 요약"),
    (9, "action", 0, "https://x.com/messages", "메시지 보내기 버튼 클릭"),
    (10, "action", 0, "https://x.com/i/flow/login", "로그인 페이지에서 'Forgot password?' 링크 클릭"),
    (11, "action", 0, "https://x.com/AnthropicAI", "트윗 본문 안의 외부 링크(anthropic.com 등) 하나 클릭"),
    (12, "action", 0, "https://x.com/explore/tabs/trending", "트렌드 5번째 항목 클릭"),
    (13, "action", 0, "https://x.com/search?q=anthropic", "Latest 탭으로 전환"),
    (14, "action", 0, "https://x.com/AnthropicAI/likes", "첫 좋아요 트윗 클릭"),
    (15, "research", 3, "https://x.com/AnthropicAI", "이 계정의 최근 트윗 본문을 모아줘"),
    (16, "research", 4, "https://x.com/search?q=AI%20safety&f=live", "AI safety 관련 트윗 본문 수집하고 흥미로운 계정 3개를 add_todo로 적어"),
    (17, "research", 5, "https://x.com/explore/tabs/trending", "트렌드 상위 3개를 각각 방문해서 본문 수집"),
    (18, "research", 3, "https://x.com/AnthropicAI", "@AnthropicAI 본문 모은 뒤 mention된 다른 계정 1개를 더 방문해 본문 수집"),
    (19, "research", 2, "https://x.com/hashtag/AI", "이 해시태그 페이지에서 본문 누적"),
    (20, "research", 2, "https://x.com/elonmusk", "이 계정의 최근 트윗과 핀 트윗 본문 수집"),
]
