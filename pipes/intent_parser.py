#!/usr/bin/env python3
"""
T9 OS Intent Parser v0.1
BIBLE.md + L2_interpretation.md 5implement.

rule . LLM API call not found. stdlibuse.
t9_seed.pyDBsearch.

Usage:
    python3 T9OS/pipes/intent_parser.py "SSK  5 analyzeresult    "
    python3 T9OS/pipes/intent_parser.py --json "ODNAR MVP deploy"
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---- path ----------------------------------------------------------------
# hardcoded : file criteriaT9OS
# intent_parser.py T9OS/pipes/ → 2T9OS
_THIS_FILE = Path(__file__).resolve()
T9 = _THIS_FILE.parent.parent          # T9OS/
HANBEEN = T9.parent                   # HANBEEN/
sys.path.insert(0, str(T9))
from lib.config import DB_PATH  # WSL DB

# ---- class --------------------------------------------------------


@dataclass
class Plan:
    id: str            # A / B / C
    name: str          # "execution"
    steps: list[str]
    time_est: str      # "30 min"
    tool: str          # cc / cx / gm / cc+cx
    strategy: str      # search / reuse / buy / build


@dataclass
class ParsedIntent:
    raw: str
    intent: str                        # create/explore/solve/earn/express/become
    state: str                         # /execution/on hold
    resources: list[str]
    constraints: list[str]             # deadline//
    artifact: str                      # artifact type
    urgency: str                       # high/mid/low
    project: str                       # SSK/ODNAR/T9/...
    disparation: Optional[dict] = None # {"dim_a": ..., "dim_b": ...}
    confidence: float = 0.0            # 0~1
    plans: list[Plan] = field(default_factory=list)
    similar_entities: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["plans"] = [asdict(p) for p in self.plans]
        return d

    def pretty(self) -> str:
        R, J = lambda v: ', '.join(v) or '(not found)', "\n"
        axes = [f"  Intent: {self.intent}", f"  State: {self.state}",
                f"  Resource: {R(self.resources)}", f"  Constraint: {R(self.constraints)}",
                f"  Artifact: {self.artifact}", f"  Urgency: {self.urgency}",
                f"  Project: {self.project}", f"  Confidence: {self.confidence:.0%}"]
        if self.disparation:
            axes.append(f"  Disparation: {self.disparation['dim_a']} vs {self.disparation['dim_b']}")
        if self.similar_entities:
            axes.append(f"  Similar: {len(self.similar_entities)}items (DB)")
            axes.extend(f"    [{e['id']:3d}] {e['phase'][:12]:12s} | {e['filename'][:50]}"
                        for e in self.similar_entities[:3])
        if self.plans:
            axes.append("")
            for p in self.plans:
                axes.append(f"  Plan {p.id}: {p.name} ({p.time_est}, {p.tool}) [{p.strategy}]")
                axes.extend(f"    {s}" for s in p.steps)
        return J.join(axes)


# ---- key(format: "kw1 kw2 kw3".split()) ----------------------

def _s(s: str) -> list[str]:
    return s.split()

# (Intent) — t9_seed.py CONCEPT_KW
INTENT_KW = {
    "create":  _s(" implement  build create   create     setup deploy deploy draft convert auto  script"),
    "explore": _s("   explore research analyze search   check compare    "),
    "solve":   _s(" modify fix solve  error debug   recover  hotfix    "),
    "earn":    _s("  earn         "),
    "express": _s("  express   report  PPT  clean up summary "),
    "become":  _s("  become  learning      "),
}
_INTENT_WEIGHT = {"create": 1.0, "solve": 1.0, "explore": 0.8, "express": 0.9, "earn": 0.7, "become": 0.6}

# state(State)
STATE_KW = {
    "execution": _s("   start    execution   deploy commit push run"),
    "": _s("  compare        "),
    "on hold": _s("   on hold  someday record  save"),
}

# (Resource)
RESOURCE_KW = {
    "": _s("  hour min  Tomorrow "),
    "token": _s("token token API call"),  "": _s("      "),
    "file": _s("file folder path  CSV JSON xlsx PDF dofile dta"),
    "": _s("        "),
    "tool": _s("Stata Python Next.js Supabase Claude GPT Gemini Docker GitHub Notion Telegram"),
    "": _s("    "),
    "GPU":  _s("GPU CUDA RTX VRAM"),
}

# (Constraint)
CONSTRAINT_KW = {
    "deadline": _s("deadline  deadline D-    Tomorrow   Tomorrow"),
    "": _s("  budget  "), "": _s("    "),
    "": _s("    "), "accesspermission": _s("permission access auth APIkey password ssh VPN"),
    "": _s("  storage  RAM"),
}

# artifact(Artifact)
ARTIFACT_KW = {
    "": _s(" script function class module dofile py ts js"),
    "": _s(" report  report md docx summary"),
    "":   _s(" table table result statistics"),
    "": _s("  plot   figure"),
    "": _s("keystructure spec blueprint"),
    "": _s(" dataset CSV JSON dta DB"),
    "PPT":  _s("PPT   "),
    "":   _s(" UI   "),
}

# project (CLAUDE.md )
PROJECT_KW = {
    "SSK":   _s("SSK     Stata   MDIS    RA"),
    "ODNAR": _s("ODNAR    Supabase   MVP unknown"),
    "SC41":  _s("   Canvas     4 "),
    "T9":    _s("T9  Individuating  constitution BIBLE seed t9_seed pipeline"),
    "AT1":   _s("AT1  "), "TSUM": _s("TSUM   LoRA FinBot  T-SUM"),
    "PM3":   _s("PM3 PMILL "), "L2U": _s("L2U watcher queue"),
    "T9D":   _s("T9D  Dashboard Vercel"), "": _s(" table "),
}

# urgent
URGENCY_KW = {
    "high": _s(" urgent urgent asap deadline        hotfix "),
    "low":  _s("   someday    "),
}

# Tension(Disparation) — L2
OPPOSITION_PAIRS = [
    (_s("  asap urgent  "), _s("   someday "), "urgency_high", "urgency_low"),
    (_s("build  implement  "), _s("buy   service existing"), "build", "buy"),
    (_s(" min  MVP"), _s("   "), "simplicity", "complexity"),
    (_s("  "), _s("   "), "solo", "collaboration"),
    (_s("  "), _s("execution deploy commit "), "exploration", "execution"),
]

# previous
AGENT_RULES = {
    "SSK": "cc", "ODNAR": "cc+cx", "SC41": "cx", "T9": "cc",
    "AT1": "cc", "TSUM": "cx",
}


# ---- IntentParser ---------------------------------------------------------

class IntentParser:
    """input5analyzeexecution suggestion."""

    def __init__(self):
        self._db_conn: Optional[sqlite3.Connection] = None

    def _get_db(self) -> Optional[sqlite3.Connection]:
        """t9_seed.py DBconnection. None."""
        if self._db_conn is not None:
            return self._db_conn
        if not DB_PATH.exists():
            return None
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            self._db_conn = conn
            return conn
        except Exception:
            return None

    def close(self):
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    # ---- 5----------------------------------------------------------

    def _detect_intent(self, text: str) -> tuple[str, float]:
        """. (intent, confidence) return."""
        tl = text.lower()
        scores: dict[str, float] = {}

        for intent, keywords in INTENT_KW.items():
            score = 0.0
            weight = _INTENT_WEIGHT.get(intent, 0.8)
            for kw in keywords:
                pos = tl.find(kw.lower())
                if pos != -1:
                    # score ()
                    position_bonus = max(0, 1.0 - pos / max(len(tl), 1))
                    score += weight * (1.0 + position_bonus * 0.5)
            scores[intent] = score

        if not any(scores.values()):
            return "explore", 0.3  # defaultvalue:

        best = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best] / total if total > 0 else 0.5
        return best, min(confidence, 1.0)

    def _detect_state(self, text: str) -> str:
        """state : /execution/on hold."""
        tl = text.lower()
        state_scores: dict[str, int] = {"execution": 0, "": 0, "on hold": 0}

        # (≤2)//substring .
        # : """" block.
        def _match_kw(kw: str, text_lower: str) -> bool:
            if len(kw) <= 2:
                return bool(re.search(r'(?<=[^-a-z])' + re.escape(kw) + r'(?=[^-a-z]|$)',
                                      ' ' + text_lower + ' '))
            return kw in text_lower

        for state, keywords in STATE_KW.items():
            for kw in keywords:
                if _match_kw(kw.lower(), tl):
                    state_scores[state] += 1

        best = max(state_scores, key=lambda k: state_scores[k])
        if state_scores[best] == 0:
            return ""  # defaultvalue
        return best

    @staticmethod
    def _match_any(tl: str, kw_dict: dict[str, list[str]]) -> list[str]:
        """keyreturn ()."""
        return [cat for cat, kws in kw_dict.items() if any(k.lower() in tl for k in kws)]

    @staticmethod
    def _score_kw(tl: str, kw_dict: dict[str, list[str]], default: str = "") -> str:
        """keyscore return."""
        scores = {cat: sum(1 for k in kws if k.lower() in tl) for cat, kws in kw_dict.items()}
        best = max(scores, key=lambda k: scores[k]) if scores else default
        return best if scores.get(best, 0) > 0 else default

    def _detect_resources(self, text: str) -> list[str]:
        return self._match_any(text.lower(), RESOURCE_KW)

    def _detect_constraints(self, text: str) -> list[str]:
        return self._match_any(text.lower(), CONSTRAINT_KW)

    def _detect_artifact(self, text: str) -> str:
        return self._score_kw(text.lower(), ARTIFACT_KW, "")

    def _detect_urgency(self, text: str) -> str:
        tl = text.lower()
        # urgency rule: keyurgent pattern
        _compound_high = [
            ("Tomorrow", ""), ("Tomorrow", ""), ("Tomorrow", "deadline"), ("Tomorrow", ""),
            ("", "deadline"), ("", ""), ("", ""),
        ]
        for pair in _compound_high:
            if all(k in tl for k in pair):
                return "high"

        for level, kws in URGENCY_KW.items():
            if any(k in tl for k in kws):
                return level
        return "mid"

    def _detect_project(self, text: str) -> str:
        return self._score_kw(text.lower(), PROJECT_KW, "(classify)")

    def _detect_disparation(self, text: str) -> Optional[dict]:
        tl = text.lower()
        for kws_a, kws_b, la, lb in OPPOSITION_PAIRS:
            if any(k in tl for k in kws_a) and any(k in tl for k in kws_b):
                return {"dim_a": la, "dim_b": lb}
        return None

    # ---- DB search -----------------------------------------------------------

    def _search_similar(self, text: str, project: str) -> list[dict]:
        """t9_seed.py DBsearch."""
        conn = self._get_db()
        if conn is None:
            return []

        results: list[dict] = []

        # 1) FTS search
        # extract (2+ )
        words = re.findall(r'[-]{2,}|[a-zA-Z]{3,}', text)
        for word in words[:5]:
            try:
                safe = '"' + word.replace('"', '') + '"'
                rows = conn.execute(
                    "SELECT e.id, e.filename, e.phase, e.filepath "
                    "FROM entities_fts f JOIN entities e ON f.rowid = e.id "
                    "WHERE entities_fts MATCH ? LIMIT 5", (safe,)
                ).fetchall()
                for r in rows:
                    entry = {"id": r["id"], "filename": r["filename"],
                             "phase": r["phase"], "filepath": r["filepath"]}
                    if entry not in results:
                        results.append(entry)
            except Exception:
                pass

        # 2) project keyLIKE search (FTS result )
        if len(results) < 3 and project != "(classify)":
            for kw in PROJECT_KW.get(project, [])[:3]:
                try:
                    rows = conn.execute(
                        "SELECT id, filename, phase, filepath FROM entities "
                        "WHERE (filename LIKE ? OR body_preview LIKE ?) "
                        "AND phase NOT IN ('dissolved') LIMIT 3",
                        (f"%{kw}%", f"%{kw}%")
                    ).fetchall()
                    for r in rows:
                        entry = {"id": r["id"], "filename": r["filename"],
                                 "phase": r["phase"], "filepath": r["filepath"]}
                        if entry not in results:
                            results.append(entry)
                except Exception:
                    pass

        return results[:8]  # max 8items

    # ---- suggestion ----------------------------------------------------------

    def suggest_plan(self, parsed: ParsedIntent) -> list[Plan]:
        """Search -> Reuse -> Buy -> Build suggestion."""
        P, tool = Plan, AGENT_RULES.get(parsed.project, "cc")
        plans: list[Plan] = []

        # Plan A: Search ()
        n = len(parsed.similar_entities)
        plans.append(P("A", f"Search -- existing  {'' if n else ''}",
            [f"1. DB   {n}items check", "2.  file  copy/modify", "3. artifact check  completed"]
            if n else ["1. grep/t9_seed search search", "2. _ai/logs/  log check", "3. found  ,  Plan B"],
            "15" if n else "10", tool if n else "cc", "search"))

        # Plan B: execution (urgency + intent )
        _B = {  # intent -> (name, steps, time, tool_override, strategy)
            "_high":  (" execution -- min path",
                       ["1. Core deliverable in 30 min", f"2. {tool}  execution", "3. verification min, Post-hoc improvement"],
                       "30 min", tool, "build"),
            "explore": ("Explore-learn loop",
                        ["1. gm  3  ", "2. Extract key insights (cc)", "3. Derive applicable patterns"],
                        "1.5 hours", "gm+cc", "buy"),
            "become": ("Explore-learn loop",
                       ["1. gm  3  ", "2. Extract key insights (cc)", "3. Derive applicable patterns"],
                       "1.5 hours", "gm+cc", "buy"),
            "solve":  ("debug -- cause   modify",
                       ["1. /  check", "2. cause  (log/ analyze)", f"3. {tool} modify  verification"],
                       "45 min", tool, "build"),
            "create": ("Split parallel execution",
                       ["1. Decompose subtasks", "2. cc/cx parallel assignment", "3. Integrate and verify"],
                       "1 hour", "cc+cx", "build"),
            "express": ("  -- structure ",
                        ["1. /structure  (cc)", f"2. body  (cx, {parsed.artifact})", "3.   "],
                        "1 hour", "cc+cx", "build"),
            "earn":   ("ROI-first execution",
                       ["1. Cost-benefit assessment", "2. Select minimum-input option", "3. Quick verification  "],
                       "45 min", "cc", "buy"),
        }
        key = "_high" if parsed.urgency == "high" else parsed.intent
        name, steps, t, tl, strat = _B.get(key, (" execution",
            ["1.  clean up", f"2. {tool} execution", "3. artifact check"], "1 hour", tool, "build"))
        plans.append(P("B", name, steps, t, tl, strat))

        # Plan C: Tension Buy-first
        if parsed.disparation:
            da, db = parsed.disparation["dim_a"], parsed.disparation["dim_b"]
            plans.append(P("C", f"Tension  -- {da} vs {db}",
                [f"1. {da} requirements analysis", f"2. {db} requirements analysis",
                 "3. Derive compatible solution (transduction)"], "1 hour", "cc", "build"))
        else:
            plans.append(P("C", "Buy-first --  tool ",
                ["1. Search 3 existing services/tools (gm)", "2. Cost-effectiveness evaluation", "3. Select and apply"],
                "45 min", "gm", "buy"))
        return plans

    # ---- ----------------------------------------------------------

    def parse(self, text: str) -> ParsedIntent:
        """input5analyze."""
        intent, confidence = self._detect_intent(text)
        state = self._detect_state(text)
        resources = self._detect_resources(text)
        constraints = self._detect_constraints(text)
        artifact = self._detect_artifact(text)
        urgency = self._detect_urgency(text)
        project = self._detect_project(text)
        disparation = self._detect_disparation(text)

        # state : urgency=highexecution
        if urgency == "high" and state != "execution":
            state = "execution"

        #
        # project + artifact + ->
        if project != "(classify)":
            confidence = min(confidence + 0.15, 1.0)
        if artifact != "":  # defaultvalue
            confidence = min(confidence + 0.1, 1.0)

        # DBsearch
        similar = self._search_similar(text, project)

        parsed = ParsedIntent(
            raw=text,
            intent=intent,
            state=state,
            resources=resources,
            constraints=constraints,
            artifact=artifact,
            urgency=urgency,
            project=project,
            disparation=disparation,
            confidence=confidence,
            similar_entities=similar,
        )

        # suggestion
        parsed.plans = self.suggest_plan(parsed)

        return parsed


# ---- t9_seed.py Integrate function --------------------------------------------------

def parse_for_compose(text: str) -> tuple[ParsedIntent, list[dict]]:
    """t9_seed.py cmd_compose()call.
    (ParsedIntent, plans_as_dicts) return.

    Usage in t9_seed.py:
        from pipes.intent_parser import parse_for_compose
        parsed, plans = parse_for_compose(text)
    """
    parser = IntentParser()
    parsed = parser.parse(text)
    parser.close()

    plans_dicts = []
    for p in parsed.plans:
        plans_dicts.append({
            "id": p.id,
            "name": p.name,
            "steps": p.steps,
            "time": p.time_est,
            "tool": p.tool,
            "strategy": p.strategy,
        })
    return parsed, plans_dicts


# ---- CLI ------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    json_mode = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]
    text = " ".join(args)

    if not text.strip():
        print("  input.")
        return

    parser = IntentParser()
    result = parser.parse(text)
    parser.close()

    if json_mode:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"\n  === T9 Intent Parser v0.1 ===")
        print(f"  Input: {text}\n")
        print(result.pretty())
        print()


if __name__ == "__main__":
    main()
