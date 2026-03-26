#!/usr/bin/env python3
"""
T9 OS Whisper Pipeline v1.0
수업 녹음 자동 전사 파이프라인.

Usage:
    python3 T9OS/pipes/whisper_pipeline.py transcribe "파일경로"
    python3 T9OS/pipes/whisper_pipeline.py batch "폴더경로"
    python3 T9OS/pipes/whisper_pipeline.py watch "폴더경로"
    python3 T9OS/pipes/whisper_pipeline.py list
    python3 T9OS/pipes/whisper_pipeline.py stats

과목 자동 분류 (파일명 패턴):
    ML_20260316.m4a      → 머신러닝
    AE4_20260316.m4a     → AE4
    SAD_20260316.m4a     → 시스템분석및설계
    GOV_20260316.m4a     → AI와데이터거버넌스
    SL_20260316.m4a      → 서비스러닝

또는 날짜+요일 기반 자동 매칭 (시간표 설정 시).
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

# ─── 경로 설정 ──────────────────────────────────────────────────────────────

# __file__ 기반 상대 경로 — 하드코딩 없이 어느 PC에서도 동작
T9 = Path(__file__).resolve().parent.parent      # T9OS/
HANBEEN = T9.parent                               # HANBEEN/
TRANSCRIPTS_DIR = T9 / "artifacts" / "transcripts"
RECORDINGS_DIR = HANBEEN / "PERSONAL" / "recordings"
DB_PATH = T9 / "pipes" / ".whisper_pipeline.db"
LOGS_DIR = HANBEEN / "_ai" / "logs" / "cc"
T9_SEED = T9 / "t9_seed.py"

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac", ".wma", ".webm", ".mp4"}

# ─── 과목 매핑 ──────────────────────────────────────────────────────────────

COURSE_MAP = {
    "ML":  "머신러닝",
    "AE4": "AE4",
    "AE":  "AE4",
    "SAD": "시스템분석및설계",
    "GOV": "AI와데이터거버넌스",
    "SL":  "서비스러닝",
}

# 요일 기반 시간표 (월=0, 화=1, ... 금=4)
# 필요 시 여기에 요일-시간 매핑 추가
SCHEDULE: dict[int, list[str]] = {
    # 예: 0: ["ML"],     # 월요일 → 머신러닝
    #     1: ["AE4"],    # 화요일 → AE4
}

# ─── Whisper 설정 ────────────────────────────────────────────────────────────

DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "cuda"
DEFAULT_COMPUTE = "float16"
DEFAULT_LANGUAGE = "ko"
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_CHUNK_LENGTH = 30  # seconds


# ─── DB 초기화 ───────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """전사 이력 DB 초기화."""
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
    """파일 SHA256 해시 (처음 1MB만)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()[:16]


def is_already_transcribed(conn: sqlite3.Connection, audio_hash: str) -> bool:
    """이미 전사된 파일인지 확인."""
    row = conn.execute(
        "SELECT id FROM transcriptions WHERE audio_hash = ? AND status = 'completed'",
        (audio_hash,),
    ).fetchone()
    return row is not None


# ─── 과목 분류 ───────────────────────────────────────────────────────────────

def detect_course(filepath: Path, recording_date: Optional[datetime] = None) -> str:
    """파일명 패턴 또는 요일 기반 과목 분류."""
    name = filepath.stem.upper()

    # 1) 파일명 접두사 매칭: ML_20260316, AE4_0316 등
    for prefix, course in COURSE_MAP.items():
        if name.startswith(prefix + "_") or name.startswith(prefix + "-"):
            return course

    # 2) 파일명에 과목명 포함
    name_lower = filepath.stem.lower()
    for keyword, course in [
        ("머신러닝", "머신러닝"), ("machine", "머신러닝"),
        ("시스템분석", "시스템분석및설계"), ("sad", "시스템분석및설계"),
        ("거버넌스", "AI와데이터거버넌스"), ("gov", "AI와데이터거버넌스"),
        ("서비스러닝", "서비스러닝"), ("service", "서비스러닝"),
        ("ae4", "AE4"), ("ae", "AE4"),
    ]:
        if keyword in name_lower:
            return course

    # 3) 요일 기반 시간표
    if recording_date and recording_date.weekday() in SCHEDULE:
        courses = SCHEDULE[recording_date.weekday()]
        if len(courses) == 1:
            return courses[0]

    return "미분류"


def extract_date_from_filename(filepath: Path) -> Optional[datetime]:
    """파일명에서 날짜 추출. 예: ML_20260316, 20260316_ML"""
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
    # 파일 수정 시간 fallback
    try:
        mtime = filepath.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    except OSError:
        return None


# ─── 전사 엔진 ───────────────────────────────────────────────────────────────

def transcribe_audio(
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    """
    faster-whisper로 오디오 전사.
    반환: {text, segments, duration, language, info}
    """
    from faster_whisper import WhisperModel

    print(f"\n{'='*60}")
    print(f"  Whisper 전사 시작")
    print(f"  파일: {audio_path.name}")
    print(f"  모델: {model_name} | 디바이스: {device}")
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
            print(f"  [WARN] GPU 로딩 실패, CPU 재시도: {e}")
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
    print(f"  오디오 길이: {duration/60:.1f}분")
    print(f"  감지 언어: {info.language} (확률 {info.language_probability:.2f})")
    print()

    # 세그먼트 수집 + 진행률 표시
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

        # 진행률 표시 (5% 단위)
        if duration > 0:
            pct = int(seg.end / duration * 100)
            if pct >= last_pct + 5:
                last_pct = pct
                elapsed = time.time() - t0
                eta = (elapsed / max(seg.end, 1)) * (duration - seg.end)
                bar = "#" * (pct // 5) + "-" * (20 - pct // 5)
                print(
                    f"  [{bar}] {pct:3d}%  "
                    f"{seg.end/60:.0f}/{duration/60:.0f}분  "
                    f"ETA {eta/60:.1f}분",
                    end="\r",
                )

    print()  # 진행률 줄바꿈

    elapsed = time.time() - t0
    full_text = "\n".join(full_text_parts)

    print(f"\n  전사 완료: {elapsed:.1f}초 (실시간 대비 {duration/max(elapsed,0.1):.1f}x)")
    print(f"  세그먼트: {len(segments)}개 | 글자 수: {len(full_text)}")

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


# ─── 출력 저장 ───────────────────────────────────────────────────────────────

def save_transcript(
    audio_path: Path,
    result: dict,
    course: str,
    recording_date: Optional[datetime] = None,
) -> Path:
    """전사 결과를 MD 파일로 저장."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = (recording_date or datetime.now()).strftime("%Y%m%d")
    safe_name = re.sub(r"[^\w가-힣-]", "_", audio_path.stem)
    out_name = f"{date_str}_{course}_{safe_name}.md"
    out_path = TRANSCRIPTS_DIR / out_name

    # 중복 방지
    if out_path.exists():
        out_name = f"{date_str}_{course}_{safe_name}_{int(time.time()) % 10000}.md"
        out_path = TRANSCRIPTS_DIR / out_name

    duration_min = result["duration"] / 60
    word_count = len(result["text"])
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"---",
        f"title: \"{course} 수업 전사 ({date_str})\"",
        f"course: {course}",
        f"date: {date_str}",
        f"source: {audio_path.name}",
        f"duration: {duration_min:.1f}분",
        f"model: {result.get('model', DEFAULT_MODEL)}",
        f"language: {result['language']}",
        f"transcribed_at: {now_str}",
        f"word_count: {word_count}",
        f"---",
        f"",
        f"# {course} 수업 전사 ({date_str})",
        f"",
        f"- 원본: `{audio_path.name}`",
        f"- 길이: {duration_min:.1f}분",
        f"- 전사 소요: {result['elapsed']:.1f}초",
        f"- 글자 수: {word_count}",
        f"",
        f"---",
        f"",
        f"## 전사 내용",
        f"",
    ]

    # 타임스탬프 포함 전사
    for seg in result["segments"]:
        ts_start = _format_ts(seg["start"])
        ts_end = _format_ts(seg["end"])
        text = seg["text"]
        if text:
            lines.append(f"**[{ts_start} ~ {ts_end}]** {text}")
            lines.append("")

    # 전체 텍스트 (검색용)
    lines.extend([
        "",
        "---",
        "",
        "## 전체 텍스트 (검색용)",
        "",
        result["text"],
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  저장: {out_path}")
    return out_path


def _format_ts(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ─── T9 Seed 연동 ───────────────────────────────────────────────────────────

def register_entity(course: str, date_str: str, transcript_path: Path, duration_min: float):
    """t9_seed.py capture로 엔티티 등록."""
    if not T9_SEED.exists():
        print("  [WARN] t9_seed.py 없음, 엔티티 등록 건너뜀")
        return

    text = f"{course} 수업 전사 완료 ({date_str}, {duration_min:.0f}분) → {transcript_path.name}"
    try:
        subprocess.run(
            [sys.executable, str(T9_SEED), "capture", text],
            capture_output=True, text=True, timeout=10,
        )
        print(f"  T9 Seed 등록 완료")
    except Exception as e:
        print(f"  [WARN] T9 Seed 등록 실패: {e}")


# ─── DB 기록 ─────────────────────────────────────────────────────────────────

def record_transcription(
    conn: sqlite3.Connection,
    audio_path: Path,
    audio_hash_val: str,
    transcript_path: Path,
    course: str,
    result: dict,
):
    """전사 결과를 DB에 기록."""
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


# ─── 메인 명령어 ─────────────────────────────────────────────────────────────

def cmd_transcribe(audio_path_str: str, force: bool = False):
    """단일 파일 전사."""
    audio_path = Path(audio_path_str).resolve()

    if not audio_path.exists():
        print(f"[ERROR] 파일 없음: {audio_path}")
        sys.exit(1)

    if audio_path.suffix.lower() not in AUDIO_EXTS:
        print(f"[ERROR] 지원하지 않는 형식: {audio_path.suffix}")
        print(f"  지원 형식: {', '.join(sorted(AUDIO_EXTS))}")
        sys.exit(1)

    conn = init_db()
    try:
        h = file_hash(audio_path)

        if not force and is_already_transcribed(conn, h):
            print(f"[SKIP] 이미 전사됨: {audio_path.name}")
            row = conn.execute(
                "SELECT transcript_path FROM transcriptions WHERE audio_hash = ?", (h,)
            ).fetchone()
            if row:
                print(f"  결과: {row[0]}")
            return

        recording_date = extract_date_from_filename(audio_path)
        course = detect_course(audio_path, recording_date)
        date_str = (recording_date or datetime.now()).strftime("%Y%m%d")

        print(f"  과목: {course}")
        print(f"  날짜: {date_str}")

        result = transcribe_audio(audio_path)

        transcript_path = save_transcript(audio_path, result, course, recording_date)

        record_transcription(conn, audio_path, h, transcript_path, course, result)

        register_entity(course, date_str, transcript_path, result["duration"] / 60)

    except Exception as e:
        print(f"\n[ERROR] 전사 중 오류: {e}")
        raise
    finally:
        conn.close()

    print(f"\n{'='*60}")
    print(f"  전사 완료!")
    print(f"  결과: {transcript_path}")
    print(f"{'='*60}\n")

    return transcript_path


def cmd_batch(folder_str: str, force: bool = False):
    """폴더 내 전체 오디오 파일 일괄 전사."""
    folder = Path(folder_str).resolve()
    if not folder.is_dir():
        print(f"[ERROR] 폴더 없음: {folder}")
        sys.exit(1)

    audio_files = sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS
    )

    if not audio_files:
        print(f"[INFO] 오디오 파일 없음: {folder}")
        return

    print(f"\n전사 대상: {len(audio_files)}개 파일")
    for i, f in enumerate(audio_files, 1):
        print(f"  {i}. {f.name}")
    print()

    conn = init_db()
    success, skip, fail = 0, 0, 0

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] {audio_file.name}")

        h = file_hash(audio_file)
        if not force and is_already_transcribed(conn, h):
            print(f"  [SKIP] 이미 전사됨")
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
            print(f"  [ERROR] 전사 실패: {e}")
            conn.execute(
                """
                INSERT OR REPLACE INTO transcriptions
                (audio_path, audio_hash, course, created_at, status, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(audio_file), h, "미분류", datetime.now().isoformat(), "failed", str(e)),
            )
            conn.commit()
            fail += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"  배치 전사 완료")
    print(f"  성공: {success} | 건너뜀: {skip} | 실패: {fail}")
    print(f"{'='*60}\n")


def cmd_watch(folder_str: str = ""):
    """폴더 감시 모드. 새 오디오 파일이 추가되면 자동 전사."""
    folder = Path(folder_str).resolve() if folder_str else RECORDINGS_DIR
    folder.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Whisper 감시 모드 시작")
    print(f"  감시 폴더: {folder}")
    print(f"  Ctrl+C로 종료")
    print(f"{'='*60}\n")

    conn = init_db()
    seen: set[str] = set()

    # 기존 파일 해시 수집 (이미 있는 파일은 건너뜀)
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            seen.add(file_hash(f))

    running = True

    def _stop(signum, frame):
        nonlocal running
        running = False
        print("\n\n  감시 종료 중...")

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

                # 파일 쓰기 완료 대기 (크기 안정화)
                size1 = f.stat().st_size
                time.sleep(2)
                if not f.exists():
                    continue
                size2 = f.stat().st_size
                if size1 != size2:
                    continue  # 아직 쓰는 중

                seen.add(h)

                if is_already_transcribed(conn, h):
                    continue

                print(f"\n  [NEW] 새 파일 감지: {f.name}")
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
                print(f"  [ERROR] 감시 오류: {e}")
                time.sleep(poll_interval)

    conn.close()
    print("  감시 종료.")


def cmd_list():
    """전사 이력 조회."""
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
        print("전사 이력 없음.")
        conn.close()
        return

    print(f"\n{'과목':<12} {'파일':<30} {'길이':>6} {'글자':>7} {'상태':<8} {'날짜':<12}")
    print("-" * 85)

    for course, audio_path, dur, wc, created, status, tp in rows:
        fname = Path(audio_path).name[:28] if audio_path else "?"
        dur_str = f"{dur/60:.0f}분" if dur else "?"
        wc_str = f"{wc:,}" if wc else "?"
        date_str = created[:10] if created else "?"
        print(f"{course or '?':<12} {fname:<30} {dur_str:>6} {wc_str:>7} {status:<8} {date_str:<12}")

    conn.close()


def cmd_stats():
    """전사 통계."""
    conn = init_db()

    total = conn.execute("SELECT COUNT(*) FROM transcriptions WHERE status='completed'").fetchone()[0]
    total_dur = conn.execute("SELECT COALESCE(SUM(duration_sec),0) FROM transcriptions WHERE status='completed'").fetchone()[0]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count),0) FROM transcriptions WHERE status='completed'").fetchone()[0]

    print(f"\n{'='*40}")
    print(f"  Whisper Pipeline 통계")
    print(f"{'='*40}")
    print(f"  전사 완료: {total}개 파일")
    print(f"  총 녹음 시간: {total_dur/3600:.1f}시간")
    print(f"  총 글자 수: {total_words:,}")
    print()

    # 과목별 통계
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
        print(f"  {'과목':<16} {'횟수':>4} {'시간':>8} {'글자':>10}")
        print(f"  {'-'*42}")
        for course, cnt, dur, wc in rows:
            print(f"  {course:<16} {cnt:>4} {dur/60:.0f}분{' ':>3} {int(wc or 0):>10,}")

    print(f"{'='*40}\n")
    conn.close()


# ─── 엔트리포인트 ─────────────────────────────────────────────────────────────

USAGE = """
T9 OS Whisper Pipeline v1.0

사용법:
  whisper_pipeline.py transcribe <파일경로> [--force]
  whisper_pipeline.py batch <폴더경로> [--force]
  whisper_pipeline.py watch [폴더경로]
  whisper_pipeline.py list
  whisper_pipeline.py stats

과목 코드 (파일명 접두사):
  ML   → 머신러닝
  AE4  → AE4
  SAD  → 시스템분석및설계
  GOV  → AI와데이터거버넌스
  SL   → 서비스러닝

예시:
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
            print("[ERROR] 파일 경로 필요")
            print("  사용법: whisper_pipeline.py transcribe <파일경로>")
            sys.exit(1)
        cmd_transcribe(sys.argv[2], force=force)

    elif cmd == "batch":
        if len(sys.argv) < 3:
            print("[ERROR] 폴더 경로 필요")
            print("  사용법: whisper_pipeline.py batch <폴더경로>")
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
        print(f"[ERROR] 알 수 없는 명령: {cmd}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
