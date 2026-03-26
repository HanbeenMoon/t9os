#!/usr/bin/env python3
"""
T9 Unified Dashboard — Single HTML, Tab-based
==============================================
Generates one dashboard.html with 5 tabs:
  [state] [Timeline] [Tension] [Transduction] [Kanban]

Usage:
    python3 t9_viz.py              # Generate & open dashboard
    python3 t9_viz.py dashboard    # Same

Output: T9OS/artifacts/dashboard.html
No external dependencies — pure HTML/CSS/JS, offline-ready.
"""

import json
import math
import sqlite3
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & DB
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
try:
    from lib.config import DB_PATH
except ImportError:
    _WSL_DB = Path.home() / ".t9os_data" / ".t9.db"
    DB_PATH = _WSL_DB if _WSL_DB.exists() else BASE / ".t9.db"
OUT_PATH = BASE / "artifacts" / "dashboard.html"

PHASE_ORDER = ["preindividual", "individuating", "stabilized",
               "tension_detected", "suspended", "archived"]
PHASE_LABELS = {
    "preindividual": "Preindividual", "individuating": "Individuating",
    "stabilized": "Stabilized", "tension_detected": "Tension",
    "suspended": "suspended", "archived": "archive",
}
PHASE_COLORS = {
    "preindividual": "#d29922", "individuating": "#58a6ff",
    "stabilized": "#3fb950", "tension_detected": "#f85149",
    "suspended": "#8b949e", "archived": "#484f58",
}


def get_db():
    if not DB_PATH.exists():
        print(f"[ERROR] DB not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def load_entities(conn):
    rows = conn.execute(
        "SELECT id, filename, phase, metadata, urgency, concepts, "
        "body_preview, updated_at, created_at FROM entities ORDER BY id"
    ).fetchall()
    out = []
    for r in rows:
        meta = {}
        if r["metadata"]:
            try:
                meta = json.loads(r["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        out.append({
            "id": r["id"], "filename": r["filename"] or "",
            "phase": r["phase"] or "preindividual", "metadata": meta,
            "urgency": r["urgency"] or "", "concepts": r["concepts"] or "",
            "body_preview": (r["body_preview"] or "")[:120],
            "updated_at": r["updated_at"] or "",
            "created_at": r["created_at"] or "",
        })
    return out


def load_transitions(conn):
    rows = conn.execute(
        "SELECT t.id, t.entity_id, t.from_phase, t.to_phase, t.timestamp, "
        "t.reason, e.filename FROM transitions t "
        "LEFT JOIN entities e ON t.entity_id = e.id "
        "ORDER BY t.timestamp DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def load_relates(conn):
    rows = conn.execute(
        "SELECT r.id, r.source_id, r.target_id, r.direction, r.description, "
        "s.filename as source_name, t.filename as target_name "
        "FROM relates r "
        "LEFT JOIN entities s ON r.source_id = s.id "
        "LEFT JOIN entities t ON r.target_id = t.id "
        "ORDER BY r.created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def esc(s):
    if not s:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------
def build_html(entities, transitions, relates):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Phase counts
    phase_counts = {}
    for e in entities:
        p = e["phase"]
        phase_counts[p] = phase_counts.get(p, 0) + 1
    max_count = max(phase_counts.values()) if phase_counts else 1

    # Urgent items
    urgent = sorted(
        [e for e in entities if e["urgency"] == "high"],
        key=lambda x: x["updated_at"], reverse=True
    )[:15]

    # Deadlines
    deadlines = []
    for e in entities:
        dl = e["metadata"].get("deadline")
        if dl:
            try:
                dt = datetime.fromisoformat(dl.replace("Z", "+00:00"))
                delta = (dt - datetime.now()).days
                deadlines.append({"filename": e["filename"], "dday": delta, "id": e["id"]})
            except (ValueError, TypeError):
                pass
    deadlines.sort(key=lambda x: x["dday"])
    deadlines = deadlines[:10]

    recent_trans = transitions[:5]

    # Disparation
    dispar = []
    for e in entities:
        d = e["metadata"].get("disparation")
        if d:
            dispar.append({
                "id": e["id"], "filename": e["filename"],
                "dim_a": d.get("dimension_a", ""),
                "dim_b": d.get("dimension_b", ""),
                "description": d.get("description", ""),
            })

    # Kanban
    kanban_phases = ["preindividual", "individuating", "stabilized", "suspended"]
    kanban = {p: [] for p in kanban_phases}
    for e in entities:
        if e["phase"] in kanban:
            kanban[e["phase"]].append(e)
    for p in kanban:
        kanban[p] = kanban[p][:30]

    # ---- Section builders ----

    def _bars():
        h = ""
        for p in PHASE_ORDER:
            cnt = phase_counts.get(p, 0)
            if cnt == 0:
                continue
            pct = (cnt / max_count) * 100
            c = PHASE_COLORS.get(p, "#8b949e")
            lbl = PHASE_LABELS.get(p, p)
            h += (f'<div class="bar-row"><span class="bar-label">{esc(lbl)}</span>'
                  f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{c}"></div></div>'
                  f'<span class="bar-count">{cnt}</span></div>')
        return h

    def _urgent():
        if not urgent:
            return '<div class="empty">urgent item not found</div>'
        h = ""
        for u in urgent:
            h += (f'<div class="li"><span class="id">#{u["id"]}</span>'
                  f'<span class="nm">{esc(u["filename"][:50])}</span>'
                  f'<span class="bg bg-r">urgent</span></div>')
        return h

    def _deadlines():
        if not deadlines:
            return '<div class="empty">deadline item not found</div>'
        h = ""
        for d in deadlines:
            c = "#f85149" if d["dday"] <= 3 else "#d29922" if d["dday"] <= 7 else "#3fb950"
            sign = "+" if d["dday"] >= 0 else ""
            h += (f'<div class="li"><span class="nm">{esc(d["filename"][:40])}</span>'
                  f'<span class="bg" style="background:{c}">D{sign}{d["dday"]}</span></div>')
        return h

    def _recent():
        if not recent_trans:
            return '<div class="empty"> record not found</div>'
        h = ""
        for t in recent_trans:
            fc = PHASE_COLORS.get(t["from_phase"], "#8b949e")
            tc = PHASE_COLORS.get(t["to_phase"], "#8b949e")
            h += (f'<div class="li"><span class="nm">{esc((t.get("filename") or "?")[:40])}</span>'
                  f'<span class="bg" style="background:{fc}">{esc(t["from_phase"][:4])}</span>'
                  f'<span class="arr">\u2192</span>'
                  f'<span class="bg" style="background:{tc}">{esc(t["to_phase"][:4])}</span>'
                  f'<span class="ts">{esc((t.get("timestamp") or "")[:16])}</span></div>')
        return h

    def _timeline():
        if not transitions:
            return ('<div class="empty big"> record .<br>'
                    't9_seed.py transition command state   .</div>')
        h = ""
        for i, t in enumerate(transitions[:50]):
            side = "l" if i % 2 == 0 else "r"
            tc = PHASE_COLORS.get(t["to_phase"], "#8b949e")
            fc = PHASE_COLORS.get(t["from_phase"], "#8b949e")
            h += (f'<div class="tli tl-{side}">'
                  f'<div class="tld" style="background:{tc}"></div>'
                  f'<div class="tlc">'
                  f'<div class="ts">{esc((t.get("timestamp") or "")[:16])}</div>'
                  f'<div class="tlt">{esc((t.get("filename") or "?")[:50])}</div>'
                  f'<div style="font-size:12px"><span style="color:{fc}">{esc(t["from_phase"])}</span>'
                  f' \u2192 <span style="color:{tc}">{esc(t["to_phase"])}</span></div>'
                  f'<div class="ts">{esc((t.get("reason") or "")[:80])}</div>'
                  f'</div></div>')
        return h

    def _dispar():
        if not dispar:
            return ('<div class="empty big">Tension(disparation) metadata   .<br>'
                    'metadata disparation.dimension_a / dimension_b add  .</div>')
        h = ""
        for d in dispar:
            h += (f'<div class="dc">'
                  f'<div style="font-weight:600;font-size:14px;margin-bottom:12px">#{d["id"]} {esc(d["filename"][:50])}</div>'
                  f'<div class="db">'
                  f'<div class="dd"><div class="dl">Dimension A</div><div class="dv">{esc(str(d["dim_a"])[:60])}</div></div>'
                  f'<div class="dvs">VS</div>'
                  f'<div class="dd"><div class="dl">Dimension B</div><div class="dv">{esc(str(d["dim_b"])[:60])}</div></div>'
                  f'</div>'
                  f'<div style="font-size:12px;color:#8b949e">{esc(str(d["description"])[:120])}</div>'
                  f'</div>')
        return h

    def _network():
        if not relates:
            return ('<div class="empty big">connection(relate)  .<br>'
                    't9_seed.py relate &lt;id1&gt; &lt;id2&gt; command  connection  .</div>')
        nodes = {}
        for r in relates:
            nodes.setdefault(r["source_id"], r.get("source_name") or f'#{r["source_id"]}')
            nodes.setdefault(r["target_id"], r.get("target_name") or f'#{r["target_id"]}')

        # SVG circular layout
        node_list = list(nodes.items())
        n = len(node_list)
        cx_c, cy_c, rad = 300, 250, 200
        pos = {}
        for i, (nid, _) in enumerate(node_list):
            a = (2 * math.pi * i) / max(n, 1)
            pos[nid] = (cx_c + rad * math.cos(a), cy_c + rad * math.sin(a))

        svg = ('<svg width="100%" viewBox="0 0 600 500" style="display:block;margin:0 auto 20px;max-width:600px">'
               '<defs><marker id="ah" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">'
               '<polygon points="0 0,8 3,0 6" fill="#58a6ff"/></marker></defs>')
        for r in relates[:50]:
            s, t = pos.get(r["source_id"]), pos.get(r["target_id"])
            if s and t:
                svg += f'<line x1="{s[0]:.0f}" y1="{s[1]:.0f}" x2="{t[0]:.0f}" y2="{t[1]:.0f}" stroke="#30363d" stroke-width="1.5" marker-end="url(#ah)"/>'
        for nid, (x, y) in pos.items():
            nm = esc(nodes[nid][:15])
            svg += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#58a6ff"/>'
            svg += f'<text x="{x:.0f}" y="{y - 10:.0f}" fill="#c9d1d9" font-size="10" text-anchor="middle">{nm}</text>'
        svg += "</svg>"

        lst = ""
        for r in relates[:50]:
            sn = esc((r.get("source_name") or f'#{r["source_id"]}')[:40])
            tn = esc((r.get("target_name") or f'#{r["target_id"]}')[:40])
            arrow = "\u2194" if r.get("direction") == "bidirectional" else "\u2192"
            desc = esc((r.get("description") or "")[:60])
            lst += (f'<div class="li"><span class="rn">{sn}</span>'
                    f'<span style="color:#58a6ff;font-size:16px">{arrow}</span>'
                    f'<span class="rn">{tn}</span>'
                    f'<span style="color:#8b949e;flex:1">{desc}</span></div>')
        return svg + lst

    def _kanban():
        h = '<div class="kb">'
        for p in kanban_phases:
            c = PHASE_COLORS.get(p, "#8b949e")
            lbl = PHASE_LABELS.get(p, p)
            total = phase_counts.get(p, 0)
            h += (f'<div class="kc"><div class="kh" style="border-top:3px solid {c}">'
                  f'<span>{esc(lbl)}</span><span class="kcnt">{total}</span></div>'
                  f'<div class="kcs">')
            for e in kanban[p]:
                ub = '<span class="bg bg-r" style="font-size:10px">\uae34\uae09</span>' if e["urgency"] == "high" else ""
                con = esc(e["concepts"][:30]) if e["concepts"] else ""
                h += (f'<div class="kd"><div class="kt">#{e["id"]} {esc(e["filename"][:35])}</div>'
                      f'{ub}<div class="kcon">{con}</div></div>')
            if not kanban[p]:
                h += '<div class="empty" style="padding:20px">\ube44\uc5b4\uc788\uc74c</div>'
            if total > 30:
                h += f'<div class="kcon" style="text-align:center;padding:8px">+{total - 30} more</div>'
            h += '</div></div>'
        h += '</div>'
        return h

    # ---- Assemble HTML ----
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><title>T9 Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:system-ui,-apple-system,sans-serif}}
.hd{{padding:16px 24px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between}}
.hd h1{{font-size:18px;font-weight:600;color:#f0f6fc}}
.hd .ts{{font-size:12px;color:#8b949e;font-family:monospace}}
.tabs{{display:flex;gap:0;border-bottom:1px solid #30363d;background:#161b22;padding:0 24px}}
.tab{{padding:10px 20px;cursor:pointer;font-size:13px;color:#8b949e;border-bottom:2px solid transparent;transition:all .15s;user-select:none}}
.tab:hover{{color:#c9d1d9}}.tab.on{{color:#58a6ff;border-bottom-color:#58a6ff}}
.tc{{display:none;padding:24px;min-height:calc(100vh - 110px)}}.tc.on{{display:block}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.cd{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}}
.ct{{font-size:13px;font-weight:600;color:#f0f6fc;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}}
.bar-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.bar-label{{width:80px;font-size:12px;text-align:right;color:#8b949e;font-family:monospace}}
.bar-track{{flex:1;height:22px;background:#21262d;border-radius:4px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:4px;transition:width .3s}}
.bar-count{{width:36px;font-size:13px;font-family:monospace;text-align:right;color:#f0f6fc}}
.li{{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:4px;font-size:12px}}
.li:hover{{background:#21262d}}
.id{{color:#8b949e;font-family:monospace;min-width:40px}}
.nm{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.bg{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500;color:#0d1117}}
.bg-r{{background:#f85149}}.bg-y{{background:#d29922}}.bg-g{{background:#3fb950}}.bg-b{{background:#58a6ff}}
.arr{{color:#8b949e}}.ts{{font-size:11px;color:#484f58;font-family:monospace}}
.empty{{color:#484f58;font-size:13px;padding:12px;text-align:center}}
.empty.big{{padding:60px 40px;font-size:14px;line-height:1.8}}
.sr{{display:flex;gap:12px;margin-bottom:16px}}
.sc{{flex:1;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;text-align:center}}
.sn{{font-size:28px;font-weight:700;font-family:monospace}}
.sl{{font-size:11px;color:#8b949e;margin-top:4px}}
.tl{{position:relative;padding:20px 0}}.tl::before{{content:'';position:absolute;left:50%;top:0;bottom:0;width:2px;background:#30363d}}
.tli{{position:relative;margin-bottom:24px;display:flex}}
.tl-l{{justify-content:flex-start;padding-right:calc(50% + 20px)}}
.tl-r{{justify-content:flex-end;padding-left:calc(50% + 20px)}}
.tld{{position:absolute;left:calc(50% - 5px);top:12px;width:10px;height:10px;border-radius:50%;z-index:1}}
.tlc{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;max-width:360px;width:100%}}
.tlt{{font-size:13px;font-weight:500;margin:4px 0}}
.dc{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}}
.db{{display:flex;align-items:center;gap:16px;margin-bottom:8px}}
.dd{{flex:1;background:#21262d;border-radius:6px;padding:12px;text-align:center}}
.dl{{font-size:10px;color:#8b949e;text-transform:uppercase;margin-bottom:4px}}
.dv{{font-size:13px;color:#f0f6fc}}.dvs{{font-size:16px;font-weight:700;color:#f85149}}
.rn{{background:#21262d;padding:3px 8px;border-radius:4px;font-family:monospace;font-size:11px}}
.kb{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;align-items:start}}
.kc{{background:#0d1117;border:1px solid #30363d;border-radius:8px;min-height:200px}}
.kh{{padding:10px 12px;display:flex;justify-content:space-between;align-items:center;font-size:13px;font-weight:600;border-radius:8px 8px 0 0;background:#161b22}}
.kcnt{{background:#21262d;padding:2px 8px;border-radius:10px;font-size:11px;color:#8b949e}}
.kcs{{padding:8px}}
.kd{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px;margin-bottom:6px}}
.kt{{font-size:12px;font-weight:500;margin-bottom:4px;word-break:break-all}}
.kcon{{font-size:10px;color:#8b949e;font-family:monospace}}
</style>
</head>
<body>
<div class="hd"><h1>T9 Dashboard</h1><span class="ts">{esc(now)}</span></div>
<div class="tabs">
<div class="tab on" onclick="sw('s')">state</div>
<div class="tab" onclick="sw('t')">Timeline</div>
<div class="tab" onclick="sw('d')">Tension</div>
<div class="tab" onclick="sw('n')">Transduction</div>
<div class="tab" onclick="sw('k')">Kanban</div>
</div>

<div id="s" class="tc on">
<div class="sr">
<div class="sc"><div class="sn">{len(entities)}</div><div class="sl">Total Entities</div></div>
<div class="sc"><div class="sn" style="color:# 58a6ff">{phase_counts.get('individuating',0)}</div><div class="sl">Individuating</div></div>
<div class="sc"><div class="sn" style="color:#3fb950">{phase_counts.get('stabilized',0)}</div><div class="sl">Stabilized</div></div>
<div class="sc"><div class="sn" style="color:#f85149">{len(urgent)}</div><div class="sl">urgent</div></div>
<div class="sc"><div class="sn" style="color:# d29922">{len(transitions)}</div><div class="sl">record</div></div>
</div>
<div class="g2">
<div class="cd"><div class="ct">Phase Distribution</div>{_bars()}</div>
<div class="cd"><div class="ct">urgent item</div>{_urgent()}</div>
</div>
<div class="g2" style="margin-top:16px">
<div class="cd"><div class="ct">deadline D-Day</div>{_deadlines()}</div>
<div class="cd"><div class="ct">Recent Transitions</div>{_recent()}</div>
</div>
</div>

<div id="t" class="tc"><div class="tl">{_timeline()}</div></div>
<div id="d" class="tc"><h2 style="font-size:16px;margin-bottom:16px;color:#f0f6fc">Tension (Disparation)</h2>{_dispar()}</div>
<div id="n" class="tc"><h2 style="font-size:16px;margin-bottom:16px;color:# f0f6fc">(Transduction)</h2>{_network()}</div>
<div id="k" class="tc">{_kanban()}</div>

<script>
function sw(id){{
document.querySelectorAll('.tc').forEach(e=>e.classList.remove('on'));
document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));
document.getElementById(id).classList.add('on');
var m={{s:0,t:1,d:2,n:3,k:4}};
document.querySelectorAll('.tab')[m[id]].classList.add('on');
}}
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    conn = get_db()
    entities = load_entities(conn)
    transitions = load_transitions(conn)
    relates = load_relates(conn)
    conn.close()

    html = build_html(entities, transitions, relates)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")

    print(f"[OK] Dashboard -> {OUT_PATH}")
    print(f"     Entities: {len(entities)}, Transitions: {len(transitions)}, Relates: {len(relates)}")
    webbrowser.open(str(OUT_PATH))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dashboard"
    if cmd in ("dashboard", "dash", "d"):
        main()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python3 t9_viz.py [dashboard]")
        sys.exit(1)
