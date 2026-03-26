"""
T9 OS Seed — 대형 커맨드 함수 분리 모듈
cmd_daily, cmd_tidy, cmd_compose, cmd_approve + 헬퍼
t9_seed.py 1000줄 상한 준수를 위해 추출됨
"""
import json, shutil, re
from datetime import datetime, timedelta
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
FIELD = T9 / "field" / "inbox"
ACTIVE = T9 / "spaces" / "active"


def _parse_deadlines(find_deadline_file_fn):
    """마감일 파싱. 여러 후보 경로에서 파일을 찾고, 없으면 빈 리스트 반환."""
    deadline_file = find_deadline_file_fn()
    if not deadline_file:
        return []
    try:
        blocks = deadline_file.read_text(encoding="utf-8", errors="replace").split("===")
    except Exception:
        return []
    deadlines, today = [], datetime.now().date()
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        d = {}
        for line in block.split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                d[k.strip()] = v.strip()
        if "날짜" in d and "제목" in d:
            try:
                days = (datetime.strptime(d["날짜"], "%Y-%m-%d").date() - today).days
                if -1 <= days <= 14:
                    deadlines.append({"title": d["제목"], "date": d["날짜"], "days": days, "urgent": d.get("긴급", "N") == "Y"})
            except ValueError:
                pass
    return sorted(deadlines, key=lambda x: x["days"])


def _show_calendar_events(now):
    """field/inbox에서 오늘자 GoogleCalendar MD를 읽어 일정 표시."""
    cal_files = sorted(FIELD.glob(f"{now:%Y%m%d}_GoogleCalendar_*.md"))
    if not cal_files:
        return
    try:
        lines = [l for l in cal_files[-1].read_text(encoding="utf-8", errors="replace").split("\n") if l.startswith("- [")]
        if lines:
            print(f"  [캘린더] 일정 ({len(lines)}건):")
            for l in lines[:8]:
                print(f"    {l[2:]}")
            print()
    except Exception:
        pass


def cmd_daily(get_db, find_deadline_file_fn):
    """일일 브리프: 마감일 + individuating/tension 수 + 전도적 학습 제안."""
    conn = get_db()
    now = datetime.now()
    print(f"\n  === T9 OS Seed v0.2 -- {now:%Y-%m-%d %A} ===\n")

    dl = _parse_deadlines(find_deadline_file_fn)
    if dl:
        print("  [!] 마감일:")
        for d in dl:
            lbl = {-1: "어제!", 0: "오늘!", 1: "내일"}.get(d["days"], f"D-{d['days']}")
            print(f"    {lbl:6s} {d['date']} {d['title']}{' *긴급*' if d['urgent'] else ''}")
        print()
    else:
        print("  [마감일] 파일 없음 또는 임박한 마감 없음\n")

    _show_calendar_events(now)

    urgent = conn.execute(
        "SELECT id,filename FROM entities WHERE phase NOT IN ('archived','sediment','dissolved') "
        "AND urgency='high'"
    ).fetchall()
    if urgent:
        print(f"  [!!] 긴급 ({len(urgent)}건):")
        for r in urgent:
            print(f"    [{r['id']}] {r['filename'][:50]}")
        print()

    active = conn.execute("SELECT id,filename FROM entities WHERE phase IN ('individuating','stabilized')").fetchall()
    if active:
        print(f"  진행 중 ({len(active)}건):")
        for r in active:
            print(f"    [{r['id']}] {r['filename'][:50]}")
        print()

    ind_cnt = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='individuating'").fetchone()["c"]
    stab_cnt = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='stabilized'").fetchone()["c"]
    pre = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='preindividual'").fetchone()["c"]
    tens = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='tension_detected'").fetchone()["c"]
    imp = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='impulse'").fetchone()["c"]
    sed = conn.execute("SELECT COUNT(*) as c FROM entities WHERE phase='sediment'").fetchone()["c"]
    print(f"  전개체: {pre}건 | 충동: {imp}건 | 긴장: {tens}건 | 개체화: {ind_cnt}건 | 안정: {stab_cnt}건")
    if sed > 0:
        print(f"  (침전: {sed}건 — 지층에 가라앉은 전개체, 검색으로 발굴 가능)")

    stale = conn.execute("SELECT id,filename FROM entities WHERE phase='suspended' AND updated_at<? LIMIT 5",
                         ((now - timedelta(days=30)).strftime("%Y-%m-%d"),)).fetchall()
    if stale:
        print(f"\n  [?] 30일+ 중단:")
        for r in stale:
            print(f"    [{r['id']}] {r['filename'][:50]}")

    recent_archived = conn.execute(
        "SELECT id,filename,concepts,metadata FROM entities "
        "WHERE phase='archived' AND updated_at>=? ORDER BY updated_at DESC LIMIT 5",
        ((now - timedelta(days=14)).strftime("%Y-%m-%d"),)
    ).fetchall()
    if recent_archived:
        print(f"\n  [전도적 학습] 최근 아카이브된 엔티티에서 추출 가능한 패턴:")
        for r in recent_archived:
            concepts = []
            if r["concepts"]:
                try:
                    concepts = json.loads(r["concepts"])
                except Exception:
                    pass
            if not concepts:
                m = json.loads(r["metadata"]) if r["metadata"] else {}
                concepts = m.get("concepts", [])
            if concepts:
                print(f"    [{r['id']}] {r['filename'][:40]} → 개념: {', '.join(concepts)}")
                for c in concepts:
                    related = conn.execute(
                        "SELECT id,filename FROM entities WHERE phase IN ('individuating','tension_detected') "
                        "AND (concepts LIKE ? OR metadata LIKE ?) AND id!=? LIMIT 2",
                        (f'%"{c}"%', f'%"{c}"%', r["id"])
                    ).fetchall()
                    if related:
                        for rel in related:
                            print(f"      → [{rel['id']}] {rel['filename'][:40]}에 전도 가능")

    # 침전 resurface: 랜덤 1~2건 표시
    if sed > 0:
        import random
        sed_items = conn.execute(
            "SELECT id,filename,body_preview FROM entities WHERE phase='sediment'"
        ).fetchall()
        if sed_items:
            sample = random.sample(list(sed_items), min(2, len(sed_items)))
            print(f"\n  [발굴] 침전에서 떠오른 전개체:")
            for s in sample:
                preview = (s["body_preview"] or "")[:60].replace("\n", " ")
                print(f"    [{s['id']}] {s['filename'][:45]}")
                if preview:
                    print(f"         {preview}")
            print(f"    → resurface 명령으로 더 탐색 가능")

    conn.close()
    print()


def cmd_tidy(get_db, cmd_transition_fn):
    """주기적 정리: inbox의 phase-directory 불일치 해소 + 30일+ preindividual 침전.
    시몽동 원칙: 전개체는 삭제되지 않는다. 침전(sediment)으로 가라앉을 뿐."""
    conn = get_db()
    now = datetime.now()
    moved = []
    sedimented = []

    # 1. stabilized가 inbox에 있으면 → archived
    stab_inbox = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='stabilized' AND filepath LIKE 'field/inbox%'"
    ).fetchall()
    conn.close()
    for ent in stab_inbox:
        name = ent["filename"].replace(".md", "")[:40]
        cmd_transition_fn(ent["id"], "archived", "tidy: stabilized→archived 자동정리")
        moved.append(f"  `{name}` → archived")

    # 2. individuating가 inbox에 있으면 → active로 파일 이동
    conn = get_db()
    ind_inbox = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='individuating' AND filepath LIKE 'field/inbox%'"
    ).fetchall()
    for ent in ind_inbox:
        old_path = T9 / ent["filepath"]
        if not old_path.exists():
            continue
        ACTIVE.mkdir(parents=True, exist_ok=True)
        new_path = ACTIVE / old_path.name
        if not new_path.exists():
            shutil.move(str(old_path), str(new_path))
            new_rel = str(new_path.relative_to(T9))
            conn.execute("UPDATE entities SET filepath=?, updated_at=? WHERE id=?",
                         (new_rel, now.isoformat(), ent["id"]))
            name = ent["filename"].replace(".md", "")[:40]
            moved.append(f"  `{name}` → active")

    # 3. 30일+ preindividual → sediment (침전: 삭제 아닌 가라앉음)
    stale_cutoff = (now - timedelta(days=30)).isoformat()
    stale_pre = conn.execute(
        "SELECT id, filename, filepath FROM entities "
        "WHERE phase='preindividual' AND updated_at < ? AND filepath LIKE 'field/inbox%'",
        (stale_cutoff,)
    ).fetchall()
    conn.close()
    for ent in stale_pre:
        name = ent["filename"].replace(".md", "")[:40]
        cmd_transition_fn(ent["id"], "sediment", "tidy: 30일+ 전개체 → 침전 (지층으로 가라앉음)")
        sedimented.append(f"  `{name}`")

    # 4. 출력
    print(f"\n  === T9 Tidy ({now:%Y-%m-%d %H:%M}) ===")
    print(f"  이동: {len(moved)}건, 침전: {len(sedimented)}건")
    for m in moved:
        print(m)
    for s in sedimented:
        print(f"  [침전] {s}")
    if not moved and not sedimented:
        print("  정리할 항목 없음")

    # 5. 텔레그램 보고 (변동 있을 때만)
    if moved or sedimented:
        try:
            import sys as _sys
            _sys.path.insert(0, str(T9 / "pipes"))
            from tg_common import tg_send
            lines = [f"T9 Tidy — {now:%m/%d %H:%M}"]
            if moved:
                lines.append(f"\n이동 {len(moved)}건:")
                lines.extend(moved[:10])
            if sedimented:
                lines.append(f"\n침전 {len(sedimented)}건 (지층으로 가라앉음):")
                lines.extend(sedimented[:10])
            tg_send("\n".join(lines))
        except Exception as e:
            print(f"  [알림실패] {e}")


def cmd_compose(text, extract_concepts_fn, detect_urgency_fn, detect_tension_fn):
    """동적 플랜 생성. concepts/urgency/disparation에 기반하여 적응적으로 생성."""
    concepts, urgency = extract_concepts_fn(text), detect_urgency_fn(text)
    has_tension, dim_a, dim_b = detect_tension_fn(text)

    print(f"\n  === T9 Composer v0.2 ===")
    print(f"  입력: {text}")
    print(f"  개념: {', '.join(concepts) or '(자유)'}  긴급: {urgency}")
    if has_tension:
        print(f"  긴장: {dim_a} vs {dim_b}")
    print()

    plans = []

    if urgency == "high":
        plans.append({"id": "A", "name": "즉시 실행 (최소 경로)",
                       "steps": ["1. 핵심 산출물만 30분 내 완성", "2. 검증 없이 배포", "3. 사후 보완"],
                       "time": "30분", "tool": "cc"})
    else:
        plans.append({"id": "A", "name": "직접 실행 (표준 경로)",
                       "steps": ["1. 기존 자원 확인", "2. 핵심 산출물 작성", "3. 검증 후 완료"],
                       "time": "1시간", "tool": "cc"})

    if "explore" in concepts or "become" in concepts:
        plans.append({"id": "B", "name": "탐색-학습 루프",
                       "steps": ["1. 3가지 소스 수집 (gm 병렬)", "2. 핵심 인사이트 추출", "3. 적용 가능 패턴 도출"],
                       "time": "1.5시간", "tool": "gm+cc"})
    elif "create" in concepts or "solve" in concepts:
        plans.append({"id": "B", "name": "분할 병렬 실행",
                       "steps": ["1. 하위 작업 분할", "2. cc/cx 병렬 배분", "3. 통합 및 검증"],
                       "time": "1시간", "tool": "cc+cx"})
    elif "earn" in concepts:
        plans.append({"id": "B", "name": "ROI 우선 실행",
                       "steps": ["1. 비용 대비 효과 산정", "2. 최소 투입 방안 선택", "3. 빠른 검증"],
                       "time": "45분", "tool": "cc"})
    else:
        plans.append({"id": "B", "name": "병렬 분할",
                       "steps": ["1. 하위 작업 분할", "2. cc/cx 병렬 배분", "3. 통합"],
                       "time": "1시간", "tool": "cc+cx"})

    if has_tension:
        plans.append({"id": "C", "name": f"긴장 해소 ({dim_a} vs {dim_b})",
                       "steps": [f"1. {dim_a} 측면 요구사항 정리", f"2. {dim_b} 측면 요구사항 정리",
                                 "3. 양립 가능한 해결책 도출 (transduction)"],
                       "time": "1시간", "tool": "cc"})
    else:
        plans.append({"id": "C", "name": "Buy-first 탐색",
                       "steps": ["1. 기존 서비스/도구 3개 검색", "2. 비용 효과 평가", "3. 선택 및 적용"],
                       "time": "45분", "tool": "gm"})

    for p in plans:
        print(f"  -- Plan {p['id']}: {p['name']} ({p['time']}, {p['tool']}) --")
        for s in p["steps"]:
            print(f"     {s}")
        print()

    cid = f"{datetime.now():%Y%m%d_%H%M%S}"
    cdir = T9 / "data" / "composes"
    cdir.mkdir(parents=True, exist_ok=True)
    compose_data = {
        "id": cid, "text": text, "concepts": concepts, "urgency": urgency,
        "plans": plans, "created": datetime.now().isoformat(), "approved": None,
    }
    if has_tension:
        compose_data["disparation"] = {"dimension_a": dim_a, "dimension_b": dim_b}
    (cdir / f"{cid}.json").write_bytes(json.dumps(compose_data, ensure_ascii=False, indent=2).encode("utf-8"))
    plan_ids = "/".join(p["id"] for p in plans)
    print(f"  Compose ID: {cid}\n  승인: python3 t9_seed.py approve {cid} {plan_ids}\n")


def cmd_approve(cid, choice, self_check_fn, write_md_fn, index_file_fn):
    """플랜 승인 → active 엔티티 생성."""
    cf = T9 / "data" / "composes" / f"{cid}.json"
    if not cf.exists():
        print(f"  ID '{cid}' 없음")
        return
    data = json.loads(cf.read_text(encoding="utf-8"))
    sel = next((p for p in data["plans"] if p["id"] == choice.upper()), None)
    if not sel:
        valid_ids = "/".join(p["id"] for p in data["plans"])
        print(f"  Plan '{choice}' 없음 (유효: {valid_ids})")
        return
    now = datetime.now()
    safe = re.sub(r'[^\w\s가-힣]', '', data["text"][:30]).strip()
    fp = ACTIVE / f"{now:%Y%m%d}_{safe}_{now:%H%M%S}.md"
    ACTIVE.mkdir(parents=True, exist_ok=True)
    meta = {"phase": "individuating", "created": f"{now:%Y-%m-%d %H:%M}", "concepts": data.get("concepts", []),
            "urgency": data.get("urgency", "mid"), "compose_id": cid, "plan": choice.upper()}
    if data.get("disparation"):
        meta["disparation"] = data["disparation"]
    body = f"# {data['text']}\n\n## Plan {sel['id']}: {sel['name']}\n\n" + "".join(f"- [ ] {s}\n" for s in sel["steps"])
    self_check_fn("approve", meta)
    write_md_fn(fp, meta, body)
    index_file_fn(fp)
    data["approved"] = {"plan": choice.upper(), "timestamp": now.isoformat()}
    cf.write_bytes(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    print(f"  승인: Plan {choice.upper()}, 생성: {fp.name}\n")
