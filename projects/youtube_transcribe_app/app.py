# FILE: projects/youtube_transcribe_app/app.py
"""링크/제목 입력 → 다운로드 → Whisper 스크립트 표시 (Flask).

실행:
    cd projects/youtube_transcribe_app
    python app.py
    # 브라우저에서 http://127.0.0.1:5000 열기

환경 변수로 오버라이드 가능:
    WHISPER_MODEL=small WHISPER_DEVICE=cpu WHISPER_COMPUTE=int8 python app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from threading import Lock

from flask import Flask, render_template, request, jsonify

# experiments/youtube_whisper 모듈 재사용
# (검증 끝나면 core/youtube_whisper/ 로 승격하면 sys.path 트릭 제거 가능)
EXPERIMENTS_DIR = Path(__file__).resolve().parents[2] / "experiments" / "youtube_whisper"
if str(EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENTS_DIR))

from yt_download import download  # type: ignore  # noqa: E402
from transcribe import transcribe_one  # type: ignore  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

app = Flask(__name__)

_MODEL: WhisperModel | None = None
_MODEL_LOCK = Lock()
_MODEL_SIZE = os.getenv("WHISPER_MODEL", "large-v3")
_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
_COMPUTE = os.getenv("WHISPER_COMPUTE", "float16")


def _get_model() -> WhisperModel:
    """첫 요청에 1번만 모델 로드 (글로벌 캐시)."""
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            print(f"[init] 모델 로드: {_MODEL_SIZE} (device={_DEVICE}, compute_type={_COMPUTE})")
            _MODEL = WhisperModel(_MODEL_SIZE, device=_DEVICE, compute_type=_COMPUTE)
        return _MODEL


@app.route("/")
def index():
    return render_template("index.html", model_size=_MODEL_SIZE, device=_DEVICE)


@app.route("/transcribe", methods=["POST"])
def do_transcribe():
    data = request.get_json(silent=True) or request.form
    query = (data.get("query") or "").strip()
    language = (data.get("language") or "").strip() or None
    if not query:
        return jsonify({"error": "query 필요"}), 400

    try:
        # 전사용이라 mp3로만 받음 (용량/시간 절감)
        media = download(query, audio_only=True)
        model = _get_model()
        txt_path = transcribe_one(media, model, language)
        text = txt_path.read_text(encoding="utf-8")
        return jsonify({
            "media": media.name,
            "transcript": text,
            "txt_path": str(txt_path),
        })
    except Exception as e:
        return jsonify({"error": repr(e)}), 500


if __name__ == "__main__":
    # 모델 로딩이 길어 동시 요청은 1개만 처리하는 게 안전 (threaded=False)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=False)
