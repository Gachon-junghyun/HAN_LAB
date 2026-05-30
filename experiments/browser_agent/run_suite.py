# FILE: experiments/browser_agent/run_suite.py
"""시나리오 묶음을 일괄 실행하고 결과를 markdown 표로 정리한다.
사용: python run_suite.py --suite twitter
      python run_suite.py --suite sns_mixed --timeout 240

main.py와의 계약은 두 가지:
  1) main.py의 SUMMARY_COLUMNS / SUMMARY_FILE_GLOB 상수를 import해서 헤더/경로 검증.
     컬럼 추가/이름 변경 시 import 또는 헤더 검증에서 즉시 실패해 조용한 결과 깨짐 방지.
  2) main.py의 CLI 인자(--llm/--mode/--url/--max-visits/positional goal)를 사용.
     이 인자가 변하면 build_main_command 한 군데만 수정.
"""
import argparse
import csv
import importlib
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # main.py / scenarios.* import용
from main import SUMMARY_COLUMNS, SUMMARY_FILE_GLOB, STEPS_FILE_GLOB  # noqa: E402
_ = STEPS_FILE_GLOB  # 계약 가시화. 사후 검증 도구가 같은 패턴 쓰도록 main.py가 source.

LOG_DIR = HERE / "logs"
RESULTS_DIR = HERE / "scenarios"


def build_main_command(mode, mv, url, goal):
    """main.py 인자 조립 single source of truth. 인자 변경 시 여기만 수정."""
    cmd = [sys.executable, str(HERE / "main.py"), "--llm", "ollama",
           "--mode", mode, "--url", url]
    if mode == "research":
        cmd += ["--max-visits", str(mv)]
    cmd.append(goal)
    return cmd


def run_one(sid, mode, mv, url, goal, timeout):
    cmd = build_main_command(mode, mv, url, goal)
    start = time.time()
    try:
        proc = subprocess.run(cmd, timeout=timeout,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL,
                              cwd=str(HERE))
        rc, timed_out = proc.returncode, False
    except subprocess.TimeoutExpired:
        rc, timed_out = -1, True
    elapsed = time.time() - start

    cands = sorted(LOG_DIR.glob(SUMMARY_FILE_GLOB),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    summary, rows = (cands[0] if cands else None), []
    if summary:
        with open(summary, encoding="utf-8") as f:
            rdr = csv.reader(f, delimiter="\t")
            header = next(rdr, None)
            if tuple(header or ()) != SUMMARY_COLUMNS:
                raise RuntimeError(
                    f"summary header mismatch: got {header}, expected {SUMMARY_COLUMNS}. "
                    f"main.py 변경됐으면 SUMMARY_COLUMNS와 write_summary_header 동기화 확인."
                )
            rows = list(rdr)
    return dict(id=sid, elapsed=elapsed, timed_out=timed_out, rc=rc,
                summary_file=summary.name if summary else None, rows=rows)


def classify(info):
    if info["timed_out"]:
        return "TIMEOUT"
    if info["rc"] != 0:
        return "CRASH"
    if not info["rows"]:
        return "NO_STEPS"
    last = info["rows"][-1]
    if len(last) < 4:
        return "MALFORMED"
    if "DONE" in last[3]:
        return "DONE"
    if "FAIL" in last[3]:
        return "FAIL"
    return "MAX_STEPS"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True,
                        help="scenarios/<NAME>.py — 예: twitter, sns_mixed")
    parser.add_argument("--timeout", type=int, default=240,
                        help="시나리오당 최대 초 (기본 240)")
    args = parser.parse_args()

    mod = importlib.import_module(f"scenarios.{args.suite}")
    scenarios = mod.SCENARIOS
    results_file = RESULTS_DIR / f"{args.suite}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    print(f"=== Suite '{args.suite}' ({len(scenarios)} runs, timeout={args.timeout}s) -> {results_file} ===\n")
    results = []
    for sc in scenarios:
        sid, mode, mv, url, goal = sc
        print(f"[#{sid}] ({mode}) {goal[:70]}")
        info = run_one(sid, mode, mv, url, goal, args.timeout)
        info["class"] = classify(info)
        info["scenario"] = sc
        print(f"   -> {info['class']} ({len(info['rows'])} steps, {info['elapsed']:.0f}s, summary={info['summary_file']})")
        results.append(info)

    lines = [f"# Suite '{args.suite}' — {datetime.now().isoformat(timespec='seconds')}\n",
             "| # | mode | class | steps | sec | last_action | last_result |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        sid, mode, *_ = r["scenario"]
        last = r["rows"][-1] if r["rows"] else ["", "", "", ""]
        la = (last[2] if len(last) > 2 else "")[:60].replace("|", "/").replace("\n", " ")
        lr = (last[3] if len(last) > 3 else "")[:80].replace("|", "/").replace("\n", " ")
        lines.append(f"| {sid} | {mode} | {r['class']} | {len(r['rows'])} | "
                     f"{r['elapsed']:.0f} | {la} | {lr} |")
    lines += ["", "## Detail", ""]
    for r in results:
        sid, mode, mv, url, goal = r["scenario"]
        lines.append(f"### #{sid} ({mode}) — {goal}")
        lines.append(f"- url: {url}")
        lines.append(f"- summary: `{r['summary_file']}`")
        lines.append(f"- class: **{r['class']}**, steps: {len(r['rows'])}, elapsed: {r['elapsed']:.0f}s\n")
    results_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n=== Done. Results: {results_file}")


if __name__ == "__main__":
    main()
