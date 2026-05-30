# FILE: experiments/browser_agent/test_rss_reddit.py
"""LLM/브라우저 없이 ingest 모듈(reddit_api + rss)만 standalone test.
실행: python test_rss_reddit.py
출력: stdout 한 줄씩 + scenarios/ingest_test_<ts>.md (markdown 한 장)
"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from ingest import reddit_api, rss

# 입력 묶음 — 본인 관심사로 교체 가능
REDDIT_SUBS = [
    ("LocalLLaMA", "hot", 10),
    ("ollama", "hot", 10),
    ("MachineLearning", "hot", 10),
]

RSS_FEEDS = [
    "https://hnrss.org/frontpage",
    "https://export.arxiv.org/rss/cs.CL",
    "https://export.arxiv.org/rss/cs.LG",
]


def main():
    lines = [f"# Ingest Test — {datetime.now().isoformat(timespec='seconds')}\n"]
    print(f"=== Ingest test ===")

    for sub, sort, limit in REDDIT_SUBS:
        print(f"\n[Reddit r/{sub} {sort} top {limit}]")
        try:
            posts = reddit_api.fetch_subreddit(sub, limit=limit, sort=sort)
        except Exception as e:
            print(f"  FAIL: {e}")
            lines.append(f"\n## r/{sub} (FAIL: {e})\n")
            continue
        lines.append(f"\n## r/{sub} ({sort}, {len(posts)}건)\n")
        for p in posts:
            row = f"- **[{p['score']:>5}↑]** [{p['title']}]({p['url']}) ({p['num_comments']} comments)"
            if p.get("flair"):
                row += f" `{p['flair']}`"
            lines.append(row)
            print(f"  [{p['score']:>5}↑] {p['title'][:80]}")

    for feed_url in RSS_FEEDS:
        print(f"\n[RSS {feed_url}]")
        try:
            items = rss.fetch_rss(feed_url, limit=10)
        except Exception as e:
            print(f"  FAIL: {e}")
            lines.append(f"\n## {feed_url} (FAIL: {e})\n")
            continue
        feed_title = items[0]["feed_title"] if items else feed_url
        lines.append(f"\n## {feed_title} ({len(items)}건)\n")
        for it in items:
            date = it["published"][:10] if it["published"] else "(no date)"
            lines.append(f"- [{date}] [{it['title']}]({it['url']})")
            print(f"  [{date}] {it['title'][:80]}")

    out_dir = HERE / "scenarios"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"ingest_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n=== Saved: {out_file}")


if __name__ == "__main__":
    main()
