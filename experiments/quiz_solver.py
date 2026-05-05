# FILE: experiments/quiz_solver.py
# 퀴즈 JSON을 읽어 문제마다 독립 chat 세션으로 풀이하고 md로 저장한다.
# 각 문제는 fresh messages 리스트를 쓰므로 이전 문제의 컨텍스트가 새지 않는다.

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# HAN_LAB 루트를 sys.path에 추가 (core import용)
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.ai import OllamaClient

# ----- 설정 -----
MODEL_NAME = "gemma4:e4b"   # 사용자가 지정한 모델. 로컬에 없으면 변경.
TEST_FILE = Path(__file__).parent / "quiz_data.json"
OUT_FILE = Path(__file__).parent / "quiz_solve.md"

SYSTEM_PROMPT = (
    "너는 논리적이고 차분한 한국어 튜터다. "
    "문제를 받으면 (1) 무엇을 묻는지 한 줄로 정리하고 "
    "(2) 풀이 과정을 단계별로 보이고 "
    "(3) 마지막에 '결론:' 한 줄로 답을 못박아라. "
    "모르는 사실은 추측하지 말고 모른다고 명시해라."
)


def solve_one(client: OllamaClient, problem: dict) -> str:
    """문제 1개를 새 chat 세션에서 풀고 응답 텍스트를 반환."""
    # 매 호출마다 새 messages 리스트 → 독립 대화 보장
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": problem["question"]},
    ]
    print(f"\n[#{problem['id']:>2}] [{problem['genre']}] {problem['title']}")
    print("-" * 60)
    chunks = []
    for chunk in client.chat(messages, stream=True):
        print(chunk, end="", flush=True)
        chunks.append(chunk)
    print()
    return "".join(chunks).strip()


def main():
    # 1) 시험지 로드
    with open(TEST_FILE, encoding="utf-8") as f:
        data = json.load(f)
    problems = data["problems"]
    meta = data.get("meta", {})
    print(f"=== {meta.get('title', '퀴즈')} (총 {len(problems)}문제) ===")
    print(f"모델: {MODEL_NAME}\n")

    # 2) 클라이언트 1개로 충분 (대화 격리는 messages로 보장)
    client = OllamaClient(model_name=MODEL_NAME)

    # 3) 결과 md 헤더
    out_lines = [
        f"# {meta.get('title', '퀴즈 풀이')}",
        "",
        f"- 모델: `{MODEL_NAME}`",
        f"- 시각: {datetime.now().isoformat(timespec='seconds')}",
        f"- 문항 수: {len(problems)}",
        "",
        "각 문제는 **독립된 chat 세션**에서 풀이되었다.",
        "",
        "---",
        "",
    ]

    # 4) 문제별로 독립 풀이
    t_start = time.time()
    for p in problems:
        t0 = time.time()
        try:
            answer = solve_one(client, p)
        except Exception as e:
            answer = f"_[오류 발생: {e}]_"
            print(f"\n[ERROR] #{p['id']}: {e}")
        elapsed = time.time() - t0

        out_lines += [
            f"## {p['id']}. [{p['genre']}] {p['title']}",
            "",
            "**문제**",
            "",
            p["question"],
            "",
            f"**풀이** _(소요 {elapsed:.1f}s)_",
            "",
            answer,
            "",
            "---",
            "",
        ]

    out_lines.append(f"_총 소요 시간: {time.time() - t_start:.1f}s_")

    # 5) 저장
    OUT_FILE.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\n[저장 완료] {OUT_FILE}")


if __name__ == "__main__":
    main()
