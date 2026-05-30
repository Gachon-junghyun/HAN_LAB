# FILE: experiments/browser_agent/ingest/reddit_api.py
"""Reddit 무인증 read-only — URL 끝에 `.json` 붙이면 구조화된 JSON 반환.
HTML 크롤링보다 깔끔 (메뉴/사이드바 잡설 0). 검색/sub/게시물 다 동일 패턴.

사용:
    posts = fetch_subreddit("LocalLLaMA", limit=10)
    posts = search_subreddit("LocalLLaMA", "ollama", limit=10)
    comments = fetch_post_comments("LocalLLaMA", "1pvjpmb")

반환: dict의 list. 각 dict는 normalize_post() 결과 (url, title, author, body, score, num_comments, created).
"""
import urllib.request
import urllib.parse
import json
from datetime import datetime, timezone

USER_AGENT = "Mozilla/5.0 (HAN_LAB browser_agent ingest module)"
_TIMEOUT = 15


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _normalize_post(child: dict) -> dict:
    d = child.get("data", {})
    return {
        "url": "https://old.reddit.com" + d.get("permalink", ""),
        "external_url": d.get("url", ""),
        "title": d.get("title", ""),
        "author": d.get("author", ""),
        "subreddit": d.get("subreddit", ""),
        "body": d.get("selftext", ""),
        "score": d.get("score", 0),
        "num_comments": d.get("num_comments", 0),
        "created": datetime.fromtimestamp(
            d.get("created_utc", 0), tz=timezone.utc).isoformat(),
        "flair": d.get("link_flair_text", ""),
        "is_video": d.get("is_video", False),
    }


def fetch_subreddit(sub: str, limit: int = 25, sort: str = "hot") -> list:
    """sub: 'LocalLLaMA' (r/ 빼고). sort: hot|new|top|rising."""
    url = f"https://old.reddit.com/r/{sub}/{sort}.json?limit={limit}"
    data = _fetch_json(url)
    return [_normalize_post(c) for c in data.get("data", {}).get("children", [])]


def search_subreddit(sub: str, query: str, limit: int = 25, sort: str = "relevance") -> list:
    """sub 안에서만 검색 (restrict_sr=on). sort: relevance|top|new."""
    q = urllib.parse.quote(query)
    url = (f"https://old.reddit.com/r/{sub}/search.json"
           f"?q={q}&restrict_sr=on&limit={limit}&sort={sort}")
    data = _fetch_json(url)
    return [_normalize_post(c) for c in data.get("data", {}).get("children", [])]


def fetch_post_comments(sub: str, post_id: str, limit: int = 100) -> dict:
    """게시물 본문 + 최상위 댓글들. 반환: {'post': {...}, 'comments': [{author, body, score, created}, ...]}."""
    url = f"https://old.reddit.com/r/{sub}/comments/{post_id}.json?limit={limit}"
    data = _fetch_json(url)
    if not isinstance(data, list) or len(data) < 2:
        return {"post": None, "comments": []}
    post = _normalize_post(data[0]["data"]["children"][0]) if data[0]["data"]["children"] else None
    comments = []
    for c in data[1].get("data", {}).get("children", []):
        d = c.get("data", {})
        if d.get("body"):
            comments.append({
                "author": d.get("author", ""),
                "body": d.get("body", ""),
                "score": d.get("score", 0),
                "created": datetime.fromtimestamp(
                    d.get("created_utc", 0), tz=timezone.utc).isoformat(),
            })
    return {"post": post, "comments": comments}


if __name__ == "__main__":
    # smoke test
    posts = fetch_subreddit("LocalLLaMA", limit=3)
    for p in posts:
        print(f"[{p['score']:>5}] {p['title'][:80]} ({p['num_comments']} comments)")
        print(f"        {p['url']}")
