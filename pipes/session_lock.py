"""T9 OS Session Lock — project/file 
session fileitems.
- project claim: project namefile pattern claim
- file claim: file/pattern claim
- conflict check: modify session claim check
- heartbeat: 30 min response auto expired
- JSON sync: .session_locks.jsonstate record

stdlibuse. file. path hardcoded .
"""
import json
import os
import re
import fnmatch
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent
LOCKS_JSON = T9 / ".session_locks.json"
SESSION_FILE = Path.home() / ".t9_current_session"

# project → file pattern mapping (: JSON config file)
_DEFAULT_PROJECT_PATTERNS = {
    "ODNAR":      ["PROJECTS/ODNAR/*", "T9OS/artifacts/odnar_*/*"],
    "SSK":        ["PROJECTS/SSK_RA/*", "T9OS/artifacts/ssk_*/*"],
    "T9":         ["T9OS/t9_seed.py", "T9OS/lib/*", "T9OS/pipes/*",
                   "T9OS/constitution/*", "T9OS/telos/*", "T9OS/config/*",
                   ".claude/*"],
    "T9D":        ["PROJECTS/t9-dashboard/*"],
    "SC41":       ["PERSONAL/academic/*", "T9OS/artifacts/sc41_*/*"],
    "PM3":        ["PROJECTS/PM3/*", "T9OS/artifacts/pm3_*/*"],
    "L2U":        ["T9OS/pipes/t9_bot.py", "T9OS/pipes/whisper_pipeline.py"],
    "FinBot":     ["T9OS/artifacts/finbot_*/*"],
    "Dashboard":  ["PROJECTS/t9-dashboard/*"],
    "AT1":        ["T9OS/artifacts/at1_*/*"],
}

HEARTBEAT_TIMEOUT_MIN = 30


def _get_session_id() -> str:
    """current session ID. PID create."""
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text().strip()
    return f"unknown_{os.getpid()}"


def _load_locks() -> dict:
    """JSON file. structure."""
    if LOCKS_JSON.exists():
        try:
            return json.loads(LOCKS_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"sessions": {}}


def _save_locks(data: dict) -> None:
    """JSON file."""
    LOCKS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _is_stale(session: dict) -> bool:
    """heartbeatHEARTBEAT_TIMEOUT_MIN stale."""
    hb = session.get("last_heartbeat", session.get("started", ""))
    if not hb:
        return True
    try:
        last = datetime.fromisoformat(hb)
        return (datetime.now() - last) > timedelta(minutes=HEARTBEAT_TIMEOUT_MIN)
    except ValueError:
        return True


def _cleanup_stale(data: dict) -> list[str]:
    """stale sessionremoveremovesession ID return."""
    removed = []
    for sid in list(data["sessions"].keys()):
        if _is_stale(data["sessions"][sid]):
            removed.append(sid)
            del data["sessions"][sid]
    return removed


def _get_project_patterns(project: str) -> list[str]:
    """projectfile patternreturn. config file ."""
    custom_path = T9 / "config" / "project_patterns.json"
    patterns = dict(_DEFAULT_PROJECT_PATTERNS)
    if custom_path.exists():
        try:
            custom = json.loads(custom_path.read_text(encoding="utf-8"))
            patterns.update(custom)
        except (json.JSONDecodeError, OSError):
            pass
    # skip
    for key in patterns:
        if key.upper() == project.upper():
            return patterns[key]
    # PROJECTS/<project>/* default pattern
    return [f"PROJECTS/{project}/*", f"T9OS/artifacts/{project.lower()}_*/*"]


def _patterns_overlap(patterns_a: list[str], patterns_b: list[str]) -> list[str]:
    """pattern patternreturn.
    file patterncompare. patterncheck."""
    overlaps = []
    for pa in patterns_a:
        for pb in patterns_b:
            if pa == pb:
                overlaps.append(pa)
                continue
            # file pathpattern
            if not pa.endswith("*") and _file_matches_patterns(pa, [pb]):
                overlaps.append(f"{pa} <-> {pb}")
            elif not pb.endswith("*") and _file_matches_patterns(pb, [pa]):
                overlaps.append(f"{pa} <-> {pb}")
            # globprefix
            elif pa.endswith("/*") and pb.endswith("/*"):
                pa_dir = pa[:-2]
                pb_dir = pb[:-2]
                #
                if pa_dir == pb_dir:
                    overlaps.append(pa)
                elif pa_dir.startswith(pb_dir + "/") or pb_dir.startswith(pa_dir + "/"):
                    overlaps.append(f"{pa} <-> {pb}")
    return overlaps


def _file_matches_patterns(filepath: str, patterns: list[str]) -> bool:
    """file pathpattern check."""
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # pattern (/*), path
        if pattern.endswith("/*") and filepath.startswith(pattern[:-2]):
            return True
    return False


# ─── API ────────────────────────────────────────


def claim_project(project: str, description: str = "") -> bool:
    """projectcurrent sessionclaim. False return."""
    sid = _get_session_id()
    data = _load_locks()
    removed = _cleanup_stale(data)
    if removed:
        print(f"  [stale] expiredsession {len(removed)}clean up: {', '.join(removed)}")

    patterns = _get_project_patterns(project)

    # session
    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        other_patterns = other.get("files_claimed", [])
        overlaps = _patterns_overlap(patterns, other_patterns)
        if overlaps:
            other_projects = ", ".join(other.get("working_on", []))
            print(f"  [CONFLICT] {project} patternsession {other_sid} ({other_projects}):")
            for o in overlaps:
                print(f"    - {o}")
            print(f"  -> sessionreleasemanual ")
            return False

    # claim register
    now = _now_iso()
    if sid not in data["sessions"]:
        data["sessions"][sid] = {
            "started": now,
            "last_heartbeat": now,
            "working_on": [],
            "files_claimed": [],
            "description": "",
        }

    session = data["sessions"][sid]
    if project.upper() not in [p.upper() for p in session["working_on"]]:
        session["working_on"].append(project)
    # pattern add (duplicate remove)
    for p in patterns:
        if p not in session["files_claimed"]:
            session["files_claimed"].append(p)
    if description:
        session["description"] = description
    session["last_heartbeat"] = now

    _save_locks(data)
    print(f"  [CLAIMED] {project} -> session {sid}")
    print(f"    pattern: {', '.join(patterns)}")
    return True


def claim_file(filepath: str) -> bool:
    """file/patterncurrent sessionclaim."""
    sid = _get_session_id()
    data = _load_locks()
    _cleanup_stale(data)

    # session
    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        if _file_matches_patterns(filepath, other.get("files_claimed", [])):
            other_projects = ", ".join(other.get("working_on", []))
            print(f"  [CONFLICT] {filepath} -> session {other_sid} ({other_projects})claim ")
            return False

    now = _now_iso()
    if sid not in data["sessions"]:
        data["sessions"][sid] = {
            "started": now,
            "last_heartbeat": now,
            "working_on": [],
            "files_claimed": [],
            "description": "",
        }

    session = data["sessions"][sid]
    if filepath not in session["files_claimed"]:
        session["files_claimed"].append(filepath)
    session["last_heartbeat"] = now

    _save_locks(data)
    print(f"  [CLAIMED] {filepath} -> session {sid}")
    return True


def check_file(filepath: str) -> dict | None:
    """file modify call. claimed by another sessionsession return."""
    sid = _get_session_id()
    data = _load_locks()
    _cleanup_stale(data)

    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        if _file_matches_patterns(filepath, other.get("files_claimed", [])):
            return {
                "session_id": other_sid,
                "working_on": other.get("working_on", []),
                "description": other.get("description", ""),
                "started": other.get("started", ""),
            }
    return None


def check_conflicts() -> list[dict]:
    """current sessionclaimsessionclaimreturn."""
    sid = _get_session_id()
    data = _load_locks()
    _cleanup_stale(data)

    if sid not in data["sessions"]:
        print("  current sessionclaim not found")
        return []

    my_patterns = data["sessions"][sid].get("files_claimed", [])
    conflicts = []

    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        overlaps = _patterns_overlap(my_patterns, other.get("files_claimed", []))
        if overlaps:
            conflicts.append({
                "session_id": other_sid,
                "working_on": other.get("working_on", []),
                "overlaps": overlaps,
            })

    if conflicts:
        print(f"  [WARNING] {len(conflicts)}session:")
        for c in conflicts:
            print(f"    - {c['session_id']} ({', '.join(c['working_on'])})")
            for o in c["overlaps"]:
                print(f"      {o}")
    else:
        print("  not found")

    return conflicts


def heartbeat(description: str = "") -> None:
    """session heartbeat update. 30 mincall ."""
    sid = _get_session_id()
    data = _load_locks()

    if sid in data["sessions"]:
        data["sessions"][sid]["last_heartbeat"] = _now_iso()
        if description:
            data["sessions"][sid]["description"] = description
        _save_locks(data)


def release(project: str | None = None) -> None:
    """current sessionclaim. project project."""
    sid = _get_session_id()
    data = _load_locks()

    if sid not in data["sessions"]:
        print("  current sessionclaim not found")
        return

    if project is None:
        # total
        del data["sessions"][sid]
        _save_locks(data)
        print(f"  [RELEASED] session {sid} total ")
    else:
        session = data["sessions"][sid]
        # project remove
        session["working_on"] = [
            p for p in session["working_on"]
            if p.upper() != project.upper()
        ]
        # project pattern remove
        project_patterns = set(_get_project_patterns(project))
        session["files_claimed"] = [
            p for p in session["files_claimed"]
            if p not in project_patterns
        ]
        # session delete
        if not session["working_on"] and not session["files_claimed"]:
            del data["sessions"][sid]
        _save_locks(data)
        print(f"  [RELEASED] {project} from session {sid}")


def list_sessions() -> None:
    """active session listoutput."""
    data = _load_locks()
    removed = _cleanup_stale(data)
    if removed:
        _save_locks(data)
        print(f"  [stale] expiredsession {len(removed)}clean up")

    sessions = data.get("sessions", {})
    if not sessions:
        print("  active session not found (claimproject not found)")
        return

    print(f"\n  === active session {len(sessions)}===\n")
    for sid, s in sessions.items():
        projects = ", ".join(s.get("working_on", [])) or "(not found)"
        desc = s.get("description", "")
        started = s.get("started", "?")[:16]
        hb = s.get("last_heartbeat", "?")[:16]
        print(f"  [{sid}]")
        print(f"    project: {projects}")
        if desc:
            print(f"    : {desc}")
        print(f"    start: {started}  heartbeat: {hb}")
        claimed = s.get("files_claimed", [])
        if claimed:
            print(f"    claimed ({len(claimed)}):")
            for p in claimed[:10]:
                print(f"      - {p}")
            if len(claimed) > 10:
                print(f"      ... (+{len(claimed)-10})")
        print()


def sync_working_md() -> None:
    """WORKING.md[SESSIONS] auto update. existing content."""
    data = _load_locks()
    _cleanup_stale(data)
    sessions = data.get("sessions", {})

    working_md = HANBEEN / ".claude" / "WORKING.md"
    if not working_md.exists():
        return

    content = working_md.read_text(encoding="utf-8")

    # [SESSIONS] create
    section = f"\n## [SESSIONS] active claim ({_now_iso()[:16]})\n\n"
    if sessions:
        for sid, s in sessions.items():
            projects = ", ".join(s.get("working_on", []))
            started = s.get("started", "?")[:16]
            hb = s.get("last_heartbeat", "?")[:16]
            desc = s.get("description", "")
            section += f"### [{sid}] {projects} ({started}~ hb:{hb})\n"
            if desc:
                section += f"- {desc}\n"
            claimed = s.get("files_claimed", [])
            if claimed:
                section += f"- claimed: {', '.join(claimed[:5])}\n"
            section += "\n"
    else:
        section += "active claim not found\n\n"

    # [SESSIONS]
    pattern = r'\n## \[SESSIONS\][^\n]*\n(?:(?!\n## [^[]).)*'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, section, content, count=1, flags=re.DOTALL)
    else:
        # *update:
        if "*update:" in content:
            content = content.replace(
                "\n*update:",
                section + "*update:",
            )
        else:
            content += section

    working_md.write_text(content, encoding="utf-8")


# ─── CLI ─────────────────────────────────────────────────────────


def cli_main(args: list[str]) -> None:
    """CLI . t9_seed.pycall."""
    if not args:
        print("  use:")
        print("    claim <project> [description]  — project claim")
        print("    claim-file <path>              — file claim")
        print("    check <path>                   — file conflict check")
        print("    check-conflicts                — total check")
        print("    sessions                       — active session list")
        print("    release [project]              — release claim")
        print("    heartbeat [description]        — heartbeat update")
        return

    cmd = args[0]
    if cmd == "claim" and len(args) >= 2:
        desc = " ".join(args[2:]) if len(args) > 2 else ""
        claim_project(args[1], desc)
        sync_working_md()
    elif cmd == "claim-file" and len(args) >= 2:
        claim_file(args[1])
        sync_working_md()
    elif cmd == "check" and len(args) >= 2:
        result = check_file(args[1])
        if result:
            print(f"  [BLOCKED] {args[1]} -> session {result['session_id']} ({', '.join(result['working_on'])})")
        else:
            print(f"  [OK] {args[1]} -> claim not found, modify ")
    elif cmd == "check-conflicts":
        check_conflicts()
    elif cmd == "sessions":
        list_sessions()
    elif cmd == "release":
        project = args[1] if len(args) > 1 else None
        release(project)
        sync_working_md()
    elif cmd == "heartbeat":
        desc = " ".join(args[1:]) if len(args) > 1 else ""
        heartbeat(desc)
    else:
        print(f"  unknown command: {cmd}")


if __name__ == "__main__":
    import sys
    cli_main(sys.argv[1:])
