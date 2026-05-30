# FILE: experiments/browser_agent/ingest/youtube_transcript.py
"""YouTube 영상 자막 추출. youtube-transcript-api 사용.

사용:
    text = fetch_transcript("https://www.youtube.com/watch?v=aircAruvnKk")
    text = fetch_transcript("aircAruvnKk")  # ID만 줘도 OK

반환: 자막 합쳐진 str (시간 정보 제거). 자막 없으면 "" (빈 문자열).
"""
import re

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # pip install youtube-transcript-api
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def is_available() -> bool:
    return _AVAILABLE


_VID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/|/shorts/)([\w-]{11})")


def extract_video_id(url_or_id: str) -> str:
    """URL에서 video ID 11자 추출. 이미 ID면 그대로 반환."""
    if re.fullmatch(r"[\w-]{11}", url_or_id):
        return url_or_id
    m = _VID_RE.search(url_or_id)
    return m.group(1) if m else ""


def fetch_transcript(url_or_id: str, languages: tuple = ("ko", "en")) -> str:
    """자막을 한 문자열로 합쳐 반환. 자막 없거나 실패면 ''.
    languages: 우선순위 — 자동/번역 자막 fallback. 한국어 → 영어 순.
    """
    if not _AVAILABLE:
        raise RuntimeError("youtube-transcript-api 미설치 — `pip install youtube-transcript-api`")
    vid = extract_video_id(url_or_id)
    if not vid:
        return ""
    try:
        # API 변경 대응: get_transcript는 list 반환. 각 entry는 {'text','start','duration'}.
        entries = YouTubeTranscriptApi.get_transcript(vid, languages=list(languages))
    except Exception as e:
        print(f"[TRANSCRIPT-FAIL] {vid}: {e}")
        return ""
    return " ".join(e.get("text", "").strip() for e in entries if e.get("text"))


def fetch_with_meta(url_or_id: str, languages: tuple = ("ko", "en")) -> dict:
    """자막 + 메타. 반환: {video_id, transcript, char_len}."""
    vid = extract_video_id(url_or_id)
    transcript = fetch_transcript(vid, languages=languages) if vid else ""
    return {
        "video_id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}" if vid else url_or_id,
        "transcript": transcript,
        "char_len": len(transcript),
    }


if __name__ == "__main__":
    # smoke test
    if not _AVAILABLE:
        print("youtube-transcript-api 미설치 — pip install youtube-transcript-api")
    else:
        sample = fetch_with_meta("https://www.youtube.com/watch?v=aircAruvnKk")
        print(f"video_id: {sample['video_id']}, transcript {sample['char_len']} chars")
        print(sample["transcript"][:300])
