"""T9 OS Inter-Session Communication (IPC) v2
시몽동 기반 세션 간 통신: 메시지 = 전개체, 수신 = 개체화, 전도 = discovery

v2 변경 (2026-03-26):
- 파일=truth 원칙 도입 (TAP 참고). 메시지는 파일에 저장, DB는 캐시.
- heartbeat 파일 기반 세션 발견 (PID + heartbeat 이중 체크)
- Claude Channels MCP 서버(t9_channel_server.py)와 연동
"""
import sqlite3, os, json, re, signal
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
from lib.config import DB_PATH  # WSL 네이티브 DB
SESSION_FILE = Path.home() / ".t9_current_session"
WORKING_MD = T9.parent / ".claude" / "WORKING.md"

# v2: 파일 기반 IPC 디렉토리
IPC_DIR = T9 / "data" / "ipc"
IPC_INBOX = IPC_DIR / "inbox"
IPC_ARCHIVE = IPC_DIR / "archive"
HEARTBEATS_FILE = IPC_DIR / "heartbeats.json"

# 디렉토리 보장
IPC_INBOX.mkdir(parents=True, exist_ok=True)
IPC_ARCHIVE.mkdir(parents=True, exist_ok=True)

def _db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    _ensure_tables(conn)
    return conn

def _ensure_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        status TEXT DEFAULT 'active',
        working_on TEXT DEFAULT '',
        pid INTEGER,
        claimed_project TEXT DEFAULT '',
        capacity TEXT DEFAULT 'idle'
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_session TEXT NOT NULL,
        to_session TEXT,
        type TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        priority TEXT DEFAULT 'normal',
        created_at TEXT NOT NULL,
        read_at TEXT,
        expires_at TEXT
    );
    CREATE TABLE IF NOT EXISTS file_locks (
        filepath TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        locked_at TEXT NOT NULL,
        operation TEXT DEFAULT 'edit'
    );
    CREATE TABLE IF NOT EXISTS session_equity (
        session_id TEXT PRIMARY KEY,
        started_at TEXT,
        ended_at TEXT,
        duration_minutes INTEGER,
        entities_created INTEGER DEFAULT 0,
        files_modified INTEGER DEFAULT 0,
        debt_reduced REAL DEFAULT 0,
        user_satisfaction REAL DEFAULT 0,
        equity_score REAL DEFAULT 0,
        recommendation TEXT,
        blockers TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    """)
    conn.commit()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── v2: 파일 기반 메시지 + Heartbeat ─────────────────────────

def _save_msg_file(from_sid, to_sid, msg_type, subject, body="", priority="normal"):
    """메시지를 파일로 저장 (truth). TAP 파일명 규약."""
    today = datetime.now().strftime("%Y%m%d")
    from_short = from_sid[:8] if from_sid else "system"
    to_short = (to_sid[:8] if to_sid and to_sid != "all" else "all")
    safe_subject = re.sub(r'[^\w\-]', '_', subject)[:40]
    filename = f"{today}-{from_short}-{to_short}-{safe_subject}.md"
    filepath = IPC_INBOX / filename

    content = f"""---
from: {from_sid}
to: {to_sid or 'broadcast'}
type: {msg_type}
subject: {subject}
priority: {priority}
created: {_now()}
---

{body}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath

def heartbeat_update(session_id, status="active"):
    """Heartbeat 파일 갱신 (TAP 방식). 모든 도구 호출 시 자동 실행."""
    data = {}
    if HEARTBEATS_FILE.exists():
        try:
            data = json.loads(HEARTBEATS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    data[session_id] = {
        "timestamp": _now(),
        "status": status,
        "pid": os.getpid(),
    }

    # stale 세션 제거 (10분 타임아웃)
    cutoff = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    data = {k: v for k, v in data.items()
            if v.get("timestamp", "") >= cutoff or v.get("status") == "signing-off"}

    HEARTBEATS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def heartbeat_who():
    """살아있는 세션 목록 (heartbeat 기반)."""
    if not HEARTBEATS_FILE.exists():
        return []
    try:
        data = json.loads(HEARTBEATS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    cutoff = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    alive = []
    for sid, info in data.items():
        if info.get("timestamp", "") >= cutoff and info.get("status") != "signing-off":
            alive.append({"session_id": sid, **info})
    return alive

def inbox_unread(session_id):
    """미읽은 메시지 파일 스캔 (파일 기반)."""
    if not IPC_INBOX.exists():
        return []
    short_id = session_id[:8]
    unread = []
    for f in sorted(IPC_INBOX.glob("*.md")):
        name = f.stem  # YYYYMMDD-from-to-subject
        parts = name.split("-", 3)
        if len(parts) < 4:
            continue
        to_field = parts[2]
        if to_field == short_id or to_field == "all":
            unread.append({"file": f.name, "path": str(f), "to": to_field, "subject": parts[3]})
    return unread

def _pid_alive(pid):
    """PID가 살아있는지 확인 (Linux)"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 권한 없을 뿐, 프로세스는 살아있음

# ─── 세션 관리 ─────────────────────────────────────────────────

def session_register(session_id, pid):
    conn = _db()
    # stale 세션 정리 먼저
    _cleanup_stale(conn)
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, started_at, status, pid) VALUES (?,?,?,?)",
        (session_id, _now(), "active", pid)
    )
    conn.commit()
    SESSION_FILE.write_text(session_id)
    print(f"  세션 등록: {session_id} (PID {pid})")
    conn.close()

def session_end(session_id):
    conn = _db()
    conn.execute("UPDATE sessions SET ended_at=?, status='ended' WHERE id=?", (_now(), session_id))
    # 해당 세션의 모든 잠금 해제
    released = conn.execute("DELETE FROM file_locks WHERE session_id=?", (session_id,)).rowcount
    conn.commit()
    if released:
        print(f"  잠금 해제: {released}건")
    print(f"  세션 종료: {session_id}")
    _sync_working(conn)
    conn.close()

def session_heartbeat(session_id, working_on=""):
    conn = _db()
    conn.execute("UPDATE sessions SET working_on=? WHERE id=?", (working_on, session_id))
    conn.commit()
    conn.close()

def session_list():
    conn = _db()
    _cleanup_stale(conn)
    rows = conn.execute(
        "SELECT id, started_at, status, working_on, pid FROM sessions WHERE status='active' ORDER BY started_at"
    ).fetchall()
    if not rows:
        print("  활성 세션 없음")
    else:
        print(f"  활성 세션 {len(rows)}개:")
        for r in rows:
            work = f" — {r[3]}" if r[3] else ""
            print(f"    [{r[0]}] PID={r[4]} 시작={r[1]}{work}")
    # 잠긴 파일도 표시
    locks = conn.execute("SELECT filepath, session_id FROM file_locks").fetchall()
    if locks:
        print(f"  잠긴 파일 {len(locks)}개:")
        for fp, sid in locks:
            print(f"    🔒 {fp} ← {sid}")
    conn.close()

def _cleanup_stale(conn):
    """PID가 죽은 active 세션 → crashed 처리 + 잠금 해제 + ended 세션 잔여 잠금 정리"""
    active = conn.execute("SELECT id, pid FROM sessions WHERE status='active'").fetchall()
    for sid, pid in active:
        if pid and not _pid_alive(pid):
            conn.execute("UPDATE sessions SET status='crashed', ended_at=? WHERE id=?", (_now(), sid))
            released = conn.execute("DELETE FROM file_locks WHERE session_id=?", (sid,)).rowcount
            print(f"  ⚠️ stale 세션 정리: {sid} (PID {pid} 죽음, 잠금 {released}건 해제)")
    # ended/crashed 세션의 잔여 잠금도 정리 (session-end 백그라운드 실패 시 남은 것)
    orphaned = conn.execute("""
        DELETE FROM file_locks WHERE session_id IN (
            SELECT id FROM sessions WHERE status IN ('ended', 'crashed')
        )
    """).rowcount
    if orphaned:
        print(f"  ⚠️ 고아 잠금 정리: {orphaned}건 (종료된 세션)")
    conn.commit()

# ─── 메시지 ────────────────────────────────────────────────────

def msg_send(from_sid, to_sid, msg_type, subject, body="", priority="normal"):
    conn = _db()
    expires = None
    if msg_type in ("lock", "unlock", "alert"):
        expires = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    elif msg_type == "work_progress":
        expires = (datetime.now() + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO messages (from_session, to_session, type, subject, body, priority, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
        (from_sid, to_sid if to_sid != "all" else None, msg_type, subject, body, priority, _now(), expires)
    )
    conn.commit()
    target = to_sid if to_sid and to_sid != "all" else "전체"
    print(f"  📨 [{msg_type}] → {target}: {subject}")
    conn.close()

    # v2: 파일=truth — 메시지를 파일로도 저장 (Channel 서버가 fs.watch로 감지)
    _save_msg_file(from_sid, to_sid, msg_type, subject, body, priority)

    # v2: escalation → 텔레그램 알림 (한빈에게 즉시 전달)
    if msg_type == "escalation":
        _tg_escalation(subject, body)


def _tg_escalation(subject, body=""):
    """escalation 시 텔레그램으로 한빈에게 알림."""
    try:
        import subprocess as _sp
        tg_common = T9 / "pipes" / "tg_common.py"
        if tg_common.exists():
            msg = f"🚨 [ESCALATION] {subject}\n{body[:200]}"
            _sp.Popen(
                ["python3", str(tg_common), msg],
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            )
    except Exception:
        pass

def msg_check(session_id):
    conn = _db()
    # 만료된 메시지 정리
    conn.execute("UPDATE messages SET status='expired' WHERE expires_at IS NOT NULL AND expires_at < ? AND status='pending'", (_now(),))
    conn.commit()
    # 해당 세션 또는 broadcast의 미읽은 메시지
    rows = conn.execute("""
        SELECT id, from_session, type, subject, body, priority, created_at
        FROM messages
        WHERE status='pending' AND (to_session=? OR to_session IS NULL)
        ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, created_at
    """, (session_id,)).fetchall()
    if rows:
        print(f"  📬 미읽은 메시지 {len(rows)}건:")
        for r in rows:
            icon = "🔴" if r[5] == "critical" else "🟡" if r[5] == "high" else "📩"
            print(f"    {icon} [{r[0]}] {r[2]}|{r[3]} (from {r[1]}, {r[6]})")
            if r[4]:
                print(f"       {r[4][:100]}")
    else:
        print("  📭 미읽은 메시지 없음")
    conn.close()
    return rows

def msg_read(msg_id, session_id):
    conn = _db()
    conn.execute("UPDATE messages SET status='read', read_at=? WHERE id=?", (_now(), msg_id))
    conn.commit()
    conn.close()

def msg_act(msg_id, session_id):
    conn = _db()
    conn.execute("UPDATE messages SET status='acted', read_at=? WHERE id=?", (_now(), msg_id))
    conn.commit()
    conn.close()

# ─── 파일 잠금 ─────────────────────────────────────────────────

def lock_acquire(session_id, filepath, operation="edit"):
    conn = _db()
    try:
        existing = conn.execute("SELECT session_id, locked_at FROM file_locks WHERE filepath=?", (filepath,)).fetchone()
        if existing:
            if existing[0] == session_id:
                return True  # 이미 본인이 잠금
            other_session = conn.execute("SELECT pid FROM sessions WHERE id=?", (existing[0],)).fetchone()
            if other_session and other_session[0] and not _pid_alive(other_session[0]):
                conn.execute("DELETE FROM file_locks WHERE filepath=?", (filepath,))
            else:
                print(f"  🔒 BLOCKED: {filepath} ← 세션 {existing[0]} 수정 중 ({existing[1]})")
                return False
        conn.execute(
            "INSERT OR REPLACE INTO file_locks (filepath, session_id, locked_at, operation) VALUES (?,?,?,?)",
            (filepath, session_id, _now(), operation)
        )
        conn.commit()
        return True
    finally:
        conn.close()

def lock_release(session_id, filepath):
    conn = _db()
    conn.execute("DELETE FROM file_locks WHERE filepath=? AND session_id=?", (filepath, session_id))
    conn.commit()
    conn.close()

def lock_check(filepath):
    conn = _db()
    row = conn.execute("SELECT session_id, locked_at, operation FROM file_locks WHERE filepath=?", (filepath,)).fetchone()
    conn.close()
    if row:
        print(f"  🔒 {filepath}: 세션 {row[0]} ({row[2]}, {row[1]})")
        return row
    else:
        print(f"  🔓 {filepath}: 잠금 없음")
        return None

# ─── WORKING.md 자동 동기화 ────────────────────────────────────

def _sync_working(conn):
    """활성 세션 + 잠금 + 메시지를 WORKING.md [AUTO] 섹션에 반영"""
    sessions = conn.execute(
        "SELECT id, started_at, working_on, pid FROM sessions WHERE status='active' ORDER BY started_at"
    ).fetchall()
    locks = conn.execute("SELECT filepath, session_id FROM file_locks").fetchall()
    pending = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE status='pending'"
    ).fetchone()[0]

    auto_section = f"\n## [AUTO] 세션 현황 ({_now()})\n\n"
    if sessions:
        auto_section += f"### 활성 세션 {len(sessions)}개\n"
        for s in sessions:
            work = f" — {s[2]}" if s[2] else ""
            project = ""
            try:
                p = conn.execute("SELECT claimed_project FROM sessions WHERE id=?", (s[0],)).fetchone()
                if p and p[0]:
                    project = f" [{p[0]}]"
            except Exception:
                pass
            auto_section += f"- `{s[0]}` (PID {s[3]}){project}{work}\n"
    else:
        auto_section += "활성 세션 없음\n"

    # 프로젝트 claim 현황 (session_lock.py 통합 — 구체화 v2)
    claims_json = T9.parent / "T9OS" / ".session_locks.json"
    if not claims_json.exists():
        claims_json = T9 / ".session_locks.json"
    if claims_json.exists():
        try:
            cdata = json.loads(claims_json.read_text(encoding="utf-8"))
            claim_sessions = cdata.get("sessions", {})
            if claim_sessions:
                auto_section += f"\n### 프로젝트 claim\n"
                for sid, info in claim_sessions.items():
                    projects = ", ".join(info.get("working_on", []))
                    if projects:
                        auto_section += f"- `{sid[:16]}` → {projects}\n"
        except Exception:
            pass

    if locks:
        auto_section += f"\n### 잠긴 파일 {len(locks)}개\n"
        for fp, sid in locks:
            auto_section += f"- 🔒 `{fp}` ← `{sid}`\n"

    if pending:
        auto_section += f"\n### 미처리 메시지 {pending}건\n"

    # IPC inbox 요약
    inbox_count = len(list(IPC_INBOX.glob("*.md"))) if IPC_INBOX.exists() else 0
    if inbox_count:
        auto_section += f"\n### IPC inbox {inbox_count}건\n"

    # WORKING.md에서 기존 [AUTO] 섹션 교체 (없으면 맨 아래 추가)
    if WORKING_MD.exists():
        content = WORKING_MD.read_text(encoding="utf-8")
        # [AUTO] 섹션 찾기: 해당 줄부터 파일 끝까지 잘라내고 새 섹션으로 교체
        marker = "\n## [AUTO]"
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx]
        content = content.rstrip() + "\n" + auto_section
        WORKING_MD.write_text(content, encoding="utf-8")

def sync_working_md():
    conn = _db()
    _sync_working(conn)
    conn.close()
    print("  WORKING.md 동기화 완료")

# ─── CLI 래퍼 ──────────────────────────────────────────────────

def cli(args):
    """t9_seed.py에서 호출. args = sys.argv[2:]"""
    if not args:
        print("  사용법: t9_seed.py ipc <session|msg|lock|sync> ...")
        return

    cmd = args[0]
    if cmd == "session":
        sub = args[1] if len(args) > 1 else ""
        if sub == "register" and len(args) >= 4:
            session_register(args[2], int(args[3]))
        elif sub == "end" and len(args) >= 3:
            session_end(args[2])
        elif sub == "list":
            session_list()
        elif sub == "heartbeat" and len(args) >= 3:
            session_heartbeat(args[2], " ".join(args[3:]) if len(args) > 3 else "")
        else:
            print("  사용법: ipc session register|end|list|heartbeat <id> [args]")

    elif cmd == "msg":
        sub = args[1] if len(args) > 1 else ""
        if sub == "send" and len(args) >= 6:
            msg_send(args[2], args[3], args[4], args[5], " ".join(args[6:]) if len(args) > 6 else "")
        elif sub == "check" and len(args) >= 3:
            msg_check(args[2])
        elif sub == "read" and len(args) >= 4:
            msg_read(int(args[2]), args[3])
        elif sub == "act" and len(args) >= 4:
            msg_act(int(args[2]), args[3])
        else:
            print("  사용법: ipc msg send|check|read|act <args>")

    elif cmd == "lock":
        sub = args[1] if len(args) > 1 else ""
        if sub == "acquire" and len(args) >= 4:
            lock_acquire(args[2], args[3])
        elif sub == "release" and len(args) >= 4:
            lock_release(args[2], args[3])
        elif sub == "check" and len(args) >= 3:
            lock_check(args[2])
        elif sub == "list":
            conn = _db()
            locks = conn.execute("SELECT filepath, session_id, locked_at FROM file_locks").fetchall()
            if locks:
                for fp, sid, at in locks:
                    print(f"  🔒 {fp} ← {sid} ({at})")
            else:
                print("  잠긴 파일 없음")
            conn.close()
        else:
            print("  사용법: ipc lock acquire|release|check|list <args>")

    elif cmd == "sync":
        sync_working_md()
    else:
        print(f"  알 수 없는 IPC 명령: {cmd}")
