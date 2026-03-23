#!/usr/bin/env python3
"""t9_auto.py — T9 OS 자동 개체화 엔진.
Gemini Flash를 중간관리자로 쓴다. 판단은 코드, NLP만 Gemini.
cron으로 6시간마다 실행 또는 t9tb에서 /auto로 호출."""
import sqlite3, json, urllib.request, urllib.parse, re, sys, time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GEMINI_KEY, T9, HANBEEN, DB_PATH
from lib.logger import pipeline_run

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send

MODEL = "gemini-3-flash-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_KEY}"

# T9 OS 프로젝트 목록 (코드로 고정 — Gemini한테 이것만 알려줌)
PROJECTS = ["T9", "PROJECT_A", "RESEARCH", "COURSEWORK", "CONTEST", "T9D", "t9tb", "PIPELINE", "LEGACY"]

# 마감/긴급 키워드 (하드 규칙)
URGENT_KEYWORDS = ["마감", "deadline", "급함", "긴급", "D-", "오늘까지", "내일까지", "ASAP", "즉시"]
DEADLINE_PATTERN = re.compile(r'(\d{4})-(\d{2})-(\d{2})')


# ─── Gemini 호출 (단순 NLP만) ───

def gemini_call(prompt, max_tokens=200):
    """Gemini Flash 단일 호출. 실패하면 None."""
    if not GEMINI_KEY:
        print("  [gemini 실패] GEMINI_API_KEY 환경변수 없음")
        return None
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.1,
            "thinkingConfig": {"thinkingBudget": 0},
        }
    }).encode()
    req = urllib.request.Request(API_URL, body, {"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        candidates = data.get("candidates", [])
        if not candidates:
            print(f"  [gemini] 빈 응답")
            return None
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        for part in parts:
            if "text" in part:
                return part["text"].strip()
        print(f"  [gemini] text 없음: {list(content.keys())}")
        return None
    except Exception as e:
        print(f"  [gemini 실패] {e}")
        return None


def gemini_batch(items, prompt_fn, max_tokens=150):
    """여러 항목을 하나의 프롬프트로 묶어서 처리. Batch API 대신 단일 호출로 묶기."""
    if not items:
        return {}
    # 최대 20개씩 묶기
    results = {}
    for i in range(0, len(items), 20):
        chunk = items[i:i + 20]
        prompt = prompt_fn(chunk)
        raw = gemini_call(prompt, max_tokens=max_tokens * len(chunk) // 5)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for idx, item in enumerate(chunk):
                        if idx < len(parsed):
                            results[item["id"]] = parsed[idx]
                elif isinstance(parsed, dict):
                    results.update(parsed)
            except json.JSONDecodeError:
                # 줄 단위 파싱 시도
                lines = [l.strip() for l in raw.split("\n") if l.strip()]
                for idx, item in enumerate(chunk):
                    if idx < len(lines):
                        results[item["id"]] = lines[idx]
        if i + 20 < len(items):
            time.sleep(1)  # rate limit 방지
    return results


# ─── 하드 규칙 (코드) ───

def detect_urgency_hard(text, filename):
    """규칙 기반 urgency 판별"""
    combined = f"{filename} {text}".lower()
    if any(k.lower() in combined for k in URGENT_KEYWORDS):
        return "high"
    # 마감일이 7일 이내면 high
    dates = DEADLINE_PATTERN.findall(combined)
    today = datetime.now().date()
    for y, m, d in dates:
        try:
            dt = datetime(int(y), int(m), int(d)).date()
            delta = (dt - today).days
            if 0 <= delta <= 7:
                return "high"
            elif 7 < delta <= 14:
                return "mid"
        except ValueError:
            pass
    return ""


def detect_project_hard(text, filename):
    """규칙 기반 프로젝트 매칭"""
    combined = f"{filename} {text}".upper()
    for proj in PROJECTS:
        if proj.upper() in combined:
            return proj
    return ""


# should_archive 제거됨 — G2-B 존재론 감시단 VIOLATION
# 전개체의 자동 sediment/archive는 L2 위반. 한빈 수동 검토(consolidate)에서만 처리.


# ─── Gemini 소프트 작업 ───

def extract_concepts_batch(entities):
    """Gemini로 concepts 추출 (배치)"""
    def prompt_fn(chunk):
        items = []
        for e in chunk:
            preview = (e.get("body_preview") or e.get("filename", ""))[:150]
            items.append(f'{e["id"]}: {preview}')
        joined = "\n".join(items)
        return (
            f"각 항목에서 핵심 개념을 2-4개 추출해. JSON 배열로만 답해.\n"
            f"형식: [{{\"id\": N, \"concepts\": [\"개념1\", \"개념2\"]}}, ...]\n"
            f"개념은 한국어, 짧게 (2-4단어).\n\n{joined}"
        )
    raw = gemini_call(prompt_fn(entities), max_tokens=100 * len(entities))
    if not raw:
        return {}
    results = {}
    try:
        # JSON 부분만 추출
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            for item in parsed:
                if isinstance(item, dict) and "id" in item and "concepts" in item:
                    results[item["id"]] = item["concepts"]
    except (json.JSONDecodeError, KeyError):
        pass
    return results


def classify_project_batch(entities):
    """Gemini로 프로젝트 분류 (배치)"""
    def prompt_fn(chunk):
        items = []
        for e in chunk:
            preview = (e.get("body_preview") or e.get("filename", ""))[:100]
            items.append(f'{e["id"]}: {preview}')
        joined = "\n".join(items)
        return (
            f"각 항목이 어떤 프로젝트에 해당하는지 분류해. 프로젝트 목록: {', '.join(PROJECTS)}\n"
            f"해당 없으면 \"none\". JSON 배열로만 답해.\n"
            f"형식: [{{\"id\": N, \"project\": \"프로젝트명\"}}, ...]\n\n{joined}"
        )
    raw = gemini_call(prompt_fn(entities), max_tokens=50 * len(entities))
    if not raw:
        return {}
    results = {}
    try:
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            for item in parsed:
                if isinstance(item, dict) and "id" in item and "project" in item:
                    proj = item["project"]
                    if proj != "none" and proj in PROJECTS:
                        results[item["id"]] = proj
    except (json.JSONDecodeError, KeyError):
        pass
    return results


# ─── 메인 오케스트레이터 ───

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def run_auto(dry_run=False):
    """메인 자동화 루프"""
    conn = get_db()
    now = datetime.now()
    report = {"concepts_added": 0, "urgency_set": 0, "transitioned": 0, "projects_set": 0}

    # ── 1. 미분류 preindividual 수집 ──
    unclassified = conn.execute(
        "SELECT id, filename, filepath, body_preview, created_at, updated_at, "
        "concepts, urgency, metadata, phase "
        "FROM entities WHERE phase = 'preindividual' "
        "AND (concepts IS NULL OR concepts = '' OR concepts = '[]') "
        "ORDER BY created_at DESC LIMIT 40"
    ).fetchall()
    unclassified = [dict(r) for r in unclassified]

    print(f"\n=== t9_auto — {now:%Y-%m-%d %H:%M} ===")
    print(f"  미분류 preindividual: {len(unclassified)}건")

    # ── 2. 하드 규칙 먼저 적용 ──
    hard_updates = []
    for e in unclassified:
        updates = {}
        text = e.get("body_preview") or ""

        # urgency
        if not e.get("urgency"):
            urg = detect_urgency_hard(text, e["filename"])
            if urg:
                updates["urgency"] = urg

        # project (metadata에 저장)
        proj = detect_project_hard(text, e["filename"])
        if proj:
            updates["project"] = proj

        if updates:
            hard_updates.append((e["id"], updates))

    print(f"  하드 규칙 매칭: {len(hard_updates)}건")

    # ── 3. Gemini 소프트 작업 (concepts 추출) ──
    needs_concepts = [e for e in unclassified if not e.get("concepts") or e["concepts"] in ("", "[]")]
    gemini_concepts = {}
    if needs_concepts:
        print(f"  Gemini concepts 요청: {len(needs_concepts)}건...")
        gemini_concepts = extract_concepts_batch(needs_concepts[:20])  # 최대 20개
        print(f"  Gemini concepts 결과: {len(gemini_concepts)}건")

    # ── 4. Gemini 프로젝트 분류 (하드 규칙으로 못 잡은 것만) ──
    hard_project_ids = {eid for eid, u in hard_updates if "project" in u}
    needs_project = [e for e in unclassified[:20] if e["id"] not in hard_project_ids]
    gemini_projects = {}
    if needs_project:
        print(f"  Gemini 프로젝트 분류 요청: {len(needs_project)}건...")
        gemini_projects = classify_project_batch(needs_project)
        print(f"  Gemini 프로젝트 분류 결과: {len(gemini_projects)}건")

    # ── 5. DB 업데이트 ──
    if not dry_run:
        cursor = conn.cursor()

        # 하드 규칙 적용
        for eid, updates in hard_updates:
            if "urgency" in updates:
                cursor.execute("UPDATE entities SET urgency=?, updated_at=? WHERE id=?",
                               (updates["urgency"], now.isoformat(), eid))
                report["urgency_set"] += 1

        # Gemini concepts 적용
        for eid, concepts in gemini_concepts.items():
            if isinstance(concepts, list) and concepts:
                cursor.execute("UPDATE entities SET concepts=?, updated_at=? WHERE id=?",
                               (json.dumps(concepts, ensure_ascii=False), now.isoformat(), eid))
                report["concepts_added"] += 1

        # Gemini 프로젝트 적용 (metadata에 추가)
        for eid, proj in gemini_projects.items():
            row = cursor.execute("SELECT metadata FROM entities WHERE id=?", (eid,)).fetchone()
            try:
                meta = json.loads(row[0]) if row and row[0] else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            meta["project"] = proj
            cursor.execute("UPDATE entities SET metadata=?, updated_at=? WHERE id=?",
                           (json.dumps(meta, ensure_ascii=False), now.isoformat(), eid))
            report["projects_set"] += 1

        # 하드 규칙 프로젝트도 metadata에
        for eid, updates in hard_updates:
            if "project" in updates:
                row = cursor.execute("SELECT metadata FROM entities WHERE id=?", (eid,)).fetchone()
                try:
                    meta = json.loads(row[0]) if row and row[0] else {}
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                meta["project"] = updates["project"]
                cursor.execute("UPDATE entities SET metadata=?, updated_at=? WHERE id=?",
                               (json.dumps(meta, ensure_ascii=False), now.isoformat(), eid))
                report["projects_set"] += 1

        # urgency=high → tension_detected 자동 전이
        high_pre = cursor.execute(
            "SELECT id FROM entities WHERE phase='preindividual' AND urgency='high'"
        ).fetchall()
        for r in high_pre:
            cursor.execute(
                "INSERT INTO transitions (entity_id, from_phase, to_phase, timestamp, reason) "
                "VALUES (?, 'preindividual', 'tension_detected', ?, 'auto: urgency=high')",
                (r[0], now.isoformat())
            )
            cursor.execute("UPDATE entities SET phase='tension_detected', updated_at=? WHERE id=?",
                           (now.isoformat(), r[0]))
            report["transitioned"] += 1

        conn.commit()

    conn.close()

    # ── 6. 보고 ──
    summary = (
        f"t9_auto 완료 — {now:%m/%d %H:%M}\n"
        f"concepts: +{report['concepts_added']}\n"
        f"urgency: +{report['urgency_set']}\n"
        f"project: +{report['projects_set']}\n"
        f"transition: +{report['transitioned']}"
    )
    print(f"\n{summary}")

    if not dry_run and any(v > 0 for v in report.values()):
        tg_send(summary)

    return report


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("[DRY RUN]")
    with pipeline_run("t9_auto", notify_on_fail=not dry):
        run_auto(dry_run=dry)
