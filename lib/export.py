"""T9 OS JSON Export — 대시보드용"""
import json, sqlite3
from datetime import datetime
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
DB_PATH = T9 / ".t9.db"
FIELD = T9 / "field" / "inbox"
DEADLINE_CANDIDATES = [
    T9.parent / "_legacy" / "_notion_dump" / "T9_마감일.txt",
    T9.parent / "_notion_dump" / "T9_마감일.txt",
    T9 / "data" / "notion_dump" / "T9_마감일.txt",
]

def cmd_export_json():
    """모든 entities + transitions를 JSON으로 stdout에 출력 (대시보드용)."""
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row

    # entities
    entities = []
    for r in conn.execute("SELECT id, filepath, filename, phase, metadata, body_preview, urgency, concepts, created_at, updated_at FROM entities ORDER BY updated_at DESC"):
        meta = {}
        try: meta = json.loads(r["metadata"]) if r["metadata"] else {}
        except (json.JSONDecodeError, TypeError): pass
        entities.append({
            "id": r["id"], "filepath": r["filepath"], "filename": r["filename"],
            "phase": r["phase"], "urgency": r["urgency"] or meta.get("urgency",""),
            "concepts": r["concepts"] or ",".join(meta.get("concepts",[])),
            "body_preview": (r["body_preview"] or "")[:200],
            "created_at": r["created_at"] or "", "updated_at": r["updated_at"] or "",
        })

    # phase counts
    phase_counts = {}
    for r in conn.execute("SELECT phase, COUNT(*) as cnt FROM entities GROUP BY phase"):
        phase_counts[r["phase"]] = r["cnt"]

    # transitions (last 50)
    transitions = []
    for r in conn.execute("SELECT t.id, t.entity_id, t.from_phase, t.to_phase, t.timestamp, t.reason, e.filename FROM transitions t LEFT JOIN entities e ON t.entity_id = e.id ORDER BY t.timestamp DESC LIMIT 50"):
        transitions.append({
            "id": r["id"], "entity_id": r["entity_id"],
            "from_phase": r["from_phase"], "to_phase": r["to_phase"],
            "timestamp": r["timestamp"], "reason": (r["reason"] or "")[:200],
            "filename": r["filename"] or "",
        })

    # urgent items
    urgent = [e for e in entities if e["urgency"] == "high" and e["phase"] not in ("dissolved","archived")]
    # individuating (active work)
    individuating = [e for e in entities if e["phase"] == "individuating"]
    # tension_detected
    tension = [e for e in entities if e["phase"] == "tension_detected"]

    # deadlines from file
    deadlines_raw = []
    for dp in DEADLINE_CANDIDATES:
        if dp.exists():
            for line in dp.read_text(encoding="utf-8", errors="replace").strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("|")
                if len(parts) >= 2:
                    deadlines_raw.append({"date": parts[0].strip(), "title": parts[1].strip(),
                                         "project": parts[2].strip() if len(parts) > 2 else ""})
            break

    result = {
        "exported_at": datetime.now().isoformat(),
        "phase_counts": phase_counts,
        "total_entities": len(entities),
        "entities": entities,
        "transitions": transitions,
        "urgent": urgent,
        "individuating": individuating,
        "tension": tension,
        "deadlines": deadlines_raw,
    }

    conn.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))

# ─── CLI 진입점 ──────────────────────────────────────────────────────────────

USAGE = """
  T9 OS Seed v0.2 -- Simondonian Engine

  capture <text>                       전개체 저장 (tension 자동 감지 + disparation 기록)
  reindex                              파일 -> SQLite (정규 컬럼 포함)
  search <query>                       자유 검색
  status                               상태 요약 + 관계 수
  daily                                일일 브리프 + 마감일 + 전도적 학습
  transition <id> <phase> [reason]     상태 전이
  compose <text>                       동적 플랜 생성 (concepts/urgency/disparation 기반)
  approve <id> <plan>                  플랜 승인
  reflect                              주간 반성
  consolidate                          아카이브 -> memory/
  watch [sec]                          파일 감시
  history <id>                         전이 이력 + 관계 + 부모
  relate <id1> <id2> [dir] [desc]      엔티티 연결 (transduction, 방향성)
  digest                               다이제스트 파일 FTS 인덱싱
  legacy <query>                       레거시 검색
"""

