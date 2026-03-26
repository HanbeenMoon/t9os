#!/usr/bin/env python3
"""SEO keyword discovery + keyword-driven article generation.

Discovers trending AI-related long-tail keywords from Google Trends,
generates targeted articles for high-intent search queries.

Usage:
    python3 T9OS/pipes/revenue/seo_keyword.py                  # discover + generate
    python3 T9OS/pipes/revenue/seo_keyword.py --discover-only   # keywords only
    python3 T9OS/pipes/revenue/seo_keyword.py --list            # show keyword DB
    python3 T9OS/pipes/revenue/seo_keyword.py --generate --limit 3
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
import xml.etree.ElementTree as ET
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

LOG = logging.getLogger("revenue.seo")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

GEMINI_MODEL = "gemini-2.0-flash-001"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _redact_url(url: str) -> str:
    """Redact API keys from URLs before logging."""
    return re.sub(r'(key=)[^&\s]+', r'\1[REDACTED]', url)


def _redact_exc(exc: Exception) -> str:
    """Redact API keys from exception messages."""
    return re.sub(r'(key=)[^&\s]+', r'\1[REDACTED]', str(exc))


# ── DB layer ──────────────────────────────────────────────────────
def _init_keywords_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seo_keywords (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword         TEXT NOT NULL UNIQUE,
            pattern         TEXT NOT NULL DEFAULT '',
            source          TEXT NOT NULL DEFAULT '',
            search_volume   TEXT NOT NULL DEFAULT 'unknown',
            discovered_at   TEXT NOT NULL DEFAULT (datetime('now')),
            article_generated INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kw_generated ON seo_keywords(article_generated)
    """)
    conn.commit()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_keywords_table(conn)
    return conn


def insert_keyword(conn: sqlite3.Connection, keyword: str, pattern: str, source: str) -> bool:
    """Insert keyword if not duplicate. Returns True if inserted."""
    try:
        conn.execute(
            "INSERT INTO seo_keywords (keyword, pattern, source) VALUES (?, ?, ?)",
            (keyword.lower().strip(), pattern, source),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ── Gemini helper (reuse from writer) ─────────────────────────────
def _call_gemini(prompt: str, max_tokens: int = 4096) -> str | None:
    import urllib.request
    if not GEMINI_KEY:
        LOG.error("GEMINI_KEY not set")
        return None

    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
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
        except Exception as exc:
            LOG.warning("Gemini attempt %d: %s", attempt + 1, _redact_exc(exc))
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    return None


# ── Keyword discovery sources ─────────────────────────────────────

# Pattern templates for long-tail AI keywords
KEYWORD_PATTERNS = [
    "best AI tool for {topic}",
    "AI vs traditional {topic}",
    "how to automate {topic} with AI",
    "top {topic} AI tools 2026",
    "free AI {topic} generator",
    "AI {topic} assistant review",
    "{topic} AI software comparison",
    "is AI {topic} worth it",
    "AI tools for {topic} beginners",
    "best free AI {topic} alternatives",
]

# Topic seeds — expand via Google Trends
TOPIC_SEEDS = [
    "writing", "coding", "design", "marketing", "sales", "email",
    "video editing", "image generation", "data analysis", "customer support",
    "content creation", "social media", "SEO", "spreadsheets", "presentations",
    "music", "voice", "translation", "scheduling", "research",
    "meeting notes", "project management", "HR", "legal", "accounting",
    "education", "healthcare", "real estate", "ecommerce", "recruiting",
]


def discover_pattern_keywords(conn: sqlite3.Connection) -> int:
    """Generate long-tail keywords from pattern templates + topic seeds."""
    LOG.info("Generating pattern-based keywords...")
    new_count = 0
    for topic in TOPIC_SEEDS:
        for pattern in KEYWORD_PATTERNS:
            keyword = pattern.format(topic=topic)
            if insert_keyword(conn, keyword, pattern, "pattern_template"):
                new_count += 1
    LOG.info("Pattern keywords: %d new", new_count)
    return new_count


def discover_google_trends(conn: sqlite3.Connection) -> int:
    """Fetch trending topics from Google Trends RSS and extract AI-related ones."""
    LOG.info("Fetching Google Trends...")
    import urllib.request

    # Google Trends daily trending RSS for US
    trends_url = "https://trends.google.com/trending/rss?geo=US"
    new_count = 0

    try:
        req = urllib.request.Request(trends_url, headers={"User-Agent": "T9OS/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_data = resp.read().decode("utf-8")

        root = ET.fromstring(xml_data)
        # RSS items are in channel/item
        ns = {"ht": "https://trends.google.com/trends/trendingsearches/daily"}
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items:
            title_el = item.find("title")
            if title_el is None or title_el.text is None:
                continue
            title = title_el.text.strip()

            # Check if AI-related
            ai_kw_re = re.compile(r"\b(ai|artificial intelligence|chatgpt|openai|claude|gemini|copilot|llm)\b", re.I)
            if ai_kw_re.search(title):
                # Generate derivative keywords
                derivatives = [
                    f"{title} review",
                    f"best {title} alternatives",
                    f"{title} vs competitors",
                    f"how to use {title}",
                    f"is {title} free",
                ]
                for kw in derivatives:
                    if insert_keyword(conn, kw, "trends_derivative", "google_trends"):
                        new_count += 1
    except Exception as exc:
        LOG.warning("Google Trends fetch failed: %s", exc)

    LOG.info("Google Trends keywords: %d new", new_count)
    return new_count


def discover_gemini_expansion(conn: sqlite3.Connection) -> int:
    """Use Gemini to suggest additional high-intent keywords."""
    LOG.info("Gemini keyword expansion...")

    prompt = dedent("""\
        You are an SEO expert. Generate 30 high-intent, long-tail search queries
        that people would type into Google when looking for AI tools in 2026.

        Focus on:
        - Buyer intent queries ("best X for Y", "X vs Y", "X pricing")
        - Problem-solution queries ("how to automate X with AI")
        - Comparison queries ("top AI tools for X")
        - Niche-specific queries (not generic)

        Output as a JSON array of strings, nothing else.
        Example: ["best AI writing tool for bloggers", "AI video editor free no watermark"]
    """)

    response = _call_gemini(prompt, max_tokens=2000)
    if not response:
        return 0

    # Parse JSON array from response
    try:
        # Handle markdown code blocks
        cleaned = re.sub(r"```json\s*|\s*```", "", response).strip()
        keywords = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try line-by-line extraction
        keywords = [line.strip().strip('",-[]') for line in response.splitlines() if line.strip()]
        keywords = [k for k in keywords if len(k) > 10 and len(k) < 100]

    new_count = 0
    for kw in keywords:
        if isinstance(kw, str) and kw.strip():
            if insert_keyword(conn, kw, "gemini_expansion", "gemini"):
                new_count += 1

    LOG.info("Gemini expansion: %d new keywords", new_count)
    return new_count


# ── Keyword-driven article generation ─────────────────────────────
SEO_ARTICLE_PROMPT = dedent("""\
    You are a professional tech blogger writing SEO-optimized content about AI tools.
    Write a comprehensive article targeting this exact search query as the primary keyword:

    TARGET KEYWORD: "{keyword}"

    ARTICLE STRUCTURE:

    1. **Title (H1)**: Include the exact keyword naturally. Make it compelling.
       Format: "# [Title with keyword]"

    2. **Introduction** (100-150 words): Hook the reader, state the problem, promise the solution.
       Naturally include the keyword in the first paragraph.

    3. **Main Content** (600-800 words): Based on the keyword intent:
       - If "best X for Y": List and review 5-7 tools with pros/cons
       - If "X vs Y": Detailed comparison with winner for each use case
       - If "how to X with AI": Step-by-step guide with tool recommendations
       - If review/alternative: In-depth analysis with alternatives table

    4. **Comparison Table**: Markdown table comparing relevant tools.

    5. **FAQ Section**: 3-4 questions people also ask (H2: "Frequently Asked Questions")

    6. **Conclusion**: Summary + clear recommendation + CTA

    RULES:
    - Include the target keyword 4-6 times naturally (not stuffed)
    - Use H2 and H3 headers for structure
    - Include {{{{AFFILIATE_LINK}}}} placeholder where tool links appear
    - Conversational but authoritative tone
    - 1000-1500 words total
    - Output ONLY markdown, no meta-commentary
    - Do NOT wrap in code blocks
    - Current year is 2026
""")


def generate_keyword_article(keyword: str) -> str | None:
    """Generate an SEO article targeting a specific keyword."""
    prompt = SEO_ARTICLE_PROMPT.format(keyword=keyword)
    content = _call_gemini(prompt, max_tokens=5000)
    if not content:
        return None

    # Build frontmatter
    slug = re.sub(r"[^\w\s-]", "", keyword.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")[:60]
    date = datetime.now().strftime("%Y-%m-%d")

    # Extract title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title_raw = title_match.group(1).strip() if title_match else keyword.title()
    # Escape for YAML double-quoted scalar
    title = title_raw.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    desc_raw = f"{keyword.capitalize()} — comprehensive guide and comparison for 2026"
    desc = desc_raw.replace('\\', '\\\\').replace('"', '\\"')

    frontmatter = dedent(f"""\
        ---
        title: "{title}"
        date: {date}
        description: "{desc}"
        tags: ["AI", "SEO", "tool-comparison"]
        slug: "{slug}"
        target_keyword: "{keyword}"
        affiliate_placeholder: true
        ---""")

    return f"{frontmatter}\n\n{content.strip()}\n"


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:60]


def run_generate(limit: int = 5, dry_run: bool = False) -> dict[str, int]:
    """Generate articles for pending keywords."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM seo_keywords
           WHERE article_generated = 0
           ORDER BY discovered_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    if not rows:
        LOG.info("No pending keywords.")
        conn.close()
        return {"generated": 0, "failed": 0}

    generated = 0
    failed = 0

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        kw = dict(row)
        LOG.info("Generating article for keyword: %s", kw["keyword"])

        article = generate_keyword_article(kw["keyword"])
        if article:
            if not dry_run:
                slug = _slugify(kw["keyword"])
                date = datetime.now().strftime("%Y-%m-%d")
                filepath = ARTICLES_DIR / f"{date}-seo-{slug}.md"
                filepath.write_text(article, encoding="utf-8")

                conn.execute(
                    "UPDATE seo_keywords SET article_generated = 1 WHERE id = ?",
                    (kw["id"],),
                )
                conn.commit()
                LOG.info("Saved: %s", filepath.name)
            else:
                print(f"\n{'='*60}")
                print(f"KEYWORD: {kw['keyword']}")
                print(f"{'='*60}")
                print(article[:400] + "...\n")
            generated += 1
        else:
            failed += 1

        time.sleep(5)  # Gemini rate limit

    conn.close()
    return {"generated": generated, "failed": failed}


# ── CLI ───────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="SEO Keyword Discovery & Article Generation")
    parser.add_argument("--discover-only", action="store_true", help="Only discover keywords, don't generate")
    parser.add_argument("--generate", action="store_true", help="Only generate articles for existing keywords")
    parser.add_argument("--list", action="store_true", help="List all keywords")
    parser.add_argument("--limit", type=int, default=5, help="Max articles to generate")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    args = parser.parse_args()

    conn = get_db()

    if args.list:
        rows = conn.execute(
            "SELECT * FROM seo_keywords ORDER BY discovered_at DESC"
        ).fetchall()
        for r in rows:
            status = "done" if r["article_generated"] else "pending"
            print(f"[{status}] {r['keyword']} ({r['source']})")
        print(f"\nTotal: {len(rows)}")
        conn.close()
        return

    with pipeline_run("revenue_seo", notify_on_fail=False):
        # Discovery phase
        if not args.generate:
            total_new = 0
            total_new += discover_pattern_keywords(conn)
            total_new += discover_google_trends(conn)
            if GEMINI_KEY:
                total_new += discover_gemini_expansion(conn)
            LOG.info("Discovery complete: %d new keywords", total_new)

        conn.close()

        # Generation phase
        if not args.discover_only:
            stats = run_generate(limit=args.limit, dry_run=args.dry_run)
            LOG.info("Generation complete: %s", stats)
            record("revenue_seo", "OK", json.dumps(stats))


if __name__ == "__main__":
    main()
