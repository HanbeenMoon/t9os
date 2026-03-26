"""T9 OS Inter-Session Communication (IPC)
cross-session IPC: message = Preindividual, = Individuating, Transduction = discovery
"""
import sqlite3, os, json, re, signal
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
from lib.config import DB_PATH  # WSL DB
SESSION_FILE = Path.home() / ".t9_current_session"
WORKING_MD = T9.parent / ".claude" / "WORKING.md"

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
        pid INTEGER
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
    """)
    conn.commit()

def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _pid_alive(pid):
    """PIDcheck (Linux)"""
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # permission , process

# ─── session ────────────────────────────────────────

def session_register(session_id, pid):
    conn = _db()
    # stale session clean up
    _cleanup_stale(conn)
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, started_at, status, pid) VALUES (?,?,?,?)",
        (session_id, _now(), "active", pid)
    )
    conn.commit()
    SESSION_FILE.write_text(session_id)
    print(f"  session register: {session_id} (PID {pid})")
    conn.close()

def session_end(session_id):
    conn = _db()
    conn.execute("UPDATE sessions SET ended_at=?, status='ended' WHERE id=?", (_now(), session_id))
    # session
    released = conn.execute("DELETE FROM file_locks WHERE session_id=?", (session_id,)).rowcount
    conn.commit()
    if released:
        print(f"  : {released}items")
    print(f"  session end: {session_id}")
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
        print("  active session not found")
    else:
        print(f"  active session {len(rows)}:")
        for r in rows:
            work = f" — {r[3]}" if r[3] else ""
            print(f"    [{r[0]}] PID={r[4]} start={r[1]}{work}")
    # file
    locks = conn.execute("SELECT filepath, session_id FROM file_locks").fetchall()
    if locks:
        print(f"  file {len(locks)}:")
        for fp, sid in locks:
            print(f"    🔒 {fp} ← {sid}")
    conn.close()

def _cleanup_stale(conn):
    """PIDactive session → crashed process + + ended session clean up"""
    active = conn.execute("SELECT id, pid FROM sessions WHERE status='active'").fetchall()
    for sid, pid in active:
        if pid and not _pid_alive(pid):
            conn.execute("UPDATE sessions SET status='crashed', ended_at=? WHERE id=?", (_now(), sid))
            released = conn.execute("DELETE FROM file_locks WHERE session_id=?", (sid,)).rowcount
            print(f"  ⚠️ stale session clean up: {sid} (PID {pid} , {released}items )")
    # ended/crashed sessionclean up (session-end failed )
    orphaned = conn.execute("""
        DELETE FROM file_locks WHERE session_id IN (
            SELECT id FROM sessions WHERE status IN ('ended', 'crashed')
        )
    """).rowcount
    if orphaned:
        print(f"  ⚠️ clean up: {orphaned}items (endsession)")
    conn.commit()

# ─── message ────────────────────────────────────────────────────

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
    target = to_sid if to_sid and to_sid != "all" else "total"
    print(f"  📨 [{msg_type}] → {target}: {subject}")
    conn.close()

def msg_check(session_id):
    conn = _db()
    # expiredmessage clean up
    conn.execute("UPDATE messages SET status='expired' WHERE expires_at IS NOT NULL AND expires_at < ? AND status='pending'", (_now(),))
    conn.commit()
    # session broadcastmessage
    rows = conn.execute("""
        SELECT id, from_session, type, subject, body, priority, created_at
        FROM messages
        WHERE status='pending' AND (to_session=? OR to_session IS NULL)
        ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, created_at
    """, (session_id,)).fetchall()
    if rows:
        print(f"  📬 message {len(rows)}items:")
        for r in rows:
            icon = "🔴" if r[5] == "critical" else "🟡" if r[5] == "high" else "📩"
            print(f"    {icon} [{r[0]}] {r[2]}|{r[3]} (from {r[1]}, {r[6]})")
            if r[4]:
                print(f"       {r[4][:100]}")
    else:
        print("  📭 message not found")
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

# ─── file ────────────────────────────────────────

def lock_acquire(session_id, filepath, operation="edit"):
    conn = _db()
    try:
        existing = conn.execute("SELECT session_id, locked_at FROM file_locks WHERE filepath=?", (filepath,)).fetchone()
        if existing:
            if existing[0] == session_id:
                return True
            other_session = conn.execute("SELECT pid FROM sessions WHERE id=?", (existing[0],)).fetchone()
            if other_session and other_session[0] and not _pid_alive(other_session[0]):
                conn.execute("DELETE FROM file_locks WHERE filepath=?", (filepath,))
            else:
                print(f"  🔒 BLOCKED: {filepath} ← session {existing[0]} modify ({existing[1]})")
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
        print(f"  🔒 {filepath}: session {row[0]} ({row[2]}, {row[1]})")
        return row
    else:
        print(f"  🔓 {filepath}: not found")
        return None

# ─── WORKING.md auto sync ────────────────────────────────────

def _sync_working(conn):
    """active session + + messageWORKING.md [AUTO] """
    sessions = conn.execute(
        "SELECT id, started_at, working_on, pid FROM sessions WHERE status='active' ORDER BY started_at"
    ).fetchall()
    locks = conn.execute("SELECT filepath, session_id FROM file_locks").fetchall()
    pending = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE status='pending'"
    ).fetchone()[0]

    auto_section = f"\n## [AUTO] session ({_now()})\n\n"
    if sessions:
        auto_section += f"### active session {len(sessions)}\n"
        for s in sessions:
            work = f" — {s[2]}" if s[2] else ""
            auto_section += f"- `{s[0]}` (PID {s[3]}){work}\n"
    else:
        auto_section += "active session not found\n"

    if locks:
        auto_section += f"\n### file {len(locks)}\n"
        for fp, sid in locks:
            auto_section += f"- 🔒 `{fp}` ← `{sid}`\n"

    if pending:
        auto_section += f"\n### process message {pending}items\n"

    # WORKING.mdexisting [AUTO] (add)
    if WORKING_MD.exists():
        content = WORKING_MD.read_text(encoding="utf-8")
        # [AUTO] (next ## file )
        pattern = r'\n## \[AUTO\][^\n]*\n(?:(?!## ).)*'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, auto_section, content, count=1, flags=re.DOTALL)
        else:
            content += auto_section
        WORKING_MD.write_text(content, encoding="utf-8")

def sync_working_md():
    conn = _db()
    _sync_working(conn)
    conn.close()
    print("  WORKING.md sync completed")

# ─── CLI ────────────────────────────────────────

def cli(args):
    """t9_seed.pycall. args = sys.argv[2:]"""
    if not args:
        print("  use: t9_seed.py ipc <session|msg|lock|sync> ...")
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
            print("  use: ipc session register|end|list|heartbeat <id> [args]")

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
            print("  use: ipc msg send|check|read|act <args>")

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
                print("  file not found")
            conn.close()
        else:
            print("  use: ipc lock acquire|release|check|list <args>")

    elif cmd == "sync":
        sync_working_md()
    else:
        print(f"  unknown IPC command: {cmd}")
