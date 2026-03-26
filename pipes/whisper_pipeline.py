#!/usr/bin/env python3
"""
T9 OS Whisper Pipeline v1.0
auto transcription pipeline.

Usage:
    python3 T9OS/pipes/whisper_pipeline.py transcribe "filepath"
    python3 T9OS/pipes/whisper_pipeline.py batch "folderpath"
    python3 T9OS/pipes/whisper_pipeline.py watch "folderpath"
    python3 T9OS/pipes/whisper_pipeline.py list
    python3 T9OS/pipes/whisper_pipeline.py stats

auto classify (filepattern):
    ML_20260316.m4a      →     AE4_20260316.m4a     → AE4
    SAD_20260316.m4a     → systemanalyze    GOV_20260316.m4a     → AI    SL_20260316.m4a      → service
date+auto (config ).
"""

import sys
import os
import re
import json
import time
import signal
import hashlib
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# ─── path config ──────────────────────────────────────────────────────────────

# __file__ path — hardcoded PC
T9 = Path(__file__).resolve().parent.parent      # T9OS/
HANBEEN = T9.parent                               # HANBEEN/
TRANSCRIPTS_DIR = T9 / "artifacts" / "transcripts"
RECORDINGS_DIR = HANBEEN / "PERSONAL" / "recordings"
DB_PATH = T9 / "pipes" / ".whisper_pipeline.db"
LOGS_DIR = HANBEEN / "_ai" / "logs" / "cc"
T9_SEED = T9 / "t9_seed.py"

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".wma", ".webm", ".mp4"}

# ─── mapping ────────────────────────────────────────

COURSE_MAP = {
    "ML":  "",
    "AE4": "AE4",
    "AE":  "AE4",
    "SAD": "systemanalyze",
    "GOV": "AI",
    "SL":  "service",
}

# (=0, =1, ... =4)
# -mapping add
SCHEDULE: dict[int, list[str]] = {
    # : 0: ["ML"],     # →
    # 1: ["AE4"],    # → AE4
}

# ─── Whisper config ────────────────────────────────────────────────────────────

DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "cuda"
DEFAULT_COMPUTE = "float16"
DEFAULT_LANGUAGE = "ko"
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_CHUNK_LENGTH = 30  # seconds


# ─── DB initialize ───────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """transcription DB initialize."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audio_path TEXT NOT NULL,
            audio_hash TEXT NOT NULL,
            transcript_path TEXT,
            course TEXT,
            duration_sec REAL,
            transcribe_sec REAL,
            model TEXT,
            language TEXT,
            word_count INTEGER,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'completed',
            error TEXT,
            UNIQUE(audio_hash)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_course ON transcriptions(course)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_created ON transcriptions(created_at)
    """)
    conn.commit()
    return conn


def file_hash(path: Path) -> str:
    """file SHA256 hash (1MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()[:16]


def is_already_transcribed(conn: sqlite3.Connection, audio_hash: str) -> bool:
    """transcriptionfilecheck."""
    row = conn.execute(
        "SELECT id FROM transcriptions WHERE audio_hash = ? AND status = 'completed'",
        (audio_hash,),
    ).fetchone()
    return row is not None


# ─── classify ────────────────────────────────────────

def detect_course(filepath: Path, recording_date: Optional[datetime] = None) -> str:
    """filepattern classify."""
    name = filepath.stem.upper()

    # 1) file: ML_20260316, AE4_0316
    for prefix, course in COURSE_MAP.items():
        if name.startswith(prefix + "_") or name.startswith(prefix + "-"):
            return course

    # 2) file
    name_lower = filepath.stem.lower()
    for keyword, course in [
        ("", ""), ("machine", ""),
        ("systemanalyze", "systemanalyze"), ("sad", "systemanalyze"),
        ("", "AI"), ("gov", "AI"),
        ("service", "service"), ("service", "service"),
        ("ae4", "AE4"), ("ae", "AE4"),
    ]:
        if keyword in name_lower:
            return course

    #
    if recording_date and recording_date.weekday() in SCHEDULE:
        courses = SCHEDULE[recording_date.weekday()]
        if len(courses) == 1:
            return courses[0]

    return "classify"


def extract_date_from_filename(filepath: Path) -> Optional[datetime]:
    """filedate extract. : ML_20260316, 20260316_ML"""
    patterns = [
        r"(\d{8})",         # 20260316
        r"(\d{4}-\d{2}-\d{2})",  # 2026-03-16
    ]
    for pat in patterns:
        m = re.search(pat, filepath.stem)
        if m:
            try:
                ds = m.group(1).replace("-", "")
                return datetime.strptime(ds, "%Y%m%d")
            except ValueError:
                continue
    # file modify fallback
    try:
        mtime = filepath.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    except OSError:
        return None


# ─── transcription engine ───────────────────────────────────────────────────────────────

def transcribe_audio(
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    """
    faster-whispertranscription.
    return: {text, segments, duration, language, info}
    """
    from faster_whisper import WhisperModel

    print(f"\n{'='*60}")
    print(f"  Whisper transcription start")
    print(f"  file: {audio_path.name}")
    print(f"  model: {model_name} | : {device}")
    print(f"{'='*60}")

    t0 = time.time()

    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
    except Exception as e:
        if device == "cuda":
            print(f"  [WARN] GPU failed, CPU retry: {e}")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            device = "cpu"
        else:
            raise

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=DEFAULT_BEAM_SIZE,
        vad_filter=DEFAULT_VAD_FILTER,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
    )

    duration = info.duration
    print(f"  : {duration/60:.1f}")
    print(f"  : {info.language} ({info.language_probability:.2f})")
    print()

    #
    segments = []
    full_text_parts = []
    last_pct = -1

    for seg in segments_iter:
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
        full_text_parts.append(seg.text.strip())

        # (5% )
        if duration > 0:
            pct = int(seg.end / duration * 100)
            if pct >= last_pct + 5:
                last_pct = pct
                elapsed = time.time() - t0
                eta = (elapsed / max(seg.end, 1)) * (duration - seg.end)
                bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                print(
                    f"  [{bar}] {pct:3d}%  "
                    f"{seg.end/60:.0f}/{duration/60:.0f}  "
                    f"ETA {eta/60:.1f}",
                    end="\r",
                )

    print()

    elapsed = time.time() - t0
    full_text = "\n".join(full_text_parts)

    print(f"\n  transcription completed: {elapsed:.1f}({duration/max(elapsed,0.1):.1f}x)")
    print(f"  : {len(segments)}| : {len(full_text)}")

    return {
        "text": full_text,
        "segments": segments,
        "duration": duration,
        "elapsed": elapsed,
        "language": info.language,
        "language_prob": info.language_probability,
        "device": device,
        "model": model_name,
    }


# ─── output save ───────────────────────────────────────────────────────────────

def save_transcript(
    audio_path: Path,
    result: dict,
    course: str,
    recording_date: Optional[datetime] = None,
) -> Path:
    """transcription resultMD filesave."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = (recording_date or datetime.now()).strftime("%Y%m%d")
    safe_name = re.sub(r"[^\w--]", "_", audio_path.stem)
    out_name = f"{date_str}_{course}_{safe_name}.md"
    out_path = TRANSCRIPTS_DIR / out_name

    # duplicate
    if out_path.exists():
        out_name = f"{date_str}_{course}_{safe_name}_{int(time.time()) % 10000}.md"
        out_path = TRANSCRIPTS_DIR / out_name

    duration_min = result["duration"] / 60
    word_count = len(result["text"])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"---",
        f"title: \"{course}  transcription ({date_str})\"",
        f"course: {course}",
        f"date: {date_str}",
        f"source: {audio_path.name}",
        f"duration: {duration_min:.1f}",
        f"model: {result.get('model', DEFAULT_MODEL)}",
        f"language: {result['language']}",
        f"transcribed_at: {now_str}",
        f"word_count: {word_count}",
        f"---",
        f"",
        f"# {course} transcription ({date_str})",
        f"",
        f"- original: `{audio_path.name}`",
        f"- : {duration_min:.1f}",
        f"- transcription : {result['elapsed']:.1f}",
        f"-  : {word_count}",
        f"",
        f"---",
        f"",
        f"## transcription content",
        f"",
    ]

    # transcription
    for seg in result["segments"]:
        ts_start = _format_ts(seg["start"])
        ts_end = _format_ts(seg["end"])
        text = seg["text"]
        if text:
            lines.append(f"**[{ts_start} ~ {ts_end}]** {text}")
            lines.append("")

    # total (search)
    lines.extend([
        "",
        "---",
        "",
        "## total (search)",
        "",
        result["text"],
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  save: {out_path}")
    return out_path


def _format_ts(seconds: float) -> str:
    """HH:MM:SS formatconvert."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ─── T9 Seed ────────────────────────────────────────

def register_entity(course: str, date_str: str, transcript_path: Path, duration_min: float):
    """t9_seed.py captureregister."""
    if not T9_SEED.exists():
        print("  [WARN] t9_seed.py not found, register items")
        return

    text = f"{course}  transcription completed ({date_str}, {duration_min:.0f}) → {transcript_path.name}"
    try:
        subprocess.run(
            [sys.executable, str(T9_SEED), "capture", text],
            capture_output=True, text=True, timeout=10,
        )
        print(f"  T9 Seed register completed")
    except Exception as e:
        print(f"  [WARN] T9 Seed register failed: {e}")


# ─── DB record ─────────────────────────────────────────────────────────────────

def record_transcription(
    conn: sqlite3.Connection,
    audio_path: Path,
    audio_hash_val: str,
    transcript_path: Path,
    course: str,
    result: dict,
):
    """transcription resultDBrecord."""
    conn.execute(
        """
        INSERT OR REPLACE INTO transcriptions
        (audio_path, audio_hash, transcript_path, course,
         duration_sec, transcribe_sec, model, language,
         word_count, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(audio_path),
            audio_hash_val,
            str(transcript_path),
            course,
            result["duration"],
            result["elapsed"],
            DEFAULT_MODEL,
            result["language"],
            len(result["text"]),
            datetime.now().isoformat(),
            "completed",
        ),
    )
    conn.commit()


# ─── command ────────────────────────────────────────

def cmd_transcribe(audio_path_str: str, force: bool = False):
    """file transcription."""
    audio_path = Path(audio_path_str).resolve()

    if not audio_path.exists():
        print(f"[ERROR] file not found: {audio_path}")
        sys.exit(1)

    if audio_path.suffix.lower() not in AUDIO_EXTS:
        print(f"[ERROR] unsupported format: {audio_path.suffix}")
        print(f"  format: {', '.join(sorted(AUDIO_EXTS))}")
        sys.exit(1)

    conn = init_db()
    try:
        h = file_hash(audio_path)

        if not force and is_already_transcribed(conn, h):
            print(f"[SKIP] transcription: {audio_path.name}")
            row = conn.execute(
                "SELECT transcript_path FROM transcriptions WHERE audio_hash = ?", (h,)
            ).fetchone()
            if row:
                print(f"  result: {row[0]}")
            return

        recording_date = extract_date_from_filename(audio_path)
        course = detect_course(audio_path, recording_date)
        date_str = (recording_date or datetime.now()).strftime("%Y%m%d")

        print(f"  : {course}")
        print(f"  date: {date_str}")

        result = transcribe_audio(audio_path)

        transcript_path = save_transcript(audio_path, result, course, recording_date)

        record_transcription(conn, audio_path, h, transcript_path, course, result)

        register_entity(course, date_str, transcript_path, result["duration"] / 60)

    except Exception as e:
        print(f"\n[ERROR] transcription error: {e}")
        raise
    finally:
        conn.close()

    print(f"\n{'='*60}")
    print(f"  transcription completed!")
    print(f"  result: {transcript_path}")
    print(f"{'='*60}\n")

    return transcript_path


def cmd_batch(folder_str: str, force: bool = False):
    """folder total file transcription."""
    folder = Path(folder_str).resolve()
    if not folder.is_dir():
        print(f"[ERROR] folder not found: {folder}")
        sys.exit(1)

    audio_files = sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    )

    if not audio_files:
        print(f"[INFO] file not found: {folder}")
        return

    print(f"\ntranscription target: {len(audio_files)}file")
    for i, f in enumerate(audio_files, 1):
        print(f"  {i}. {f.name}")
    print()

    conn = init_db()
    success, skip, fail = 0, 0, 0

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] {audio_file.name}")

        h = file_hash(audio_file)
        if not force and is_already_transcribed(conn, h):
            print(f"  [SKIP] transcription")
            skip += 1
            continue

        try:
            recording_date = extract_date_from_filename(audio_file)
            course = detect_course(audio_file, recording_date)
            date_str = (recording_date or datetime.now()).strftime("%Y%m%d")

            result = transcribe_audio(audio_file)
            transcript_path = save_transcript(audio_file, result, course, recording_date)
            record_transcription(conn, audio_file, h, transcript_path, course, result)
            register_entity(course, date_str, transcript_path, result["duration"] / 60)

            success += 1
        except Exception as e:
            print(f"  [ERROR] transcription failed: {e}")
            conn.execute(
                """
                INSERT OR REPLACE INTO transcriptions
                (audio_path, audio_hash, course, created_at, status, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(audio_file), h, "classify", datetime.now().isoformat(), "failed", str(e)),
            )
            conn.commit()
            fail += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"  transcription completed")
    print(f"  success: {success} | items: {skip} | failed: {fail}")
    print(f"{'='*60}\n")


def cmd_watch(folder_str: str = ""):
    """folder monitoring . fileaddauto transcription."""
    folder = Path(folder_str).resolve() if folder_str else RECORDINGS_DIR
    folder.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Whisper monitoring start")
    print(f"  monitoring folder: {folder}")
    print(f"  Ctrl+Cend")
    print(f"{'='*60}\n")

    conn = init_db()
    seen: set[str] = set()

    # existing file hash (fileitems)
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            seen.add(file_hash(f))

    running = True

    def _stop(signum, frame):
        nonlocal running
        running = False
        print("\n\n  monitoring end ...")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    poll_interval = 5  # seconds

    while running:
        try:
            for f in folder.iterdir():
                if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
                    continue

                h = file_hash(f)
                if h in seen:
                    continue

                # file completed (size Stabilized)
                size1 = f.stat().st_size
                time.sleep(2)
                if not f.exists():
                    continue
                size2 = f.stat().st_size
                if size1 != size2:
                    continue

                seen.add(h)

                if is_already_transcribed(conn, h):
                    continue

                print(f"\n  [NEW] new file : {f.name}")
                try:
                    recording_date = extract_date_from_filename(f)
                    course = detect_course(f, recording_date)
                    date_str = (recording_date or datetime.now()).strftime("%Y%m%d")

                    result = transcribe_audio(f)
                    transcript_path = save_transcript(f, result, course, recording_date)
                    record_transcription(conn, f, h, transcript_path, course, result)
                    register_entity(course, date_str, transcript_path, result["duration"] / 60)
                    print(f"  [DONE] {transcript_path.name}")
                except Exception as e:
                    print(f"  [ERROR] {f.name}: {e}")

            time.sleep(poll_interval)
        except Exception as e:
            if running:
                print(f"  [ERROR] monitoring error: {e}")
                time.sleep(poll_interval)

    conn.close()
    print("  monitoring end.")


def cmd_list():
    """transcription query."""
    conn = init_db()
    rows = conn.execute(
        """
        SELECT course, audio_path, duration_sec, word_count, created_at, status, transcript_path
        FROM transcriptions
        ORDER BY created_at DESC
        LIMIT 30
        """
    ).fetchall()

    if not rows:
        print("transcription not found.")
        conn.close()
        return

    print(f"\n{'':<12} {'file':<30} {'':>6} {'':>7} {'state':<8} {'date':<12}")
    print("-" * 85)

    for course, audio_path, dur, wc, created, status, tp in rows:
        fname = Path(audio_path).name[:28] if audio_path else "?"
        dur_str = f"{dur/60:.0f}" if dur else "?"
        wc_str = f"{wc:,}" if wc else "?"
        date_str = created[:10] if created else "?"
        print(f"{course or '?':<12} {fname:<30} {dur_str:>6} {wc_str:>7} {status:<8} {date_str:<12}")

    conn.close()


def cmd_stats():
    """transcription statistics."""
    conn = init_db()

    total = conn.execute("SELECT COUNT(*) FROM transcriptions WHERE status='completed'").fetchone()[0]
    total_dur = conn.execute("SELECT COALESCE(SUM(duration_sec),0) FROM transcriptions WHERE status='completed'").fetchone()[0]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count),0) FROM transcriptions WHERE status='completed'").fetchone()[0]

    print(f"\n{'='*40}")
    print(f"  Whisper Pipeline statistics")
    print(f"{'='*40}")
    print(f"  transcription completed: {total}file")
    print(f"  : {total_dur/3600:.1f}")
    print(f"  : {total_words:,}")
    print()

    # statistics
    rows = conn.execute(
        """
        SELECT course, COUNT(*), SUM(duration_sec), SUM(word_count)
        FROM transcriptions
        WHERE status='completed'
        GROUP BY course
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()

    if rows:
        print(f"  {'':<16} {'':>4} {'':>8} {'':>10}")
        print(f"  {'-'*42}")
        for course, cnt, dur, wc in rows:
            print(f"  {course:<16} {cnt:>4} {dur/60:.0f}{' ':>3} {int(wc or 0):>10,}")

    print(f"{'='*40}\n")
    conn.close()


# ──────────────────────────────────────────────────

USAGE = """
T9 OS Whisper Pipeline v1.0

Usage:
  whisper_pipeline.py transcribe <filepath> [--force]
  whisper_pipeline.py batch <folderpath> [--force]
  whisper_pipeline.py watch [folderpath]
  whisper_pipeline.py list
  whisper_pipeline.py stats

(file):
  ML   →   AE4  → AE4
  SAD  → systemanalyze  GOV  → AI  SL   → service
:
  python3 T9OS/pipes/whisper_pipeline.py transcribe "ML_20260316.m4a"
  python3 T9OS/pipes/whisper_pipeline.py batch ~/HANBEEN/PERSONAL/recordings/
  python3 T9OS/pipes/whisper_pipeline.py watch
""".strip()


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    cmd = sys.argv[1].lower()
    force = "--force" in sys.argv

    if cmd == "transcribe":
        if len(sys.argv) < 3:
            print("[ERROR] file path ")
            print("  use: whisper_pipeline.py transcribe <filepath>")
            sys.exit(1)
        cmd_transcribe(sys.argv[2], force=force)

    elif cmd == "batch":
        if len(sys.argv) < 3:
            print("[ERROR] folder path ")
            print("  use: whisper_pipeline.py batch <folderpath>")
            sys.exit(1)
        cmd_batch(sys.argv[2], force=force)

    elif cmd == "watch":
        folder = sys.argv[2] if len(sys.argv) > 2 else ""
        cmd_watch(folder)

    elif cmd == "list":
        cmd_list()

    elif cmd == "stats":
        cmd_stats()

    else:
        print(f"[ERROR] unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
