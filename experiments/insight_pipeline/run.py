# FILE: experiments/insight_pipeline/run.py
"""단계별 오케스트레이션.

사용법:
    python run.py chunks    # 1단계: transcripts/*.srt → data/chunks.jsonl
    python run.py extract   # 2단계: chunks → propositions.jsonl (resume 가능)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from dataclasses import asdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from channel_map import build_channel_map
from clean import srt_to_clean
from chunk import chunk_video, video_id_from_path

BASE = Path(__file__).parent
YT_DIR = BASE.parent / "youtube_whisper"
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

CHUNKS_PATH = DATA_DIR / "chunks.jsonl"
PROPS_PATH = DATA_DIR / "propositions.jsonl"
STATUS_PATH = DATA_DIR / "extract_status.jsonl"


# -------- 1단계 ----------------------------------------------------------
def step_chunks() -> None:
    channel_map = build_channel_map(YT_DIR / "list.txt")
    srt_files = sorted((YT_DIR / "transcripts").glob("*.srt"))
    total_chunks = 0
    total_sentences = 0
    chunks_by_channel: Counter[str] = Counter()
    hallu_count = 0
    skipped: list[str] = []

    with CHUNKS_PATH.open("w", encoding="utf-8") as fout:
        for srt in srt_files:
            vid = video_id_from_path(srt)
            if not vid:
                skipped.append(f"{srt.name}: video_id 추출 실패")
                continue
            channel = channel_map.get(vid)
            if not channel:
                skipped.append(f"{srt.name}: channel_map 매칭 실패 ({vid})")
                continue
            segs, susp = srt_to_clean(srt)
            chunks = chunk_video(vid, channel, segs, susp)
            for c in chunks:
                fout.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
                total_chunks += 1
                total_sentences += len(c.sentences)
                chunks_by_channel[channel] += 1
                if c.hallucination_suspected:
                    hallu_count += 1

    print(f"[OK] chunks → {CHUNKS_PATH}")
    print(f"  영상 {len(srt_files)}편 → 청크 {total_chunks} / 문장 {total_sentences}")
    print(f"  환각 의심 청크: {hallu_count}")
    for ch, n in chunks_by_channel.most_common():
        print(f"    - {ch}: {n}")
    for s in skipped:
        print(f"    [SKIP] {s}")


# -------- 2단계 ----------------------------------------------------------
def _load_done_chunk_ids() -> set[str]:
    """status.jsonl에서 이미 완료한 chunk_id 모음 (resume용)."""
    done: set[str] = set()
    if not STATUS_PATH.exists():
        return done
    with STATUS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("chunk_id"):
                    done.add(r["chunk_id"])
            except json.JSONDecodeError:
                continue
    return done


def _prevent_windows_sleep() -> None:
    """스크립트 도는 동안만 OS sleep 차단. 종료 시 자동 해제."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
        print("[init] OS sleep 차단 (이 프로세스 도는 동안만)")
    except Exception as e:
        print(f"[warn] sleep 차단 실패: {e}")


def step_extract() -> None:
    """청크 → LLM 추출 → propositions.jsonl (append). status.jsonl로 resume."""
    _prevent_windows_sleep()
    from extract import extract_chunk

    if not CHUNKS_PATH.exists():
        sys.exit(f"[ERR] {CHUNKS_PATH} 없음. python run.py chunks 먼저 실행.")

    done = _load_done_chunk_ids()
    print(f"[init] 이미 처리된 청크: {len(done)}개 (skip)")

    # 청크 전체 로드 (메모리 OK — 약 6 MB)
    all_chunks: list[dict] = []
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            all_chunks.append(json.loads(line))

    pending = [c for c in all_chunks if c["chunk_id"] not in done]
    total = len(all_chunks)
    print(f"[init] 전체 {total}개 / 처리 대상 {len(pending)}개")

    # append 모드로 열고 매 청크마다 flush
    props_f = PROPS_PATH.open("a", encoding="utf-8")
    status_f = STATUS_PATH.open("a", encoding="utf-8")

    start_t = time.time()
    n_done = 0
    n_props_total = 0
    n_rejected_total = 0
    n_failed = 0

    try:
        for i, chunk in enumerate(pending, 1):
            t0 = time.time()
            err: str | None = None
            n_props = 0
            n_rejected = 0
            try:
                props, rejected = extract_chunk(chunk)
                n_props = len(props)
                n_rejected = rejected
                for p in props:
                    props_f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
                props_f.flush()
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                n_failed += 1
                traceback.print_exc(file=sys.stderr)

            dt = time.time() - t0
            status = {
                "chunk_id": chunk["chunk_id"],
                "channel": chunk["channel"],
                "n_props": n_props,
                "n_rejected": n_rejected,
                "elapsed_s": round(dt, 2),
                "error": err,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            status_f.write(json.dumps(status, ensure_ascii=False) + "\n")
            status_f.flush()

            n_done += 1
            n_props_total += n_props
            n_rejected_total += n_rejected

            elapsed = time.time() - start_t
            rate = n_done / elapsed if elapsed > 0 else 0
            eta_s = (len(pending) - n_done) / rate if rate > 0 else 0
            done_total = len(done) + n_done
            print(
                f"  [{done_total}/{total}] {chunk['chunk_id']} "
                f"({chunk['channel'][:8]}) "
                f"props={n_props} rej={n_rejected} "
                f"{dt:.1f}s | ETA {eta_s/3600:.1f}h",
                flush=True,
            )
    finally:
        props_f.close()
        status_f.close()

    print(f"\n[DONE] 청크 {n_done}/{len(pending)} 처리")
    print(f"  명제 총 {n_props_total} / reject {n_rejected_total} / 실패 청크 {n_failed}")
    print(f"  → {PROPS_PATH}")


# -------- entrypoint -----------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["chunks", "extract"])
    args = p.parse_args()
    if args.step == "chunks":
        step_chunks()
    elif args.step == "extract":
        step_extract()


if __name__ == "__main__":
    main()
