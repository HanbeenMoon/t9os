#!/usr/bin/env python3
"""t9_auto.py — T9 OS auto Individuating engine.
Gemini Flash. , NLPGemini.
cron6execution t9tb/autocall."""
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

# T9 OS project list (— Gemini)
PROJECTS = ["T9", "ODNAR", "SSK", "SC41", "AT1", "T9D", "t9tb", "PM3", "L2U"]

# deadline/urgent key(rule)
URGENT_KEYWORDS = ["deadline", "deadline", "", "urgent", "D-", "", "Tomorrow", "ASAP", ""]
DEADLINE_PATTERN = re.compile(r'(\d{4})-(\d{2})-(\d{2})')


# ─── Gemini call ( NLP) ────────────────────────────────────────

def gemini_call(prompt, max_tokens=200):
    """Gemini Flash call. failedNone."""
    if not GEMINI_KEY:
        print("  [gemini failed] GEMINI_API_KEY env var not found")
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
            print(f"  [gemini] response")
            return None
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        for part in parts:
            if "text" in part:
                return part["text"].strip()
        print(f"  [gemini] text not found: {list(content.keys())}")
        return None
    except Exception as e:
        print(f"  [gemini failed] {e}")
        return None


def gemini_batch(items, prompt_fn, max_tokens=150):
    """itemprocess. Batch API call."""
    if not items:
        return {}
    # max 20
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
                #
                lines = [l.strip() for l in raw.split("\n") if l.strip()]
                for idx, item in enumerate(chunk):
                    if idx < len(lines):
                        results[item["id"]] = lines[idx]
        if i + 20 < len(items):
            time.sleep(1)  # rate limit
    return results


# ─── rule () ────────────────────────────────────────

def detect_urgency_hard(text, filename):
    """rule urgency """
    combined = f"{filename} {text}".lower()
    if any(k.lower() in combined for k in URGENT_KEYWORDS):
        return "high"
    # deadline7high
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
    """rule project """
    combined = f"{filename} {text}".upper()
    for proj in PROJECTS:
        if proj.upper() in combined:
            return proj
    return ""


# should_archive remove— G2-B guardian VIOLATION
# Preindividualauto sediment/archiveL2 violation. manual (consolidate)process.


# ─── Gemini  task ────────────────────────────────────────

def extract_concepts_batch(entities):
    """Geminiconcepts extract ()"""
    def prompt_fn(chunk):
        items = []
        for e in chunk:
            preview = (e.get("body_preview") or e.get("filename", ""))[:150]
            items.append(f'{e["id"]}: {preview}')
        joined = "\n".join(items)
        return (
            f" item   2-4 extract. JSON  .\n"
            f"format: [{{\"id\": N, \"concepts\": [\"1\", \"2\"]}}, ...]\n"
            f" ,  (2-4).\n\n{joined}"
        )
    raw = gemini_call(prompt_fn(entities), max_tokens=100 * len(entities))
    if not raw:
        return {}
    results = {}
    try:
        # JSON partialextract
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
    """Geminiproject classify ()"""
    def prompt_fn(chunk):
        items = []
        for e in chunk:
            preview = (e.get("body_preview") or e.get("filename", ""))[:100]
            items.append(f'{e["id"]}: {preview}')
        joined = "\n".join(items)
        return (
            f" item  project  classify. project list: {', '.join(PROJECTS)}\n"
            f"  \"none\". JSON  .\n"
            f"format: [{{\"id\": N, \"project\": \"project\"}}, ...]\n\n{joined}"
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


# ──────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def run_auto(dry_run=False):
    """auto"""
    conn = get_db()
    now = datetime.now()
    report = {"concepts_added": 0, "urgency_set": 0, "transitioned": 0, "projects_set": 0}

    # ─── 1. classify preindividual ────────────────────────────────────────
    unclassified = conn.execute(
        "SELECT id, filename, filepath, body_preview, created_at, updated_at, "
        "concepts, urgency, metadata, phase "
        "FROM entities WHERE phase = 'preindividual' "
        "AND (concepts IS NULL OR concepts = '' OR concepts = '[]') "
        "ORDER BY created_at DESC LIMIT 40"
    ).fetchall()
    unclassified = [dict(r) for r in unclassified]

    print(f"\n=== t9_auto — {now:%Y-%m-%d %H:%M} ===")
    print(f"  classify preindividual: {len(unclassified)}items")

    # ─── 2.  rule  applied ────────────────────────────────────────
    hard_updates = []
    for e in unclassified:
        updates = {}
        text = e.get("body_preview") or ""

        # urgency
        if not e.get("urgency"):
            urg = detect_urgency_hard(text, e["filename"])
            if urg:
                updates["urgency"] = urg

        # project (metadatasave)
        proj = detect_project_hard(text, e["filename"])
        if proj:
            updates["project"] = proj

        if updates:
            hard_updates.append((e["id"], updates))

    print(f"  rule : {len(hard_updates)}items")

    # ─── 3. Gemini  task (concepts extract) ────────────────────────────────────────
    needs_concepts = [e for e in unclassified if not e.get("concepts") or e["concepts"] in ("", "[]")]
    gemini_concepts = {}
    if needs_concepts:
        print(f"  Gemini concepts request: {len(needs_concepts)}items...")
        gemini_concepts = extract_concepts_batch(needs_concepts[:20])  # max 20
        print(f"  Gemini concepts result: {len(gemini_concepts)}items")

    # ─── 4. Gemini project classify ( rule   ) ────────────────────────────────────────
    hard_project_ids = {eid for eid, u in hard_updates if "project" in u}
    needs_project = [e for e in unclassified[:20] if e["id"] not in hard_project_ids]
    gemini_projects = {}
    if needs_project:
        print(f"  Gemini project classify request: {len(needs_project)}items...")
        gemini_projects = classify_project_batch(needs_project)
        print(f"  Gemini project classify result: {len(gemini_projects)}items")

    # ─── 5. DB ────────────────────────────────────────
    if not dry_run:
        cursor = conn.cursor()

        # rule applied
        for eid, updates in hard_updates:
            if "urgency" in updates:
                cursor.execute("UPDATE entities SET urgency=?, updated_at=? WHERE id=?",
                               (updates["urgency"], now.isoformat(), eid))
                report["urgency_set"] += 1

        # Gemini concepts applied
        for eid, concepts in gemini_concepts.items():
            if isinstance(concepts, list) and concepts:
                cursor.execute("UPDATE entities SET concepts=?, updated_at=? WHERE id=?",
                               (json.dumps(concepts, ensure_ascii=False), now.isoformat(), eid))
                report["concepts_added"] += 1

        # Gemini project applied (metadataadd)
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

        # rule projectmetadata
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

        # urgency=high → tension_detected auto
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

    # ── 6. report ──
    summary = (
        f"t9_auto completed — {now:%m/%d %H:%M}\n"
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
