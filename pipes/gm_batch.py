#!/usr/bin/env python3 -u
"""
gm_batch.py — Gemini Batch API wrapper
T9 OS pipeline. Runs reviews, summaries, and bulk processing via Batch API.

Usage:
  # review (30review)
  python3 T9OS/pipes/gm_batch.py review --input paper.pdf --reviewers 30

  #
  python3 T9OS/pipes/gm_batch.py batch --jsonl requests.jsonl

  #
  python3 T9OS/pipes/gm_batch.py inline --prompts "1" "2" "3"

  # file list summary
  python3 T9OS/pipes/gm_batch.py summarize --files file1.pdf file2.pdf

  # state check
  python3 T9OS/pipes/gm_batch.py status --job batches/123456

  # list
  python3 T9OS/pipes/gm_batch.py list
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# API key — lib/config.py single source
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GEMINI_KEY, OPENAI_KEY

# engine : gm (Gemini, default) cx (OpenAI/Codex)
# . config file CLI.
_ENGINE_FILE = Path(__file__).resolve().parent.parent / ".guardian_engine"
_ENGINE = "gm"

def _load_engine():
    """config filecurrent engine . gm."""
    if _ENGINE_FILE.exists():
        return _ENGINE_FILE.read_text().strip() or "gm"
    return "gm"

def get_client():
    if _ENGINE == "cx":
        return None  # codex CLIsubprocesscall,
    return _get_gemini_client()

def _get_gemini_client():
    from google import genai
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not found", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=GEMINI_KEY)


# ─── review ────────────────────────────────────────

REVIEWER_PRESETS = {
    "economics": [
        {"name": "", "instruction": "   . , structure,     evaluation."},
        {"name": "", "instruction": "  full text. structure,  classify,     evaluation."},
        {"name": "", "instruction": "  full text.  , create,  , items verification   evaluation."},
        {"name": "", "instruction": "  full text. , R&D,      evaluation."},
        {"name": "", "instruction": "  full text. , ,      evaluation."},
        {"name": "", "instruction": "  .  ,  ,  ,     issue."},
        {"name": "", "instruction": "   . ,   ,    evaluation."},
        {"name": "", "instruction": "  .  , ,    analyze  evaluation."},
        {"name": "", "instruction": "  full text.   ,  ,    evaluation."},
        {"name": "OECD", "instruction": " OECD . compare ,  , OECD criteria   evaluation."},
    ],
    "general": [
        {"name": "full text", "instruction": " , statistics analyze,    evaluation."},
        {"name": "", "instruction": "    ,  ,  evaluation."},
        {"name": "full text", "instruction": "    , applied  evaluation."},
        {"name": "review", "instruction": "  review     issue."},
        {"name": "", "instruction": "   scope,  , new  suggestion."},
    ],
    "code": [
        {"name": "", "instruction": "10   code quality, key,  review."},
        {"name": "securityfull text", "instruction": "security full text , auth/,    review."},
        {"name": "", "instruction": "  , optimize ,   review."},
    ],
    # ─── T9 OS guardian ────────────────────────────────────────
    "guardian": [
        {
            "name": "G1_guardian",
            "instruction": (
                " T9 OS  guardian(G1). next criteria evaluation:\n"
                "1. OWASP Top 10 security \n"
                "2. code complexity /  (function 30 ,  3 )\n"
                "3. Build vs Buy violation (npm/pip    implement)\n"
                "4.   missing\n"
                "5. API key/password hardcoded\n"
                "6. unnecessary over-engineering\n"
                "judgment: P0( modify)/P1(session  modify)/P2(next session)/P3(informational). "
                "P0/P1 modify  ."
            ),
        },
        {
            "name": "G2_guardian",
            "instruction": (
                " T9 OS  guardian(G2). project    role.\n"
                "AI  task  /  .\n"
                "next criteria :\n"
                "1. project  / \n"
                "2.    \n"
                "3. use     \n"
                "4.    use \n"
                "5. ' system', 'final version'    (modulation  violation)\n"
                "judgment: CATASTROPHIC( )/WARNING( )/CLEAN. "
                "CATASTROPHIC    modify  ."
            ),
        },
        {
            "name": "G3_ruleguardian",
            "instruction": (
                " T9 OS rule guardian(G3). system rule compliance  .\n"
                " item:\n"
                "1. log file format compliance (YYYYMMDD_CC/CX_NNN_HHMMSS_task.txt)\n"
                "2. original  modify  ()\n"
                "3. Search > Reuse > Buy > Build  compliance\n"
                "4.  access rule (search  ''  )\n"
                "5. previous  file  \n"
                "6. state transition  compliance\n"
                "judgment: 100 .  reason . 80   modify required."
            ),
        },
        {
            "name": "G4_guardian",
            "instruction": (
                " T9 OS  guardian(G4).  artifact   verification.\n"
                " item:\n"
                "1.  :     \n"
                "2.  verification:  / verification  \n"
                "3. :       \n"
                "4. structure: ' →  → applied'  \n"
                "5. :    ±10% \n"
                "6.  : /, /manual  \n"
                "7. '  ≠  ' —      connection\n"
                "judgment: REJECT(  content)/REVISE(structure·· )/PASS( )"
            ),
        },
    ],
    # ─── guardian  (ANCHOR   ) ────────────────────────────────────────
    "philosophy": [
        {
            "name": "",
            "instruction": (
                " (Gilbert Simondon)  full text.\n"
                "Preindividual(préindividuel), Individuating(individuation), disparation(transduction), "
                "modulation(modulation), transductive learning(transductive learning)   analyze.\n"
                " :   Individuating   , "
                " /   ?"
            ),
        },
        {
            "name": "consistency",
            "instruction": (
                " project  consistency  full text.\n"
                "ODNAR: '  infra' ' ' . "
                "required( ,  , Individuating,   ) use  "
                "( , Notion/Obsidian  )  verification.\n"
                "SSK:   . '~ ' .\n"
                "T9OS: ' system', 'final version' .\n"
                " project  // judgment."
            ),
        },
        {
            "name": "monitoring",
            "instruction": (
                " '- ' full text monitoring.\n"
                "/tool/framework     .\n"
                ": 'React  ' →  . 'UX  React optional' → normal.\n"
                "'pipeline   pipeline ' →  task warning.\n"
                "    '?' , final  use  "
                "  WARNING judgment."
            ),
        },
    ],
}

# ─── guardian    (gm batch workers) ────────────────────────────────────────

GUARDIAN_WORKERS = {
    "G1": {
        "name": "guardian",
        "workers": [
            {
                "name": "G1_security",
                "instruction": (
                    " security full text. next / security  .\n"
                    ": OWASP Top 10, APIkey/password hardcoded, SQL injection, XSS, "
                    "auth/ missing, message , CSRF.\n"
                    "found : file, (), (P0/P1/P2), modify  .\n"
                    " 'CLEAN' ."
                ),
            },
            {
                "name": "G1_",
                "instruction": (
                    "   review. code quality .\n"
                    ": function 30 ,  3 , , duplicate , "
                    " ,  , unnecessary .\n"
                    " : , (P0~P3),  ."
                ),
            },
            {
                "name": "G1_BuildVsBuy",
                "instruction": (
                    " Build vs Buy .\n"
                    "  npm/pip/existing library    implement  .\n"
                    ":   ,   library,  difficulty.\n"
                    " 'CLEAN'."
                ),
            },
            {
                "name": "G1_",
                "instruction": (
                    "   full text.\n"
                    ": try-catch missing,  (swallow), use  , "
                    " failed process, null/undefined  missing.\n"
                    " : , , modify  ."
                ),
            },
        ],
    },
    "G2": {
        "name": "guardian",
        "workers": [
            {
                "name": "G2_",
                "instruction": (
                    "  . next      .\n"
                    " list:\n"
                    '- "", " ", "", " ", " ", "second brain"\n'
                    '- "AI ", "AI bot", "AI "\n'
                    '- " record ", " connection"\n'
                    '- "  "\n'
                    '- "Notion ", "Obsidian ", ""\n'
                    '- "    "\n'
                    '- " system", "final version"\n'
                    "found :  (  ),   full text,   suggestion.\n"
                    " 'CLEAN'."
                ),
            },
            {
                "name": "G2_requiredcheck",
                "instruction": (
                    " required check responsible. next  project required  use  check.\n"
                    "ODNAR required:  ,   , , , , "
                    "  , unknown unknowns, -AI-AI-, /mirror\n"
                    " required    report.\n"
                    " required( , unknown unknowns, ) 0 WARNING."
                ),
            },
            {
                "name": "G2_",
                "instruction": (
                    "   .\n"
                    "ODNAR : 3 structure — 1(:), "
                    "2(:→), 3(:AI→).\n"
                    "  ODNAR 1()   CATASTROPHIC.\n"
                    "2  WARNING.\n"
                    "3  CLEAN.\n"
                    "      report."
                ),
            },
            {
                "name": "G2_original",
                "instruction": (
                    " original  .\n"
                    "(CEO)   , AI   .\n"
                    " original pattern: (\"> ...\")  ' original (change )' .\n"
                    "AI     partial  WARNING.\n"
                    " use       CATASTROPHIC."
                ),
            },
        ],
    },
    "G3": {
        "name": "ruleguardian",
        "workers": [
            {
                "name": "G3_logformat",
                "instruction": (
                    " log file format .\n"
                    "rule: YYYYMMDD_CC/CX_NNN_HHMMSS_task.txt\n"
                    "  log file   format compliance  check.\n"
                    "violation :  file,  format ."
                ),
            },
            {
                "name": "G3_SearchReuseBuyBuild",
                "instruction": (
                    " SRBB(Search>Reuse>Buy>Build) .\n"
                    " /  implement  :\n"
                    "1.       ? (Search)\n"
                    "2.  project  use  ? (Reuse)\n"
                    "3.  service/library   ? (Buy)\n"
                    "4. Build   Build?\n"
                    "violation :   ,  ."
                ),
            },
        ],
    },
    "G4": {
        "name": "guardian",
        "workers": [
            {
                "name": "G4_verification",
                "instruction": (
                    "  verification responsible.\n"
                    "  , statistics,    extract verification   .\n"
                    "    WARNING.\n"
                    "   REJECT.\n"
                    " :  ,  , verification result."
                ),
            },
            {
                "name": "G4_structure",
                "instruction": (
                    "  structure/ .\n"
                    ": →→applied , / , /manual , "
                    " (' ' ) .\n"
                    ": , modify ."
                ),
            },
        ],
    },
    "G5": {
        "name": "guardian",
        "workers": [
            {
                "name": "G5_verification",
                "instruction": (
                    "  verification responsible.\n"
                    "     extract  verification.\n"
                    ": / consistency,  error,  , "
                    " structure ,  .\n"
                    "error found :  ,  , modify suggestion."
                ),
            },
            {
                "name": "G5_",
                "instruction": (
                    " →  .\n"
                    "  ()      .\n"
                    ": cosine similarity, pgvector, RSC, embedding, vector, API endpoint .\n"
                    " :  ,      suggestion."
                ),
            },
            {
                "name": "G5_",
                "instruction": (
                    "    check responsible.\n"
                    "    , , use   extract "
                    "   check.\n"
                    "  : WARNING + informational     /report suggestion."
                ),
            },
        ],
    },
    "G6": {
        "name": "guardian",
        "workers": [
            {
                "name": "G6_5test",
                "instruction": (
                    "  5 test responsible.\n"
                    " /    5     .\n"
                    "  partial:  , ,   suggestion.\n"
                    "full text    BLOCK."
                ),
            },
            {
                "name": "G6_",
                "instruction": (
                    "   analyze.\n"
                    "    'report ' ?\n"
                    " (hook) ?  use  ?\n"
                    ":    add  suggestion."
                ),
            },
        ],
    },
    "G7": {
        "name": "guardian",
        "workers": [
            {
                "name": "G7_",
                "instruction": (
                    "   monitoring.\n"
                    " /  , ,    implement  check.\n"
                    "CHOI OD :   (RingGeometry). "
                    "= (AdditiveBlending). = .\n"
                    "violation :   , modify ."
                ),
            },
            {
                "name": "G7_",
                "instruction": (
                    "   . Stripe/Linear/Apple criteria .\n"
                    ": easing ,  ,  ,  , "
                    " ,  tier.\n"
                    "   REJECT. previous PASS."
                ),
            },
        ],
    },
}

# guardian output schema
GUARDIAN_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "worker": {"type": "string", "description": "guardian  name"},
        "guardian": {"type": "string", "description": " guardian (G1~G7)"},
        "verdict": {
            "type": "string",
            "enum": ["CLEAN", "PASS", "WARNING", "BLOCK", "REVISE", "REJECT", "CATASTROPHIC", "VIOLATION", "DRIFT", "ALIGNED"],
            "description": "final judgment"
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "INFO"]},
                    "location": {"type": "string", "description": "file:   "},
                    "description": {"type": "string", "description": " "},
                    "suggestion": {"type": "string", "description": "modify suggestion"}
                },
                "required": ["severity", "description"]
            },
            "description": "found  list"
        },
        "summary": {"type": "string", "description": "1 summary"}
    },
    "required": ["worker", "guardian", "verdict", "issues", "summary"]
}


REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reviewer": {"type": "string", "description": "review name/role"},
        "overall_score": {"type": "integer", "description": "1-10 score"},
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": " list"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "/ list"
        },
        "critical_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "  ()"
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": " modify suggestion"
        },
        "verdict": {
            "type": "string",
            "enum": ["accept", "minor_revision", "major_revision", "reject"],
            "description": "final judgment"
        }
    },
    "required": ["reviewer", "overall_score", "strengths", "weaknesses", "verdict"]
}


# ─── function ────────────────────────────────────────

def build_review_requests(content: str, reviewers: list, model: str) -> list:
    """reviewrequest create ()"""
    requests = []
    for rev in reviewers:
        req = {
            "contents": [{
                "parts": [{"text": f"next content review:\n\n{content}"}],
                "role": "user"
            }],
            "config": {
                "system_instruction": {"parts": [{"text": rev["instruction"]}]},
                "response_mime_type": "application/json",
                "response_schema": REVIEW_OUTPUT_SCHEMA,
                "temperature": 0.7,
            }
        }
        requests.append(req)
    return requests


def build_review_jsonl(content: str, reviewers: list, output_path: str):
    """reviewrequestJSONL filecreate"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, rev in enumerate(reviewers):
            line = {
                "key": f"reviewer-{i+1}-{rev['name']}",
                "request": {
                    "contents": [{
                        "parts": [{"text": f"next content review:\n\n{content}"}],
                        "role": "user"
                    }],
                    "system_instruction": {"parts": [{"text": rev["instruction"]}]},
                    "generation_config": {
                        "response_mime_type": "application/json",
                        "response_schema": REVIEW_OUTPUT_SCHEMA,
                        "temperature": 0.7,
                    }
                }
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return output_path


def submit_inline_batch(client, model: str, requests: list, display_name: str):
    """"""
    job = client.batches.create(
        model=model,
        src=requests,
        config={"display_name": display_name},
    )
    print(f"Created: {job.name}")
    return job


def submit_file_batch(client, model: str, jsonl_path: str, display_name: str):
    """JSONL file → """
    from google.genai import types
    uploaded = client.files.upload(
        file=jsonl_path,
        config=types.UploadFileConfig(
            display_name=display_name,
            mime_type="jsonl"
        )
    )
    print(f"file : {uploaded.name}")

    job = client.batches.create(
        model=model,
        src=uploaded.name,
        config={"display_name": display_name},
    )
    print(f"Created: {job.name}")
    return job


def poll_job(client, job_name: str, interval: int = 10, timeout: int = 3600):
    """task """
    completed = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
    start = time.time()

    while True:
        job = client.batches.get(name=job_name)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] state: {state}")

        if state in completed:
            return job

        if time.time() - start > timeout:
            print(f"ERROR: timeout ({timeout}s)")
            return job

        time.sleep(interval)


def collect_inline_results(job) -> list:
    """result """
    results = []
    if job.dest and job.dest.inlined_responses:
        for i, resp in enumerate(job.dest.inlined_responses):
            if resp.response:
                try:
                    text = resp.response.text
                    data = json.loads(text)
                    results.append(data)
                except (json.JSONDecodeError, AttributeError):
                    results.append({"raw": str(resp.response), "parse_error": True})
            elif resp.error:
                results.append({"error": str(resp.error)})
    return results


def collect_file_results(client, job) -> list:
    """file result """
    results = []
    if job.dest and job.dest.file_name:
        content = client.files.download(file=job.dest.file_name)
        for line in content.decode("utf-8").splitlines():
            if line.strip():
                parsed = json.loads(line)
                if "response" in parsed and parsed["response"]:
                    try:
                        text = parsed["response"]["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(text)
                        data["_key"] = parsed.get("key", "")
                        results.append(data)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        results.append({"_key": parsed.get("key", ""), "raw": str(parsed["response"]), "parse_error": True})
                elif "error" in parsed:
                    results.append({"_key": parsed.get("key", ""), "error": str(parsed["error"])})
    return results


def save_results(results: list, output_path: str, fmt: str = "both"):
    """result save (JSON + MD)"""
    json_path = output_path + ".json"
    md_path = output_path + ".md"

    # JSON
    if fmt in ("json", "both"):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON save: {json_path}")

    # Markdown
    if fmt in ("md", "both"):
        lines = [f"# review result\n", f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n", f"review: {len(results)}\n\n---\n"]

        scores = []
        for r in results:
            if r.get("parse_error") or r.get("error"):
                lines.append(f"\n## [] {r.get('_key', '?')}\n```\n{r}\n```\n")
                continue

            name = r.get("reviewer", r.get("_key", "?"))
            score = r.get("overall_score", "?")
            verdict = r.get("verdict", "?")
            if isinstance(score, int):
                scores.append(score)

            lines.append(f"\n## {name} (score: {score}/10, judgment: {verdict})\n")

            if r.get("strengths"):
                lines.append("\n### \n")
                for s in r["strengths"]:
                    lines.append(f"- {s}\n")

            if r.get("weaknesses"):
                lines.append("\n### \n")
                for w in r["weaknesses"]:
                    lines.append(f"- {w}\n")

            if r.get("critical_issues"):
                lines.append("\n### \n")
                for c in r["critical_issues"]:
                    lines.append(f"- **{c}**\n")

            if r.get("suggestions"):
                lines.append("\n### modify suggestion\n")
                for s in r["suggestions"]:
                    lines.append(f"- {s}\n")

            lines.append("\n---\n")

        # summary statistics
        if scores:
            avg = sum(scores) / len(scores)
            verdicts = [r.get("verdict", "") for r in results if not r.get("error")]
            lines.insert(3, f"\n## summary\n- average score: **{avg:.1f}**/10\n- : {max(scores)}, : {min(scores)}\n")
            for v in ["accept", "minor_revision", "major_revision", "reject"]:
                cnt = verdicts.count(v)
                if cnt:
                    lines.insert(4, f"- {v}: {cnt}\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"MD save: {md_path}")


# ─── CLI ────────────────────────────────────────

def cmd_review(args):
    """/review """
    client = get_client()

    # reviewlist
    preset = args.preset or "general"
    reviewers = REVIEWER_PRESETS.get(preset, REVIEWER_PRESETS["general"])

    # --reviewers N
    if args.reviewers and args.reviewers < len(reviewers):
        reviewers = reviewers[:args.reviewers]

    # reviewadd
    if args.add_reviewer:
        for r in args.add_reviewer:
            name, instruction = r.split(":", 1)
            reviewers.append({"name": name.strip(), "instruction": instruction.strip()})

    print(f"review{len(reviewers)}, : {preset}")
    for r in reviewers:
        print(f"  - {r['name']}")

    # input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    content = input_path.read_text(encoding="utf-8")
    if len(content) > 500000:
        print(f"WARNING: input{len(content)}. JSONL file use.", file=sys.stderr)

    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_name = f"review-{preset}-{ts}"

    # 20inline, JSONL
    if len(reviewers) <= 20 and len(content) < 100000:
        print(": ")
        requests = build_review_requests(content, reviewers, model)
        job = submit_inline_batch(client, model, requests, display_name)
    else:
        print(": JSONL file ")
        jsonl_path = f"/tmp/gm_batch_{ts}.jsonl"
        build_review_jsonl(content, reviewers, jsonl_path)
        job = submit_file_batch(client, model, jsonl_path, display_name)

    #
    if not args.no_wait:
        print("\nstart...")
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)

        if state == "JOB_STATE_SUCCEEDED":
            print("\ncompleted!")
            if job.dest and job.dest.inlined_responses:
                results = collect_inline_results(job)
            else:
                results = collect_file_results(client, job)

            # reviewname mapping
            for i, r in enumerate(results):
                if i < len(reviewers) and "reviewer" not in r:
                    r["reviewer"] = reviewers[i]["name"]

            output_base = args.output or f"_ai/logs/gm/{ts}_review_{preset}"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base)
        else:
            print(f"failed: {state}")
            if hasattr(job, 'error') and job.error:
                print(f": {job.error}")
    else:
        print(f"\ncompleted. check: python3 {__file__} status --job {job.name}")


def _run_guardian_openai(client, model, requests, worker_names, combined):
    """Codex CLI(GPT Plus )guardian execution — G1call (token optimize).

    before: 19 workers x all files = 19 codex calls (token explosion)
    after: merge worker instructions per G = max 7 calls (G1-G7)
    """
    import concurrent.futures
    import subprocess
    import re as _re

    # Gworker
    groups = {}  # {"G1": [(idx, name, instruction), ...], ...}
    for idx, (req, name) in enumerate(zip(requests, worker_names)):
        # name format: "G1_G1_security" → G_id = "G1"
        g_id = name.split("_")[0] if "_" in name else "G?"
        instruction = req["config"]["system_instruction"]["parts"][0]["text"]
        groups.setdefault(g_id, []).append((idx, name, instruction))

    results = [None] * len(requests)

    def call_group(g_id, workers):
        """Gcodex execprocess"""
        # worker
        role_instructions = []
        for _, name, instruction in workers:
            role_instructions.append(f"### {name}\n{instruction}")

        merged_roles = "\n\n".join(role_instructions)
        prompt = (
            f" {g_id} guardian.  {len(workers)} role  .\n"
            f" role  judgment .\n\n"
            f"{merged_roles}\n\n"
            f"---\n\n"
            f"next file .  role result JSON  output.\n"
            f"format: [{{\"worker\": \"name\", \"verdict\": \"PASS/FAIL/WARNING\", \"findings\": [...]}}]\n\n"
            f"{combined}"
        )
        try:
            r = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True, text=True,
                cwd=str(Path(__file__).resolve().parent.parent.parent)
            )
            text = (r.stdout or "").strip()

            # JSON
            try:
                json_match = _re.search(r'\[[\s\S]*\]', text)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if isinstance(parsed, list):
                        # worker mapping
                        for i, (idx, name, _) in enumerate(workers):
                            if i < len(parsed):
                                result = parsed[i] if isinstance(parsed[i], dict) else {"raw": str(parsed[i])[:2000]}
                                result["worker"] = name
                                results[idx] = result
                            else:
                                results[idx] = {"worker": name, "result": {"raw": "response missing"}}
                        return
            except (json.JSONDecodeError, TypeError):
                pass

            # failed → object
            try:
                json_match = _re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    parsed = json.loads(json_match.group())
                    # workerresult
                    for idx, name, _ in workers:
                        results[idx] = {"worker": name, "result": parsed}
                    return
            except (json.JSONDecodeError, TypeError):
                pass

            # failed → raw text
            for idx, name, _ in workers:
                results[idx] = {"worker": name, "result": {"raw": text[:2000]}}

        except Exception as e:
            for idx, name, _ in workers:
                results[idx] = {"worker": name, "error": str(e)}

    # Gexecution (max 7)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(groups), 7)) as executor:
        futures = {executor.submit(call_group, g_id, workers): g_id
                   for g_id, workers in groups.items()}
        for future in concurrent.futures.as_completed(futures):
            g_id = futures[future]
            try:
                future.result()
                worker_count = len(groups[g_id])
                print(f"  ✓ {g_id} ({worker_count}) completed")
            except Exception as e:
                print(f"  ✗ {g_id} failed: {e}")

    return results


def _save_guardian_results(results, worker_names, selected, ts, args):
    """guardian resultCEO briefsave"""
    log_dir = Path(__file__).resolve().parent.parent.parent / "_ai" / "logs" / "gm"
    log_dir.mkdir(parents=True, exist_ok=True)
    brief_path = log_dir / f"{ts}_guardian_brief.md"

    lines = [f"# guardian result (engine: {_ENGINE})", f"****: {ts}", f"**guardian**: {', '.join(selected)}", ""]
    p0_count = 0

    for r in results:
        worker = r.get("worker", "unknown")
        lines.append(f"## {worker}")
        if "error" in r:
            lines.append(f"**ERROR**: {r['error']}")
        else:
            result = r.get("result", {})
            if isinstance(result, dict):
                verdict = result.get("verdict", result.get("judgment", ""))
                findings = result.get("findings", result.get("issues", result.get("found", [])))
                lines.append(f"**judgment**: {verdict}")
                if findings and isinstance(findings, list):
                    for f in findings:
                        if isinstance(f, dict):
                            sev = f.get("severity", f.get("", ""))
                            desc = f.get("description", f.get("content", str(f)))
                            lines.append(f"- [{sev}] {desc}")
                            if sev in ("P0", "CATASTROPHIC"):
                                p0_count += 1
                        else:
                            lines.append(f"- {f}")
                elif isinstance(result.get("raw"), str):
                    lines.append(result["raw"][:500])
            else:
                lines.append(str(result)[:500])
        lines.append("")

    lines.insert(3, f"**P0/CATASTROPHIC**: {p0_count}items\n")
    brief_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nresult save: {brief_path}")
    if p0_count:
        print(f"⚠️ P0/CATASTROPHIC {p0_count}items found!")


def cmd_guardian(args):
    """guardian execution"""
    client = get_client()

    # target file
    contents = []
    for fpath in args.target:
        p = Path(fpath)
        if not p.exists():
            print(f"SKIP: {fpath} not found", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")[:30000]  # token optimize
        contents.append(f"=== file: {p.name} ({len(text)}) ===\n{text}")

    if not contents:
        print("ERROR: file not found", file=sys.stderr)
        sys.exit(1)

    combined = "\n\n".join(contents)

    # guardian optional
    if args.guardians:
        selected = [g.upper() for g in args.guardians]
    elif args.mode == "light":
        selected = ["G1"]
    elif args.mode == "full":
        selected = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    else:
        selected = ["G1", "G2", "G3"]  # default

    # ANCHOR (per-project)
    anchor_text = ""
    if args.anchor:
        anchor_path = Path(args.anchor)
        if anchor_path.exists():
            anchor_text = anchor_path.read_text(encoding="utf-8", errors="replace")[:30000]

    # request create
    requests = []
    worker_names = []
    for gid in selected:
        guardian = GUARDIAN_WORKERS.get(gid)
        if not guardian:
            print(f"SKIP: {gid} not found", file=sys.stderr)
            continue
        for worker in guardian["workers"]:
            instruction = worker["instruction"]
            if anchor_text and gid == "G2":
                instruction += f"\n\n[ANCHOR ]\n{anchor_text[:10000]}"

            req = {
                "contents": [{
                    "parts": [{"text": f"next file :\n\n{combined}"}],
                    "role": "user"
                }],
                "config": {
                    "system_instruction": {"parts": [{"text": instruction}]},
                    "response_mime_type": "application/json",
                    "response_schema": GUARDIAN_OUTPUT_SCHEMA,
                    "temperature": 0.3,
                }
            }
            requests.append(req)
            worker_names.append(f"{gid}_{worker['name']}")

    print(f"guardian {len(selected)}, {len(requests)}execution (engine: {_ENGINE})")
    for gid in selected:
        g = GUARDIAN_WORKERS.get(gid)
        if g:
            workers = [w["name"] for w in g["workers"]]
            print(f"  {gid} {g['name']}: {', '.join(workers)}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_name = f"guardian-{'-'.join(selected)}-{ts}"

    if _ENGINE == "cx":
        # OpenAI/Codex engine: call (API call)
        model = args.model or "o4-mini"  # codex CLImodel (--full-auto)
        results = _run_guardian_openai(client, model, requests, worker_names, combined)
        _save_guardian_results(results, worker_names, selected, ts, args)
        return

    model = args.model or "gemini-3-flash-preview"
    job = submit_inline_batch(client, model, requests, display_name)

    if not args.no_wait:
        print(f"\nstart... ({len(requests)}items)")
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)

        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)

            # worker name mapping
            for i, r in enumerate(results):
                if i < len(worker_names):
                    if isinstance(r, dict) and "worker" not in r:
                        r["worker"] = worker_names[i]

            # CEO brief create
            p0_issues = []
            all_issues = []
            for r in results:
                if isinstance(r, dict) and "issues" in r:
                    for issue in r.get("issues", []):
                        if isinstance(issue, dict):
                            all_issues.append(issue)
                            if issue.get("severity") == "P0":
                                p0_issues.append({
                                    "worker": r.get("worker", "?"),
                                    "description": issue.get("description", ""),
                                    "suggestion": issue.get("suggestion", ""),
                                })

            # save
            output_base = args.output or f"_ai/logs/gm/{ts}_guardian"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)

            # JSON
            with open(output_base + ".json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            # CEO brief ()
            brief_lines = [
                f"# guardian CEO brief\n",
                f"execution: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
                f"guardian: {', '.join(selected)} |  {len(requests)} |  {len(all_issues)}items\n\n",
            ]

            if p0_issues:
                brief_lines.append(f"## P0 modify ({len(p0_issues)}items)\n\n")
                for p in p0_issues:
                    brief_lines.append(f"- **[{p['worker']}]** {p['description']}\n")
                    if p['suggestion']:
                        brief_lines.append(f"  → {p['suggestion']}\n")
                brief_lines.append("\n")
            else:
                brief_lines.append("## P0 not found — modify \n\n")

            # guardiansummary
            brief_lines.append("## guardianjudgment\n\n")
            brief_lines.append("|  | judgment | summary |\n|---|---|---|\n")
            for r in results:
                if isinstance(r, dict):
                    name = r.get("worker", "?")
                    verdict = r.get("verdict", "?")
                    summary = r.get("summary", "")
                    brief_lines.append(f"| {name} | {verdict} | {summary} |\n")

            with open(output_base + "_brief.md", "w", encoding="utf-8") as f:
                f.writelines(brief_lines)

            print(f"\n{'='*50}")
            print(f"guardian completed: {len(all_issues)}items (P0: {len(p0_issues)}items)")
            print(f"JSON: {output_base}.json")
            print(f"CEO brief: {output_base}_brief.md")
            print(f"{'='*50}")

            # P0 output
            if p0_issues:
                print(f"\n⚠️  P0 {len(p0_issues)}items found:")
                for p in p0_issues:
                    print(f"  [{p['worker']}] {p['description']}")
        else:
            print(f"failed: {state}")
    else:
        print(f"\ncompleted. check: python3 {__file__} status --job {job.name}")


def cmd_batch(args):
    """JSONL file"""
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    job = submit_file_batch(client, model, args.jsonl, f"batch-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_file_results(client, job)
            output_base = args.output or f"_ai/logs/gm/{ts}_batch"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base, fmt="json")
            print(f"result {len(results)}items save completed")


def cmd_inline(args):
    """"""
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    requests = []
    for prompt in args.prompts:
        requests.append({
            "contents": [{"parts": [{"text": prompt}], "role": "user"}]
        })

    job = submit_inline_batch(client, model, requests, f"inline-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)
            for i, r in enumerate(results):
                print(f"\n--- Response {i+1} ---")
                print(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, indent=2))


def cmd_summarize(args):
    """file list summary """
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    requests = []
    for fpath in args.files:
        p = Path(fpath)
        if not p.exists():
            print(f"SKIP: {fpath} not found", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")[:100000]
        requests.append({
            "contents": [{
                "parts": [{"text": f"next  800~1000 summary. title,  , , result,  .\n\nfile: {p.name}\n\n{text}"}],
                "role": "user"
            }]
        })

    if not requests:
        print("summaryfile not found")
        return

    print(f"{len(requests)}items summary ")
    job = submit_inline_batch(client, model, requests, f"summarize-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)
            output_base = args.output or f"_ai/logs/gm/{ts}_summarize"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            with open(output_base + ".md", "w", encoding="utf-8") as f:
                f.write(f"# summary result ({len(results)}items)\n\n")
                for i, r in enumerate(results):
                    fname = args.files[i] if i < len(args.files) else f"file {i+1}"
                    f.write(f"## {Path(fname).name}\n\n")
                    if isinstance(r, dict) and r.get("parse_error"):
                        f.write(f"```\n{r.get('raw', 'error')}\n```\n\n")
                    elif isinstance(r, str):
                        f.write(f"{r}\n\n")
                    else:
                        f.write(f"{json.dumps(r, ensure_ascii=False, indent=2)}\n\n")
                    f.write("---\n\n")
            print(f"save: {output_base}.md")


def cmd_status(args):
    """state check"""
    client = get_client()
    job = client.batches.get(name=args.job)
    state = job.state.name if hasattr(job.state, 'name') else str(job.state)
    print(f"name: {job.name}")
    print(f"state: {state}")
    if hasattr(job, 'display_name'):
        print(f": {job.display_name}")
    if state == "JOB_STATE_SUCCEEDED" and args.download:
        if job.dest and job.dest.inlined_responses:
            results = collect_inline_results(job)
        elif job.dest and job.dest.file_name:
            results = collect_file_results(client, job)
        else:
            results = []
        if results:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_base = args.output or f"_ai/logs/gm/{ts}_download"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base)


def cmd_list(args):
    """list"""
    client = get_client()
    jobs = client.batches.list(config={"page_size": args.limit or 10})
    for job in jobs:
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        name = getattr(job, 'display_name', '')
        print(f"  {job.name}  [{state}]  {name}")


def cmd_cancel(args):
    """"""
    client = get_client()
    client.batches.cancel(name=args.job)
    print(f": {args.job}")


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="gm_batch — Gemini/OpenAI Batch API ")
    parser.add_argument("--model", "-m", default=None, help="model (default: engine  auto)")
    parser.add_argument("--engine", "-e", choices=["gm", "cx"], default="gm", help="engine: gm(Gemini), cx(OpenAI/Codex)")
    parser.add_argument("--poll-interval", type=int, default=10, help=" ()")
    parser.add_argument("--no-wait", action="store_true", help="    ")
    parser.add_argument("--output", "-o", default=None, help="output path ( )")

    sub = parser.add_subparsers(dest="command")

    # guardian
    p_guard = sub.add_parser("guardian", help="guardian   execution")
    p_guard.add_argument("--target", "-t", nargs="+", required=True, help=" target file")
    p_guard.add_argument("--guardians", "-g", nargs="+", help="execution guardian (G1 G2 G3 ...)")
    p_guard.add_argument("--mode", choices=["light", "default", "full"], default="default", help="light/default/total")
    p_guard.add_argument("--anchor", "-a", help="ANCHOR  path (G2 )")

    # review
    p_review = sub.add_parser("review", help="/ review ")
    p_review.add_argument("--input", "-i", required=True, help="review target file")
    p_review.add_argument("--preset", "-p", choices=list(REVIEWER_PRESETS.keys()), default="general", help="review ")
    p_review.add_argument("--reviewers", "-n", type=int, help="review  ")
    p_review.add_argument("--add-reviewer", action="append", help=" review add (name:)")

    # batch
    p_batch = sub.add_parser("batch", help="JSONL file  ")
    p_batch.add_argument("--jsonl", "-j", required=True, help="JSONL file path")

    # inline
    p_inline = sub.add_parser("inline", help="  ")
    p_inline.add_argument("--prompts", nargs="+", required=True, help=" list")

    # summarize
    p_summ = sub.add_parser("summarize", help="file list summary")
    p_summ.add_argument("--files", "-f", nargs="+", required=True, help="file path list")

    # status
    p_status = sub.add_parser("status", help=" state check")
    p_status.add_argument("--job", "-j", required=True, help=" name (batches/...)")
    p_status.add_argument("--download", "-d", action="store_true", help="completed  result ")

    # list
    p_list = sub.add_parser("list", help=" list")
    p_list.add_argument("--limit", "-l", type=int, default=10)

    # cancel
    p_cancel = sub.add_parser("cancel", help=" ")
    p_cancel.add_argument("--job", "-j", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # engine config: CLI > config file > defaultvalue(gm)
    global _ENGINE
    if args.engine != "gm":  # CLI
        _ENGINE = args.engine
    else:
        _ENGINE = _load_engine()  # config file

    cmd_map = {
        "guardian": cmd_guardian,
        "review": cmd_review,
        "batch": cmd_batch,
        "inline": cmd_inline,
        "summarize": cmd_summarize,
        "status": cmd_status,
        "list": cmd_list,
        "cancel": cmd_cancel,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
