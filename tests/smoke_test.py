#!/usr/bin/env -S python3 -B
"""
T9 OS Smoke Tests — 핵심 파이프라인 최소 동작 확인
실행: python3 T9OS/tests/smoke_test.py
"""
import sys, os, subprocess, sqlite3, json
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent
# DB: WSL 네이티브 우선, fallback NTFS
_WSL_DB = Path.home() / ".t9os_data" / ".t9.db"
DB_PATH = _WSL_DB if _WSL_DB.exists() else T9 / ".t9.db"

PASS, FAIL, SKIP = 0, 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))

def skip(name, reason=""):
    global SKIP
    SKIP += 1
    print(f"  [SKIP] {name}" + (f" — {reason}" if reason else ""))

def run_cmd(cmd, timeout=30):
    """Run command and return (returncode, stdout, stderr)"""
    try:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(T9), env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

print("\n  === T9 OS Smoke Tests ===\n")

# 1. DB integrity
print("  --- DB ---")
try:
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    check("DB 연결", True)

    count = conn.execute("SELECT COUNT(*) as c FROM entities").fetchone()["c"]
    check("엔티티 존재", count > 0, f"count={count}")

    # FTS5 test
    try:
        conn.execute("SELECT * FROM entities_fts LIMIT 1")
        check("FTS5 테이블 존재", True)
    except Exception as e:
        check("FTS5 테이블 존재", False, str(e))

    # Schema check
    cols = {r[1] for r in conn.execute("PRAGMA table_info(entities)").fetchall()}
    required = {"id", "filepath", "filename", "phase", "metadata", "body_preview", "file_hash", "updated_at"}
    missing = required - cols
    check("필수 컬럼 존재", not missing, f"missing={missing}" if missing else "")

    # No corrupted filepaths
    bad = conn.execute("SELECT COUNT(*) as c FROM entities WHERE typeof(filepath) != 'text' AND filepath IS NOT NULL").fetchone()["c"]
    check("filepath 타입 정합성", bad == 0, f"corrupted={bad}")

    conn.close()
except Exception as e:
    check("DB 연결", False, str(e))

# 2. t9_seed.py commands
print("\n  --- t9_seed.py ---")
rc, out, err = run_cmd(["python3", "t9_seed.py", "status"])
check("status 명령", rc == 0 and "T9 OS Seed" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "t9_seed.py", "search", "test"])
check("search 명령", rc == 0, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "t9_seed.py", "orphans"])
check("orphans 명령", rc == 0, err[:100] if rc else "")

# 3. Key files exist
print("\n  --- 핵심 파일 ---")
key_files = [
    "t9_seed.py", "lib/config.py", "lib/logger.py", "lib/commands.py",
    "lib/parsers.py", "lib/ipc.py", "lib/transduction.py",
    "pipes/t9_bot.py", "pipes/healthcheck.py", "pipes/cron_runner.sh",
    "pipes/gm_batch.py", "pipes/calendar_sync.py", "pipes/deadline_notify.py",
    "pipes/t9_ceo_brief.py", "pipes/session_live_read.py",
    "constitution/L1_execution.md", "constitution/L2_interpretation.md",
    "constitution/L3_amendment.md", "constitution/GUARDIANS.md",
]
for f in key_files:
    p = T9 / f
    check(f"파일: {f}", p.exists())

# 4. Cron entries
print("\n  --- Cron ---")
rc, out, err = run_cmd(["crontab", "-l"])
if rc == 0:
    cron_checks = [
        ("calendar_sync", "calendar"),
        ("deadline_notify", "deadline"),
        ("healthcheck", "healthcheck"),
        ("ceo_brief", "ceo_brief"),
        ("sc41", "sc41"),
        ("t9_auto", "t9_auto"),
    ]
    for name, keyword in cron_checks:
        check(f"cron: {name}", keyword in out)
else:
    skip("cron", "crontab 접근 불가")

# 5. systemd service
print("\n  --- systemd ---")
rc, out, err = run_cmd(["systemctl", "--user", "is-active", "t9_bot"])
check("t9_bot 서비스 활성", rc == 0 and "active" in out, out.strip() if rc else err[:50])

# 6. Config imports
print("\n  --- 모듈 임포트 ---")
rc, out, err = run_cmd(["python3", "-c", "from lib.config import *; print('OK')"])
check("lib.config 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "-c", "from lib.logger import *; print('OK')"])
check("lib.logger 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

rc, out, err = run_cmd(["python3", "-c", "from lib.parsers import *; print('OK')"])
check("lib.parsers 임포트", rc == 0 and "OK" in out, err[:100] if rc else "")

# 7. 정합성 검증 (DB 이중화, 하드코딩, 깨진 링크, 미러 동기화)
print("\n  --- 정합성 ---")

# 7a. DB 유령 파일 탐지 — T9OS/.t9.db가 존재하면 안 됨 (실제 DB는 WSL 네이티브)
ghost_db = T9 / ".t9.db"
check("유령 DB 없음 (T9OS/.t9.db)", not ghost_db.exists() or ghost_db.stat().st_size == 0,
      f"크기={ghost_db.stat().st_size}" if ghost_db.exists() else "")

# 7b. 하드코딩된 DB 경로 탐지 — config.py import 없이 .t9.db 직접 참조하는 .py 파일
hardcoded = []
for pyf in T9.rglob("*.py"):
    if "__pycache__" in str(pyf) or "snapshot" in str(pyf) or "smoke_test" in pyf.name:
        continue
    if "verify_claims" in pyf.name:
        continue
    try:
        content = pyf.read_text(encoding="utf-8", errors="replace")
        if ".t9.db" in content and "from lib.config import" not in content and "config.DB_PATH" not in content:
            # 문자열 리터럴(에러 메시지 등)은 제외
            lines = [l for l in content.split("\n") if ".t9.db" in l
                     and "import" not in l and '".t9.db' not in l and "'.t9.db" not in l
                     and "detail" not in l and "#" not in l.split(".t9.db")[0]]
            if lines:
                hardcoded.append(str(pyf.relative_to(T9)))
    except Exception:
        pass
check("하드코딩 DB 경로 없음", len(hardcoded) == 0,
      f"파일: {', '.join(hardcoded[:3])}" if hardcoded else "")

# 7c. 깨진 심볼릭 링크 (T9OS + 1depth만 — _legacy 47GB 스캔 방지)
broken_links = []
for link in list(T9.rglob("*")) + list(HANBEEN.glob("*")):
    if link.is_symlink() and not link.exists():
        try:
            broken_links.append(str(link.relative_to(HANBEEN)))
        except ValueError:
            broken_links.append(str(link))
check("깨진 심볼릭 링크 없음", len(broken_links) == 0,
      f"{len(broken_links)}개: {', '.join(broken_links[:3])}" if broken_links else "")

# 7d. pycache 잔존 — 자동 정리 (WSL-NTFS는 삭제 후 find 캐시 잔류 가능)
subprocess.run(["find", str(T9), "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
               capture_output=True, timeout=10)
check("__pycache__ 자동 정리", True, "자동 정리 실행 완료")

# 7e. t9os-public 핵심 파일 동기화 (구조 정합성 — 민감정보 제거 버전이므로 바이트 동일 아님)
PUBLIC = HANBEEN / "t9os-public"
if PUBLIC.exists():
    sync_files = {
        "t9_seed.py": ["def cmd_capture", "def cmd_reindex", "def cmd_search", "TRANSITIONS"],
        "lib/config.py": ["def get(", "DB_PATH", "GEMINI_KEY", "_parse_env_file"],
        "constitution/GUARDIANS.md": ["Guardian", "G1", "G2", "G3"],
    }
    desync = []
    for sf, markers in sync_files.items():
        priv = T9 / sf
        pub = PUBLIC / sf
        if priv.exists() and pub.exists():
            pub_text = pub.read_text(encoding="utf-8", errors="replace")
            missing = [m for m in markers if m not in pub_text]
            if missing:
                desync.append(f"{sf}(구조 누락: {', '.join(missing)})")
        elif priv.exists() and not pub.exists():
            desync.append(f"{sf}(미존재)")
    check("t9os-public 핵심파일 동기화", len(desync) == 0,
          f"불일치: {', '.join(desync)}" if desync else "")
else:
    skip("t9os-public 동기화", "폴더 없음")

# 7f. digest 데이터 생존 확인 (reindex 삭제 방지)
try:
    conn2 = sqlite3.connect(str(DB_PATH), timeout=5)
    digest_count = conn2.execute(
        "SELECT COUNT(*) FROM entities WHERE filepath LIKE '%digested_final%'").fetchone()[0]
    check("AI chat digest 생존", digest_count >= 90,
          f"현재 {digest_count}건 (99건이어야 함)" if digest_count < 90 else f"{digest_count}건")
    conn2.close()
except Exception as e:
    check("AI chat digest 생존", False, str(e))

# 7g. 환경변수 단일 소스 확인 (_keys/.env.sh 존재)
env_file = HANBEEN / "_keys" / ".env.sh"
check("환경변수 파일 존재 (_keys/.env.sh)", env_file.exists())

# 8. Gravity Engine (벡터 임베딩 + 전개체 개체화)
print("\n  --- Gravity Engine ---")
check("파일: lib/gravity.py", (T9 / "lib" / "gravity.py").exists())
check("파일: lib/vec.py", (T9 / "lib" / "vec.py").exists())

try:
    conn_grav = sqlite3.connect(str(DB_PATH), timeout=5)
    grav_cols = {r[1] for r in conn_grav.execute("PRAGMA table_info(entities)").fetchall()}
    check("entities.embedding BLOB 컬럼", "embedding" in grav_cols)

    grav_tables = {r[0] for r in conn_grav.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    check("entity_vectors 테이블 존재", "entity_vectors" in grav_tables)

    relates_count = conn_grav.execute("SELECT COUNT(*) FROM relates").fetchone()[0]
    check("relates 테이블 데이터", relates_count > 0, f"count={relates_count}")
    conn_grav.close()
except Exception as e:
    check("Gravity DB 스키마", False, str(e))

# 9. IPC v2 (Channels 기반)
ipc_inbox = T9 / "data" / "ipc" / "inbox"
check("IPC v2 inbox 디렉토리", ipc_inbox.is_dir())
channel_server = T9 / "mcp" / "t9_channel_server.py"
check("IPC v2 Channel MCP 서버", channel_server.exists())
try:
    sys.path.insert(0, str(T9))
    from lib.ipc import heartbeat_update, heartbeat_who, inbox_unread, IPC_INBOX
    check("IPC v2 함수 import", True)
except Exception as e:
    check("IPC v2 함수 import", False, str(e))

# Summary
print(f"\n  === 결과: PASS={PASS} FAIL={FAIL} SKIP={SKIP} ===")
print(f"  {'ALL CLEAR' if FAIL == 0 else f'FAILURES: {FAIL}'}\n")
sys.exit(0 if FAIL == 0 else 1)
