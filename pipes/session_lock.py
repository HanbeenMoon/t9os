"""T9 OS Session Lock — 프로젝트/파일 단위 충돌 방지

세션 간 같은 파일을 모르고 건드리는 문제를 해결한다.
- project claim: 프로젝트 이름으로 관련 파일 패턴 일괄 claim
- file claim: 개별 파일/패턴 claim
- conflict check: 수정 전 다른 세션 claim 여부 확인
- heartbeat: 30분 무응답 시 자동 만료
- JSON sync: .session_locks.json에 사람이 읽을 수 있는 상태 기록

stdlib만 사용. 단일 파일. 경로 하드코딩 금지.
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

# 프로젝트 → 파일 패턴 매핑 (소프트코딩: JSON 설정 파일에서 오버라이드 가능)
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
    """현재 세션 ID를 읽는다. 없으면 PID 기반으로 생성."""
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text().strip()
    return f"unknown_{os.getpid()}"


def _load_locks() -> dict:
    """JSON 잠금 파일을 읽는다. 없으면 빈 구조."""
    if LOCKS_JSON.exists():
        try:
            return json.loads(LOCKS_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"sessions": {}}


def _save_locks(data: dict) -> None:
    """JSON 잠금 파일에 쓴다."""
    LOCKS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _is_stale(session: dict) -> bool:
    """heartbeat가 HEARTBEAT_TIMEOUT_MIN 이상 지났으면 stale."""
    hb = session.get("last_heartbeat", session.get("started", ""))
    if not hb:
        return True
    try:
        last = datetime.fromisoformat(hb)
        return (datetime.now() - last) > timedelta(minutes=HEARTBEAT_TIMEOUT_MIN)
    except ValueError:
        return True


def _cleanup_stale(data: dict) -> list[str]:
    """stale 세션을 제거하고 제거된 세션 ID 리스트를 반환."""
    removed = []
    for sid in list(data["sessions"].keys()):
        if _is_stale(data["sessions"][sid]):
            removed.append(sid)
            del data["sessions"][sid]
    return removed


def _get_project_patterns(project: str) -> list[str]:
    """프로젝트에 해당하는 파일 패턴을 반환. 커스텀 설정 파일 우선."""
    custom_path = T9 / "config" / "project_patterns.json"
    patterns = dict(_DEFAULT_PROJECT_PATTERNS)
    if custom_path.exists():
        try:
            custom = json.loads(custom_path.read_text(encoding="utf-8"))
            patterns.update(custom)
        except (json.JSONDecodeError, OSError):
            pass
    # 대소문자 무시 매칭
    for key in patterns:
        if key.upper() == project.upper():
            return patterns[key]
    # 매칭 안 되면 PROJECTS/<project>/* 기본 패턴
    return [f"PROJECTS/{project}/*", f"T9OS/artifacts/{project.lower()}_*/*"]


def _patterns_overlap(patterns_a: list[str], patterns_b: list[str]) -> list[str]:
    """두 패턴 집합이 겹치는 패턴을 반환.
    정확한 파일 패턴끼리만 비교한다. 디렉토리 패턴은 같은 디렉토리인지만 확인."""
    overlaps = []
    for pa in patterns_a:
        for pb in patterns_b:
            if pa == pb:
                overlaps.append(pa)
                continue
            # 구체적 파일 경로가 다른 쪽 패턴에 매칭되는지
            if not pa.endswith("*") and _file_matches_patterns(pa, [pb]):
                overlaps.append(f"{pa} <-> {pb}")
            elif not pb.endswith("*") and _file_matches_patterns(pb, [pa]):
                overlaps.append(f"{pa} <-> {pb}")
            # 디렉토리 glob끼리는 정확히 같은 디렉토리 prefix일 때만
            elif pa.endswith("/*") and pb.endswith("/*"):
                pa_dir = pa[:-2]
                pb_dir = pb[:-2]
                # 정확히 같거나, 한쪽이 다른 쪽의 하위인 경우
                if pa_dir == pb_dir:
                    overlaps.append(pa)
                elif pa_dir.startswith(pb_dir + "/") or pb_dir.startswith(pa_dir + "/"):
                    overlaps.append(f"{pa} <-> {pb}")
    return overlaps


def _file_matches_patterns(filepath: str, patterns: list[str]) -> bool:
    """파일 경로가 패턴 리스트 중 하나와 매칭되는지 확인."""
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # 디렉토리 패턴 (끝이 /*)인 경우, 하위 경로도 매칭
        if pattern.endswith("/*") and filepath.startswith(pattern[:-2]):
            return True
    return False


# ─── 핵심 API ────────────────────────────────────────────────────


def claim_project(project: str, description: str = "") -> bool:
    """프로젝트를 현재 세션에 claim. 충돌 시 False 반환."""
    sid = _get_session_id()
    data = _load_locks()
    removed = _cleanup_stale(data)
    if removed:
        print(f"  [stale] 만료된 세션 {len(removed)}개 정리: {', '.join(removed)}")

    patterns = _get_project_patterns(project)

    # 다른 세션과 충돌 검사
    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        other_patterns = other.get("files_claimed", [])
        overlaps = _patterns_overlap(patterns, other_patterns)
        if overlaps:
            other_projects = ", ".join(other.get("working_on", []))
            print(f"  [CONFLICT] {project} 패턴이 세션 {other_sid} ({other_projects})와 충돌:")
            for o in overlaps:
                print(f"    - {o}")
            print(f"  -> 해당 세션이 release할 때까지 대기하거나 수동 조율 필요")
            return False

    # claim 등록
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
    # 패턴 추가 (중복 제거)
    for p in patterns:
        if p not in session["files_claimed"]:
            session["files_claimed"].append(p)
    if description:
        session["description"] = description
    session["last_heartbeat"] = now

    _save_locks(data)
    print(f"  [CLAIMED] {project} -> 세션 {sid}")
    print(f"    패턴: {', '.join(patterns)}")
    return True


def claim_file(filepath: str) -> bool:
    """개별 파일/패턴을 현재 세션에 claim."""
    sid = _get_session_id()
    data = _load_locks()
    _cleanup_stale(data)

    # 다른 세션 충돌 검사
    for other_sid, other in data["sessions"].items():
        if other_sid == sid:
            continue
        if _file_matches_patterns(filepath, other.get("files_claimed", [])):
            other_projects = ", ".join(other.get("working_on", []))
            print(f"  [CONFLICT] {filepath} -> 세션 {other_sid} ({other_projects})가 이미 claim 중")
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
    print(f"  [CLAIMED] {filepath} -> 세션 {sid}")
    return True


def check_file(filepath: str) -> dict | None:
    """파일 수정 전 호출. 다른 세션이 claim 중이면 해당 세션 정보 반환."""
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
    """현재 세션의 claim과 다른 세션의 claim이 겹치는 것을 모두 반환."""
    sid = _get_session_id()
    data = _load_locks()
    _cleanup_stale(data)

    if sid not in data["sessions"]:
        print("  현재 세션에 claim 없음")
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
        print(f"  [WARNING] {len(conflicts)}개 세션과 충돌 가능:")
        for c in conflicts:
            print(f"    - {c['session_id']} ({', '.join(c['working_on'])})")
            for o in c["overlaps"]:
                print(f"      {o}")
    else:
        print("  충돌 없음")

    return conflicts


def heartbeat(description: str = "") -> None:
    """세션 heartbeat 갱신. 30분마다 호출 권장."""
    sid = _get_session_id()
    data = _load_locks()

    if sid in data["sessions"]:
        data["sessions"][sid]["last_heartbeat"] = _now_iso()
        if description:
            data["sessions"][sid]["description"] = description
        _save_locks(data)


def release(project: str | None = None) -> None:
    """현재 세션의 claim을 해제. project 지정 시 해당 프로젝트만."""
    sid = _get_session_id()
    data = _load_locks()

    if sid not in data["sessions"]:
        print("  현재 세션에 claim 없음")
        return

    if project is None:
        # 전체 해제
        del data["sessions"][sid]
        _save_locks(data)
        print(f"  [RELEASED] 세션 {sid} 전체 해제")
    else:
        session = data["sessions"][sid]
        # 프로젝트 제거
        session["working_on"] = [
            p for p in session["working_on"]
            if p.upper() != project.upper()
        ]
        # 해당 프로젝트 패턴 제거
        project_patterns = set(_get_project_patterns(project))
        session["files_claimed"] = [
            p for p in session["files_claimed"]
            if p not in project_patterns
        ]
        # 아무것도 안 남으면 세션 자체 삭제
        if not session["working_on"] and not session["files_claimed"]:
            del data["sessions"][sid]
        _save_locks(data)
        print(f"  [RELEASED] {project} from 세션 {sid}")


def list_sessions() -> None:
    """활성 세션 목록을 출력."""
    data = _load_locks()
    removed = _cleanup_stale(data)
    if removed:
        _save_locks(data)
        print(f"  [stale] 만료된 세션 {len(removed)}개 정리")

    sessions = data.get("sessions", {})
    if not sessions:
        print("  활성 세션 없음 (claim된 프로젝트 없음)")
        return

    print(f"\n  === 활성 세션 {len(sessions)}개 ===\n")
    for sid, s in sessions.items():
        projects = ", ".join(s.get("working_on", [])) or "(없음)"
        desc = s.get("description", "")
        started = s.get("started", "?")[:16]
        hb = s.get("last_heartbeat", "?")[:16]
        print(f"  [{sid}]")
        print(f"    프로젝트: {projects}")
        if desc:
            print(f"    설명: {desc}")
        print(f"    시작: {started}  heartbeat: {hb}")
        claimed = s.get("files_claimed", [])
        if claimed:
            print(f"    claimed ({len(claimed)}):")
            for p in claimed[:10]:
                print(f"      - {p}")
            if len(claimed) > 10:
                print(f"      ... (+{len(claimed)-10}개)")
        print()


def sync_working_md() -> None:
    """WORKING.md의 [SESSIONS] 섹션을 자동 갱신. 기존 내용은 보존."""
    data = _load_locks()
    _cleanup_stale(data)
    sessions = data.get("sessions", {})

    working_md = HANBEEN / ".claude" / "WORKING.md"
    if not working_md.exists():
        return

    content = working_md.read_text(encoding="utf-8")

    # [SESSIONS] 섹션 생성
    section = f"\n## [SESSIONS] 활성 claim ({_now_iso()[:16]})\n\n"
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
        section += "활성 claim 없음\n\n"

    # [SESSIONS] 섹션만 교체
    pattern = r'\n## \[SESSIONS\][^\n]*\n(?:(?!\n## [^[]).)*'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, section, content, count=1, flags=re.DOTALL)
    else:
        # *갱신: 줄 바로 위에 삽입
        if "*갱신:" in content:
            content = content.replace(
                "\n*갱신:",
                section + "*갱신:",
            )
        else:
            content += section

    working_md.write_text(content, encoding="utf-8")


# ─── CLI ─────────────────────────────────────────────────────────


def cli_main(args: list[str]) -> None:
    """CLI 엔트리포인트. t9_seed.py에서 호출."""
    if not args:
        print("  사용법:")
        print("    claim <project> [description]  — 프로젝트 claim")
        print("    claim-file <path>              — 파일 claim")
        print("    check <path>                   — 파일 충돌 확인")
        print("    check-conflicts                — 전체 충돌 확인")
        print("    sessions                       — 활성 세션 목록")
        print("    release [project]              — claim 해제")
        print("    heartbeat [description]        — heartbeat 갱신")
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
            print(f"  [BLOCKED] {args[1]} -> 세션 {result['session_id']} ({', '.join(result['working_on'])})")
        else:
            print(f"  [OK] {args[1]} -> claim 없음, 수정 가능")
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
        print(f"  알 수 없는 명령: {cmd}")


if __name__ == "__main__":
    import sys
    cli_main(sys.argv[1:])
