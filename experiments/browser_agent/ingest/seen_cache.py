# FILE: experiments/browser_agent/ingest/seen_cache.py
"""URL/content 해시 캐시 — 매일 자율 실행 시 어제 이전 본 콘텐츠 skip 용도.

사용 흐름:
    cache = SeenCache()
    if cache.is_new(url, body):
        # 처리 (records, brief 등)
        cache.mark(url, body)
    else:
        # skip 또는 'old' 표시

저장 형태: ingest/seen.json
    {
      "<url>": {"content_hash": "<md5>", "first_seen": ISO, "last_seen": ISO, "count": N}
    }

content_hash로 비교 — URL 같은데 본문 바뀐 경우(예: 핀 트윗 변경)도 'new'로 인식.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

_DEFAULT_PATH = Path(__file__).parent / "seen.json"


class SeenCache:
    def __init__(self, path: Path = _DEFAULT_PATH):
        self.path = Path(path)
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.md5((content or "").encode("utf-8")).hexdigest()

    def is_new(self, url: str, content: str = "") -> bool:
        """이 url+content 조합이 캐시에 없으면 True."""
        if url not in self.data:
            return True
        if content and self.data[url].get("content_hash") != self._hash(content):
            return True
        return False

    def mark(self, url: str, content: str = ""):
        """현재 시각 + content_hash로 갱신."""
        now = datetime.now().isoformat(timespec="seconds")
        h = self._hash(content)
        if url in self.data:
            self.data[url]["last_seen"] = now
            self.data[url]["count"] = self.data[url].get("count", 0) + 1
            self.data[url]["content_hash"] = h
        else:
            self.data[url] = {
                "content_hash": h,
                "first_seen": now,
                "last_seen": now,
                "count": 1,
            }

    def save(self):
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def stats(self) -> dict:
        return {"total": len(self.data),
                "path": str(self.path)}
