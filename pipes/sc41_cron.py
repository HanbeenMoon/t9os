"""SC41 Canvas cron wrapper.

Runs sc41_main.py and, on new downloads, triggers t9_seed.py reindex
so that new assignments/files are reflected in the T9 OS entity DB.

Usage (cron):
    0 8,20 * * * /mnt/c/Users/winn/HANBEEN/T9OS/pipes/sc41_cron_runner.sh
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HANBEEN = Path(__file__).resolve().parents[2]  # ~/code/HANBEEN
SC41_DIR = HANBEEN / "_ai" / "sc41"
SC41_MAIN = SC41_DIR / "sc41_main.py"
T9_SEED = HANBEEN / "T9OS" / "t9_seed.py"
DOWNLOAD_RECORD = SC41_DIR / ".downloaded_files.json"
LOG_DIR = HANBEEN / "_ai" / "logs" / "cc"


def _load_download_record() -> dict:
    if not DOWNLOAD_RECORD.exists():
        return {}
    try:
        return json.loads(DOWNLOAD_RECORD.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _next_log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    existing = sorted(LOG_DIR.glob(f"{date_part}_CC_*_sc41_cron_*"))
    seq = len(existing) + 1
    return LOG_DIR / f"{date_part}_CC_{seq:03d}_sc41_cron_{time_part}_결과.txt"


def main() -> int:
    now = datetime.now()
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        log_lines.append(line)
        print(line)

    log(f"SC41 cron start: {now:%Y-%m-%d %H:%M:%S}")

    # Snapshot download record before run
    before = _load_download_record()
    before_count = sum(len(v) if isinstance(v, list) else 1 for v in before.values())

    # Run sc41_main.py --all
    log(f"Running: python3 {SC41_MAIN} --all")
    result = subprocess.run(
        [sys.executable, str(SC41_MAIN), "--all"],
        capture_output=True,
        text=True,
        cwd=str(SC41_DIR),
        timeout=300,
    )

    log(f"sc41_main exit code: {result.returncode}")
    if result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            log(f"  [stdout] {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().split("\n"):
            log(f"  [stderr] {line}")

    # Check if new files were downloaded
    after = _load_download_record()
    after_count = sum(len(v) if isinstance(v, list) else 1 for v in after.values())
    new_count = after_count - before_count

    if new_count > 0:
        log(f"New downloads detected: {new_count} files. Running reindex...")
        reindex_result = subprocess.run(
            [sys.executable, str(T9_SEED), "reindex"],
            capture_output=True,
            text=True,
            cwd=str(HANBEEN),
            timeout=120,
        )
        log(f"reindex exit code: {reindex_result.returncode}")
        if reindex_result.stdout.strip():
            log(f"  [reindex] {reindex_result.stdout.strip()[:200]}")
    else:
        log("No new downloads. Skipping reindex.")

    # Save log
    log_path = _next_log_path()
    log(f"Log saved: {log_path}")
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
