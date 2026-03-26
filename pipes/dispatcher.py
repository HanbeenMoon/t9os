#!/usr/bin/env python3
"""T9 OS 세션 디스패처 — 멀티프로젝트 자동 배분 + 세션 spawn

국가 3요소 통합:
- 통치: L1 헌법이 최상위. 세션 간 위계 없음.
- 제도: dispatch → claim → 작업 → release → ADR 기록
- 시장: 이행 시 지분 +30, 부당 거부 시 부채 -30

사용법:
    python3 dispatcher.py dispatch "SSK 피드백 반영"       # 자동 배분
    python3 dispatcher.py spawn "T9OS" "벡터 임베딩 구현"   # 새 세션 생성
    python3 dispatcher.py status                           # 전체 현황
    python3 dispatcher.py capacity <session_id> <full|partial|idle>
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import DB_PATH
from lib.ipc import (
    _db, _now, _save_msg_file, heartbeat_who,
    IPC_INBOX, HEARTBEATS_FILE
)

import sqlite3

T9 = Path(__file__).resolve().parent.parent
HANBEEN = T9.parent

# 프로젝트 정의: config/projects.json 단일 소스 (구체화 수렴점)
PROJECTS_JSON = T9 / "config" / "projects.json"

def _load_projects() -> dict:
    """projects.json에서 프로젝트 정의 로드."""
    if PROJECTS_JSON.exists():
        try:
            return json.loads(PROJECTS_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _get_project_keywords() -> dict:
    """프로젝트별 키워드 패턴 반환."""
    projects = _load_projects()
    return {name: info.get("keywords", []) for name, info in projects.items()}

def _get_tier1() -> set:
    projects = _load_projects()
    return {name for name, info in projects.items() if info.get("tier") == 1}

TIER1 = _get_tier1() or {"T9", "SSK", "ODNAR"}

MAX_SESSIONS = 5  # dv 조언: 훅 프리징 방지


def classify_project(text: str) -> str:
    """텍스트에서 프로젝트를 자동 분류. projects.json 단일 소스."""
    text_lower = text.lower()
    keywords = _get_project_keywords()
    scores = {}
    for project, kw_list in keywords.items():
        score = 0
        for kw in kw_list:
            matches = re.findall(kw, text_lower)
            score += len(matches)
        if score > 0:
            scores[project] = score

    if not scores:
        return "T9"  # 기본값: T9OS 인프라

    return max(scores, key=scores.get)


def get_active_sessions() -> list[dict]:
    """활성 세션 목록 (DB + heartbeat 통합)."""
    conn = _db()
    rows = conn.execute(
        "SELECT id, pid, claimed_project, capacity, working_on FROM sessions WHERE status='active'"
    ).fetchall()
    conn.close()

    # heartbeat 기반 보강
    hb_alive = {s["session_id"] for s in heartbeat_who()}

    sessions = []
    for r in rows:
        sessions.append({
            "id": r[0],
            "pid": r[1],
            "project": r[2] or "",
            "capacity": r[3] or "idle",
            "working_on": r[4] or "",
            "heartbeat_alive": r[0] in hb_alive or any(r[0][:8] in s for s in hb_alive),
        })

    return sessions


def find_best_session(project: str, sessions: list[dict]) -> dict | None:
    """프로젝트에 가장 적합한 세션 찾기."""
    # 1. 이미 해당 프로젝트를 claim한 세션
    for s in sessions:
        if s["project"].upper() == project.upper() and s["capacity"] != "full":
            return s

    # 2. idle 세션
    for s in sessions:
        if s["capacity"] == "idle" and s["heartbeat_alive"]:
            return s

    # 3. partial 세션 (Tier1 프로젝트가 아닌 것을 담당 중)
    for s in sessions:
        if s["capacity"] == "partial" and s["heartbeat_alive"]:
            if s["project"].upper() not in {t.upper() for t in TIER1}:
                return s

    return None  # spawn 필요


def dispatch(task_text: str, priority: str = "normal") -> str:
    """작업을 적절한 세션에 배분."""
    project = classify_project(task_text)
    sessions = get_active_sessions()

    # 마감일 키워드 확인 → priority 자동 상승
    if re.search(r'마감|deadline|긴급|D-\d|급해|지금', task_text, re.IGNORECASE):
        priority = "critical"

    target = find_best_session(project, sessions)

    if target:
        # T2 사후보고: 기존 세션에 배분 → 알아서 하고 브리프에 보고
        _save_msg_file(
            "dispatcher",
            target["id"],
            "dispatch",
            f"작업배분_{project}",
            f"디스패처 자동 배분.\n프로젝트: {project}\n작업: {task_text}\n우선순위: {priority}",
            priority
        )

        # DB 갱신
        conn = _db()
        conn.execute(
            "UPDATE sessions SET claimed_project=?, capacity='partial' WHERE id=?",
            (project, target["id"])
        )
        conn.commit()
        conn.close()

        result = f"[DISPATCH·T2] {project} → 세션 {target['id'][:16]} (기존)"
        print(f"  {result}")
        return result

    else:
        # 새 세션 spawn 필요
        if len(sessions) >= MAX_SESSIONS:
            # T3 사전승인: 상한 초과 — 한빈 판단 필요
            _save_msg_file(
                "dispatcher",
                "all",
                "escalation",
                f"세션상한초과_{project}",
                f"활성 세션 {len(sessions)}개 (상한 {MAX_SESSIONS}). "
                f"새 세션 spawn 불가. 작업: {task_text}. "
                f"여유 세션이 완료 후 처리하거나 한빈이 판단.",
                "critical"
            )
            result = f"[ESCALATION·T3] 세션 상한 초과. {project} 배분 보류."
            print(f"  {result}")
            _tg_notify(f"⚠️ 세션 상한 초과: {project} — {task_text[:50]}")
            return result

        # T3 사전승인: spawn은 한빈에게 물어본다
        print(f"  [T3·사전승인] 새 세션 spawn 필요: {project} — {task_text[:50]}")
        print(f"  여유 세션이 없어서 새 세션을 만들어야 합니다. 진행할까요?")
        return f"[SPAWN_PENDING·T3] {project} — 한빈 승인 대기"


def spawn_session(project: str, task_text: str, priority: str = "normal") -> str:
    """새 Claude Code 세션을 백그라운드로 spawn."""
    prompt = f"""T9OS 디스패처 자동 배분.
프로젝트: {project}
작업: {task_text}
우선순위: {priority}

규칙:
1. .mcp.json 로드됨 — t9-ipc Channel 서버 활성. 세션 시작 시 t9_ipc_set_name 호출.
2. 작업 시작 전 claim: python3 T9OS/pipes/session_lock.py claim {project}
3. 완료 후 inbox에 완료 보고 + release.
4. L1 헌법 준수 필수. CLAUDE.md 읽고 시작.
5. 다른 세션 메시지 확인: T9OS/data/ipc/inbox/
"""

    cmd = [
        "claude", "-p", prompt,
        "--allowedTools", "Edit,Write,Read,Bash,Glob,Grep",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(HANBEEN),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # 부모 프로세스와 분리
        )

        result = f"[SPAWN] {project} → PID {proc.pid}"
        print(f"  {result}")

        # dispatch 메시지도 남김 (truth)
        _save_msg_file(
            "dispatcher",
            "all",
            "broadcast",
            f"세션spawn_{project}",
            f"디스패처가 새 세션을 spawn했습니다.\n프로젝트: {project}\n작업: {task_text}\nPID: {proc.pid}",
            priority
        )

        return result

    except FileNotFoundError:
        result = "[ERROR] claude 명령어 없음. PATH 확인 필요."
        print(f"  {result}")
        return result
    except Exception as e:
        result = f"[ERROR] spawn 실패: {e}"
        print(f"  {result}")
        return result


def set_capacity(session_id: str, capacity: str) -> str:
    """세션 여유도 설정."""
    if capacity not in ("full", "partial", "idle"):
        return f"[ERROR] capacity는 full/partial/idle 중 하나"

    conn = _db()
    conn.execute(
        "UPDATE sessions SET capacity=? WHERE id LIKE ?",
        (capacity, f"{session_id}%")
    )
    conn.commit()
    conn.close()

    result = f"[CAPACITY] {session_id} → {capacity}"
    print(f"  {result}")
    return result


def status() -> str:
    """전체 디스패처 현황."""
    sessions = get_active_sessions()
    inbox_count = len(list(IPC_INBOX.glob("*.md")))

    lines = [f"\n  === 디스패처 현황 ({_now()}) ===\n"]
    lines.append(f"  활성 세션: {len(sessions)}/{MAX_SESSIONS}")
    lines.append(f"  inbox 메시지: {inbox_count}건")

    if sessions:
        lines.append("")
        for s in sessions:
            hb = "🟢" if s["heartbeat_alive"] else "🔴"
            cap = {"full": "🔴full", "partial": "🟡partial", "idle": "🟢idle"}.get(s["capacity"], s["capacity"])
            proj = s["project"] or "(미배정)"
            lines.append(f"  {hb} [{s['id'][:16]}] {cap} — {proj}")
    else:
        lines.append("  활성 세션 없음")

    # 미처리 dispatch
    dispatch_files = [f for f in IPC_INBOX.glob("*.md") if "dispatch" in f.name.lower()]
    if dispatch_files:
        lines.append(f"\n  미처리 dispatch: {len(dispatch_files)}건")

    output = "\n".join(lines)
    print(output)
    return output


def _tg_notify(msg: str):
    """텔레그램 escalation 알림 (non-blocking)."""
    try:
        tg_common = T9 / "pipes" / "tg_common.py"
        if tg_common.exists():
            subprocess.Popen(
                ["python3", "-c", f"""
import sys; sys.path.insert(0, '{T9}')
from pipes.tg_common import send_message
send_message('{msg}')
"""],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


# ─── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  dispatcher.py dispatch <작업 텍스트>")
        print("  dispatcher.py spawn <프로젝트> <작업>")
        print("  dispatcher.py status")
        print("  dispatcher.py capacity <session_id> <full|partial|idle>")
        print("  dispatcher.py classify <텍스트>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "dispatch" and len(sys.argv) >= 3:
        task = " ".join(sys.argv[2:])
        dispatch(task)

    elif cmd == "spawn" and len(sys.argv) >= 4:
        project = sys.argv[2]
        task = " ".join(sys.argv[3:])
        spawn_session(project, task)

    elif cmd == "status":
        status()

    elif cmd == "capacity" and len(sys.argv) >= 4:
        set_capacity(sys.argv[2], sys.argv[3])

    elif cmd == "classify" and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
        project = classify_project(text)
        print(f"  분류 결과: {project}")

    else:
        print(f"  알 수 없는 명령: {cmd}")
        sys.exit(1)
