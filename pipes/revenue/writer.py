#!/usr/bin/env python3
"""AI tool review article generator — powered by Gemini (free tier).

Picks tools with article_generated=0 from revenue.db and generates
SEO-optimized review articles in Markdown with affiliate placeholders.

Usage:
    python3 T9OS/pipes/revenue/writer.py              # generate for all pending
    python3 T9OS/pipes/revenue/writer.py --limit 5    # limit batch size
    python3 T9OS/pipes/revenue/writer.py --id 42      # specific tool ID
    python3 T9OS/pipes/revenue/writer.py --dry-run    # preview without saving
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# ── T9OS imports ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lib.config import GEMINI_KEY  # noqa: E402
from lib.logger import pipeline_run, record  # noqa: E402

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# ── Constants ─────────────────────────────────────────────────────
DB_PATH = Path.home() / ".t9os_data" / "revenue.db"
ARTICLES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "revenue" / "articles"

LOG = logging.getLogger("revenue.writer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# Gemini model — use latest stable
GEMINI_MODEL = "gemini-2.0-flash-001"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _redact_url(url: str) -> str:
    """Redact API keys from URLs before logging."""
    return re.sub(r'(key=)[^&\s]+', r'\1[REDACTED]', url)


def _redact_exc(exc: Exception) -> str:
    """Redact API keys from exception messages."""
    return re.sub(r'(key=)[^&\s]+', r'\1[REDACTED]', str(exc))


# ── Gemini client (stdlib only, no SDK dependency) ────────────────
def _call_gemini(prompt: str, max_tokens: int = 4096) -> str | None:
    """Call Gemini API using urllib (zero external deps)."""
    if not GEMINI_KEY:
        LOG.error("GEMINI_KEY not set. Cannot generate articles.")
        return None

    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        },
    }

    import urllib.request
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                LOG.warning("Gemini returned empty response")
                return None
        except Exception as exc:
            LOG.warning("Gemini attempt %d failed: %s", attempt + 1, _redact_exc(exc))
            if attempt < 2:
                time.sleep(3 * (attempt + 1))

    return None


# ── Article generation ────────────────────────────────────────────
ARTICLE_PROMPT = dedent("""\
    You are an expert tech reviewer writing for a popular AI tools blog.
    Write a compelling, honest, SEO-optimized article about this AI tool.

    TITLE RULES (critical for click-through):
    - Make titles irresistible. Use curiosity gaps, numbers, or bold claims.
    - Good: "This $0 Tool Just Made Cursor Look Expensive", "I Replaced 3 Apps With This One AI Tool"
    - Bad: "[Tool] Review: [Feature] — Is It Worth It in 2026?"
    - NEVER use generic review title format. Each title must be unique and hooking.

    SUMMARY (required, right after title):
    - Start every article with a bold 1-2 sentence summary in italics
    - This summary should make people want to read the full article
    - Example: *"A solo developer built an AI that writes better code than GitHub Copilot — and it's completely free."*

    Tool Name: {name}
    Tool URL: {url}
    Description: {description}
    Category: {category}
    Source: {source}
    Upvotes/Popularity: {upvotes}

    ARTICLE STRUCTURE:
    Pick ONE of these formats randomly — do NOT always use the same one:

    FORMAT A (Review):
    # [Tool] Review: [Benefit] — Worth It in 2026?
    → TL;DR → What it does → Features (bullets) → Pros/Cons → Pricing → Verdict

    FORMAT B (Comparison):
    # [Tool] vs [Competitor]: Which One Should You Pick?
    → Quick answer → Side-by-side table → Deep dive each → Winner by use case

    FORMAT C (Guide):
    # How to [Solve Problem] with [Tool] — Step-by-Step
    → The problem → Why this tool → Tutorial steps → Tips → Alternatives

    FORMAT D (Listicle):
    # [Number] Things You Should Know About [Tool] Before Signing Up
    → Numbered insights → Each with detail paragraph → Bottom line

    FORMAT E (Story):
    # I Tested [Tool] for a Week — Here's What Happened
    → First impression → Day-by-day experience → What worked → What didn't → Would I pay?

    Include this affiliate placeholder naturally: {{{{AFFILIATE_LINK}}}}

    RULES:
    - Vary your tone: sometimes casual, sometimes analytical, sometimes enthusiastic
    - Be honest — mention limitations, don't oversell
    - Include the tool name naturally 3-5 times for SEO
    - Output ONLY the markdown article, no meta-commentary
    - Do NOT wrap in code blocks
    - Use proper markdown formatting
    - Article length: vary between 600-1500 words (not always the same)
    - NEVER start two articles the same way
""")


def _quality_check(content: str, tool_name: str) -> tuple[bool, list[str]]:
    """글 감시단 — 트래픽+신뢰도 기준 자동 검수."""
    issues = []
    words = content.split()
    word_count = len(words)

    # 1. 길이 체크
    if word_count < 400:
        issues.append(f"too_short({word_count}w)")
    if word_count > 2000:
        issues.append(f"too_long({word_count}w)")

    # 2. 제목 후킹 체크 — generic 제목 감지
    first_line = content.strip().split("\n")[0]
    boring_patterns = ["Review:", "Is It Worth", "— A Review", "An Overview", "A Comprehensive"]
    if any(p.lower() in first_line.lower() for p in boring_patterns):
        issues.append("boring_title")

    # 3. 요약 존재 체크 — 첫 5줄 안에 이탤릭(*) 요약이 있어야 함
    first_lines = "\n".join(content.strip().split("\n")[:8])
    if "*" not in first_lines:
        issues.append("no_summary")

    # 4. 구조 체크 — h2가 최소 3개
    h2_count = content.count("\n## ")
    if h2_count < 3:
        issues.append(f"weak_structure(h2={h2_count})")

    # 5. 도구명 SEO 체크 — 본문에 3회 이상
    name_lower = tool_name.lower().split("–")[0].split("—")[0].strip()
    if len(name_lower) > 3:
        name_count = content.lower().count(name_lower)
        if name_count < 3:
            issues.append(f"low_seo(name={name_count})")

    # 6. AI 냄새 체크 — 과도한 AI 문투
    ai_smell = ["in conclusion", "it's worth noting", "in today's rapidly",
                "in the ever-evolving", "dive into", "game-changer",
                "revolutionize", "cutting-edge", "landscape"]
    smell_count = sum(1 for phrase in ai_smell if phrase in content.lower())
    if smell_count >= 3:
        issues.append(f"ai_smell({smell_count})")

    # 7. 어필리에이트 링크 플레이스홀더 존재
    if "AFFILIATE_LINK" not in content:
        issues.append("no_affiliate_placeholder")

    passed = len(issues) == 0
    return passed, issues


def generate_article(tool: dict, max_attempts: int = 3) -> str | None:
    """Generate a review article with quality gate."""
    prompt = ARTICLE_PROMPT.format(
        name=tool["name"],
        url=tool["url"],
        description=tool["description"] or "No description available",
        category=tool["category"],
        source=tool["source"],
        upvotes=tool["upvotes"],
    )

    for attempt in range(max_attempts):
        LOG.info("Generating article for: %s (attempt %d)", tool["name"], attempt + 1)
        content = _call_gemini(prompt, max_tokens=4096)

        if not content:
            LOG.error("Failed to generate article for: %s", tool["name"])
            continue

        # 감시단 검수
        passed, issues = _quality_check(content, tool["name"])
        if passed:
            LOG.info("Quality check PASSED for: %s", tool["name"])
            frontmatter = _build_frontmatter(tool, content)
            return f"{frontmatter}\n\n{content.strip()}\n"

        LOG.warning("Quality check FAILED (%s): %s — retrying", tool["name"], ", ".join(issues))

        # 재생성 시 이슈 피드백 추가
        if attempt < max_attempts - 1:
            prompt += f"\n\nPREVIOUS ATTEMPT FAILED QUALITY CHECK. Fix these: {', '.join(issues)}. "
            if "boring_title" in issues:
                prompt += "Make the title MORE provocative and clickable. "
            if "no_summary" in issues:
                prompt += "Add an italic *summary* in the first 2 lines. "
            if "ai_smell" in issues:
                prompt += "Write more naturally. Avoid cliché phrases like 'game-changer', 'dive into', 'landscape'. "

    LOG.error("All %d attempts failed quality check for: %s", max_attempts, tool["name"])
    return None


def _build_frontmatter(tool: dict, content: str) -> str:
    """Build YAML frontmatter for SEO."""
    # Extract title from generated content
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title_raw = title_match.group(1).strip() if title_match else f"{tool['name']} Review"
    # Escape for YAML double-quoted scalar
    title = title_raw.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')

    # Generate description from first paragraph after title
    desc_raw = tool["description"][:160] if tool["description"] else title[:160]
    # Escape for YAML double-quoted scalar
    desc = desc_raw.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')

    # Slugify for filename
    slug = _slugify(tool["name"])
    date = datetime.now().strftime("%Y-%m-%d")

    tags_raw = json.loads(tool["tags"]) if isinstance(tool["tags"], str) else tool.get("tags", [])
    tags = ["AI", "tool-review"] + [t for t in tags_raw if t not in ("AI",)]

    return dedent(f"""\
        ---
        title: "{title}"
        date: {date}
        description: "{desc}"
        tags: {json.dumps(tags)}
        slug: "{slug}-review"
        affiliate_placeholder: true
        ---""")


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


def _save_article(tool: dict, article: str) -> Path:
    """Save article as markdown file."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(tool["name"])
    date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date}-{slug}-review.md"
    filepath = ARTICLES_DIR / filename

    filepath.write_text(article, encoding="utf-8")
    LOG.info("Article saved: %s", filepath)
    return filepath


def _mark_generated(conn: sqlite3.Connection, tool_id: int) -> None:
    """Mark tool as article_generated=1."""
    conn.execute(
        "UPDATE tools SET article_generated = 1 WHERE id = ?",
        (tool_id,),
    )
    conn.commit()


# ── Orchestrator ──────────────────────────────────────────────────
def run_writer(
    limit: int = 10,
    tool_id: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Generate articles for pending tools. Returns stats."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    if tool_id:
        rows = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM tools
               WHERE article_generated = 0
               ORDER BY upvotes DESC, discovered_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

    if not rows:
        LOG.info("No pending tools for article generation.")
        conn.close()
        return {"generated": 0, "failed": 0}

    generated = 0
    failed = 0

    for row in rows:
        tool = dict(row)
        article = generate_article(tool)

        if article:
            if not dry_run:
                path = _save_article(tool, article)
                _mark_generated(conn, tool["id"])
                LOG.info("Done: %s → %s", tool["name"], path.name)
            else:
                print(f"\n{'='*60}")
                print(f"PREVIEW: {tool['name']}")
                print(f"{'='*60}")
                print(article[:500] + "...\n")
            generated += 1
        else:
            failed += 1

        # Rate limit: Gemini free tier = 15 RPM for flash
        if not dry_run:
            time.sleep(5)

    conn.close()
    return {"generated": generated, "failed": failed}


# ── CLI ───────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="AI Tool Review Writer")
    parser.add_argument("--limit", type=int, default=10, help="Max articles to generate")
    parser.add_argument("--id", type=int, help="Generate for specific tool ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    with pipeline_run("revenue_writer", notify_on_fail=False):
        stats = run_writer(limit=args.limit, tool_id=args.id, dry_run=args.dry_run)
        LOG.info("Writer complete: %s", stats)
        record("revenue_writer", "OK", json.dumps(stats))


if __name__ == "__main__":
    main()
