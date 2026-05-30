# FILE: experiments/browser_agent/ingest/rss.py
"""RSS / Atom feed 수집. feedparser 사용 (있을 때만). 없으면 친절 에러.

사용:
    items = fetch_rss("https://hnrss.org/frontpage")
    items = fetch_many([url1, url2, ...])

반환: list of dict {url, title, summary, published, source}. records 통합 형식과 호환.
"""
from datetime import datetime
from urllib.parse import urlparse

try:
    import feedparser  # pip install feedparser
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def is_available() -> bool:
    return _AVAILABLE


def fetch_rss(feed_url: str, limit: int = 30) -> list:
    """RSS 한 개 fetch + normalize."""
    if not _AVAILABLE:
        raise RuntimeError("feedparser 미설치 — `pip install feedparser`")
    parsed = feedparser.parse(feed_url)
    out = []
    for e in parsed.entries[:limit]:
        # published 처리: published_parsed 우선, 없으면 updated_parsed
        ts = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        published = datetime(*ts[:6]).isoformat() if ts else ""
        out.append({
            "url": getattr(e, "link", ""),
            "title": getattr(e, "title", ""),
            "summary": getattr(e, "summary", "")[:3000],
            "published": published,
            "source": urlparse(feed_url).netloc or feed_url,
            "feed_title": getattr(parsed.feed, "title", ""),
        })
    return out


def fetch_many(feed_urls: list, limit_per: int = 30) -> list:
    """여러 feed 합쳐서 한 list로. 실패한 feed는 skip + log (print)."""
    out = []
    for u in feed_urls:
        try:
            out.extend(fetch_rss(u, limit=limit_per))
        except Exception as e:
            print(f"[RSS-FAIL] {u}: {e}")
    return out


# 자주 쓰는 feed 묶음 (참고용 — 사용자가 본인 관심사로 교체)
PRESETS = {
    "ai_dev": [
        "https://hnrss.org/frontpage",
        "https://feeds.feedburner.com/oreilly/radar",
    ],
    "ml_papers": [
        "https://export.arxiv.org/rss/cs.LG",
        "https://export.arxiv.org/rss/cs.CL",
    ],
}


if __name__ == "__main__":
    # smoke test
    if not _AVAILABLE:
        print("feedparser 미설치 — pip install feedparser")
    else:
        items = fetch_rss("https://hnrss.org/frontpage", limit=3)
        for it in items:
            print(f"[{it['published'][:10]}] {it['title'][:80]}")
            print(f"        {it['url']}")
