#!/usr/bin/env python3
"""AI tool discovery crawler — Product Hunt, Hacker News, Reddit.

Discovers new AI tools daily, deduplicates by URL, stores in SQLite.
Designed for cron: `0 8 * * * python3 T9OS/pipes/revenue/crawler.py`

Usage:
    python3 T9OS/pipes/revenue/crawler.py              # crawl all sources
    python3 T9OS/pipes/revenue/crawler.py --source ph   # Product Hunt only
    python3 T9OS/pipes/revenue/crawler.py --source hn   # Hacker News only
    python3 T9OS/pipes/revenue/crawler.py --source reddit
    python3 T9OS/pipes/revenue/crawler.py --list        # show recent discoveries
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
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# ── T9OS imports ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lib.config import GEMINI_KEY, GITHUB_TOKEN  # noqa: E402
from lib.logger import pipeline_run, log_error, record  # noqa: E402

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# ── Constants ─────────────────────────────────────────────────────
DB_PATH = Path.home() / ".t9os_data" / "revenue.db"
LOG = logging.getLogger("revenue.crawler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

USER_AGENT = "T9OS-Revenue-Crawler/1.0 (github.com/t9os)"
REQUEST_TIMEOUT = 20
import html as html_module
import ipaddress
import socket


def _sanitize_text(text: str) -> str:
    """Strip HTML tags, script/iframe elements, and escape special characters."""
    if not text:
        return ""
    # Remove script/iframe blocks (including content)
    text = re.sub(r'<\s*(script|iframe)[^>]*>.*?</\s*\1\s*>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove self-closing script/iframe
    text = re.sub(r'<\s*(script|iframe)[^>]*/?\s*>', '', text, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities then re-escape for safety
    text = html_module.unescape(text)
    text = html_module.escape(text, quote=True)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _is_safe_url(url: str) -> bool:
    """Block private IPs, localhost, and non-HTTP schemes (SSRF prevention)."""
    try:
        parsed = urllib.parse.urlparse(url)
        # Only allow http/https
        if parsed.scheme not in ('http', 'https'):
            return False
        hostname = parsed.hostname or ''
        # Block obvious localhost
        if hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0', ''):
            return False
        # Resolve and check for private IPs
        try:
            addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for _, _, _, _, sockaddr in addr_infos:
                ip = ipaddress.ip_address(sockaddr[0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    LOG.warning("SSRF blocked: %s resolves to private IP %s", hostname, ip)
                    return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False


# ── Data model ────────────────────────────────────────────────────
@dataclass
class ToolEntry:
    name: str
    url: str
    description: str
    category: str = "AI"
    source: str = ""
    tags: list[str] = field(default_factory=list)
    upvotes: int = 0


# ── DB layer ──────────────────────────────────────────────────────
def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            url             TEXT NOT NULL UNIQUE,
            description     TEXT NOT NULL DEFAULT '',
            category        TEXT NOT NULL DEFAULT 'AI',
            source          TEXT NOT NULL DEFAULT '',
            tags            TEXT NOT NULL DEFAULT '[]',
            upvotes         INTEGER NOT NULL DEFAULT 0,
            discovered_at   TEXT NOT NULL DEFAULT (datetime('now')),
            article_generated INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tools_article ON tools(article_generated)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tools_discovered ON tools(discovered_at DESC)
    """)
    conn.commit()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db_existed = DB_PATH.exists()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    # Restrict DB file permissions to owner-only
    if not db_existed:
        os.chmod(str(DB_PATH), 0o600)
    return conn


def insert_tool(conn: sqlite3.Connection, tool: ToolEntry) -> bool:
    """Insert tool if URL not already present. Returns True if inserted."""
    try:
        conn.execute(
            """INSERT INTO tools (name, url, description, category, source, tags, upvotes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                _sanitize_text(tool.name),
                _normalize_url(tool.url),
                _sanitize_text(tool.description)[:2000],
                tool.category,
                tool.source,
                json.dumps(tool.tags),
                tool.upvotes,
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate URL


def _normalize_url(url: str) -> str:
    """Strip tracking params, trailing slashes for dedup."""
    parsed = urllib.parse.urlparse(url)
    # Remove common tracking params
    params = urllib.parse.parse_qs(parsed.query)
    clean_params = {
        k: v for k, v in params.items()
        if not k.startswith("utm_") and k not in ("ref", "source")
    }
    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
    cleaned = parsed._replace(query=clean_query, fragment="")
    result = urllib.parse.urlunparse(cleaned).rstrip("/")
    return result


# ── HTTP helper ───────────────────────────────────────────────────
def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict | list | None:
    """Fetch JSON from URL with retries."""
    if not _is_safe_url(url):
        LOG.warning("SSRF blocked: %s", url)
        return None
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            LOG.warning("Fetch attempt %d failed for %s: %s", attempt + 1, url, exc)
            if attempt < 2:
                time.sleep(2 ** attempt)
    return None


def _fetch_html(url: str) -> str | None:
    """Fetch raw HTML content."""
    if not _is_safe_url(url):
        LOG.warning("SSRF blocked: %s", url)
        return None
    hdrs = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        LOG.warning("HTML fetch failed for %s: %s", url, exc)
        return None


# ── AI keyword filter ─────────────────────────────────────────────
AI_KEYWORDS = re.compile(
    r"\b(ai|artificial.?intelligence|machine.?learning|llm|gpt|openai|claude|gemini|"
    r"copilot|chatbot|generative|neural|deep.?learning|nlp|computer.?vision|"
    r"diffusion|transformer|rag|vector|embedding|automation|no.?code|low.?code|"
    r"ai.?agent|ai.?tool|ai.?assistant|ai.?workflow|prompt)\b",
    re.IGNORECASE,
)


def _is_ai_related(text: str) -> bool:
    return bool(AI_KEYWORDS.search(text))


# ── Source: Product Hunt ──────────────────────────────────────────
def crawl_product_hunt() -> Iterator[ToolEntry]:
    """Crawl Product Hunt's daily posts via their public API.

    Uses the GraphQL API with the public client token.
    Falls back to the RSS-style tech page if that fails.
    """
    LOG.info("Crawling Product Hunt...")

    # Method 1: GraphQL API (public, no auth needed for basic queries)
    graphql_url = "https://api.producthunt.com/v2/api/graphql"
    query = """
    {
      posts(order: VOTES, first: 30) {
        edges {
          node {
            name
            tagline
            url
            votesCount
            topics {
              edges {
                node {
                  name
                }
              }
            }
          }
        }
      }
    }
    """

    # Try with PH access token if available
    ph_token = os.environ.get("PH_ACCESS_TOKEN", "")
    if ph_token:
        headers = {
            "Authorization": f"Bearer {ph_token}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            graphql_url,
            data=json.dumps({"query": query}).encode(),
            headers={**headers, "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                edges = data.get("data", {}).get("posts", {}).get("edges", [])
                for edge in edges:
                    node = edge["node"]
                    text = f"{node['name']} {node['tagline']}"
                    topics = [
                        t["node"]["name"]
                        for t in node.get("topics", {}).get("edges", [])
                    ]
                    if _is_ai_related(text) or any("ai" in t.lower() for t in topics):
                        yield ToolEntry(
                            name=node["name"],
                            url=node["url"],
                            description=node["tagline"],
                            category="AI",
                            source="producthunt",
                            tags=topics[:5],
                            upvotes=node.get("votesCount", 0),
                        )
                return
        except Exception as exc:
            LOG.warning("PH GraphQL failed: %s, falling back to scrape", exc)

    # Method 2: Scrape the featured/topic page
    html = _fetch_html("https://www.producthunt.com/topics/artificial-intelligence")
    if not html:
        LOG.warning("Product Hunt scrape failed")
        return

    # Extract tool names and URLs from the page with regex
    # PH uses data attributes and structured HTML
    pattern = re.compile(
        r'href="(/posts/[^"]+)"[^>]*>.*?<[^>]*>([^<]+)</[^>]*>',
        re.DOTALL,
    )
    seen: set[str] = set()
    for match in pattern.finditer(html):
        path, name = match.group(1), match.group(2).strip()
        if not name or path in seen:
            continue
        seen.add(path)
        url = f"https://www.producthunt.com{path}"
        yield ToolEntry(
            name=name,
            url=url,
            description="",
            category="AI",
            source="producthunt",
        )


# ── Source: Hacker News ───────────────────────────────────────────
def crawl_hackernews() -> Iterator[ToolEntry]:
    """Crawl HN front page + Show HN for AI tool launches."""
    LOG.info("Crawling Hacker News...")

    # Top stories + Show HN
    for endpoint in ("topstories", "showstories"):
        url = f"https://hacker-news.firebaseio.com/v0/{endpoint}.json"
        story_ids = _fetch_json(url)
        if not story_ids:
            continue

        # Check top 50 from each
        for sid in story_ids[:50]:
            item = _fetch_json(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
            )
            time.sleep(0.5)  # Rate limit: respect HN API
            if not item or item.get("type") != "story":
                continue

            title = item.get("title", "")
            story_url = item.get("url", "")
            if not story_url:
                story_url = f"https://news.ycombinator.com/item?id={sid}"

            text = f"{title} {item.get('text', '')}"
            if _is_ai_related(text):
                # Extract tool name from title (strip "Show HN:" etc.)
                name = re.sub(r"^(Show HN|Ask HN|Launch HN|Tell HN)\s*[:–-]\s*", "", title).strip()
                # Further clean: take part before first dash/colon if long
                if len(name) > 80:
                    name = re.split(r"\s*[–—-]\s*", name)[0][:80]

                yield ToolEntry(
                    name=name,
                    url=story_url,
                    description=title,
                    category="AI",
                    source="hackernews",
                    upvotes=item.get("score", 0),
                )


# ── Source: Reddit ────────────────────────────────────────────────
def crawl_reddit() -> Iterator[ToolEntry]:
    """Crawl AI-related subreddits for new tool announcements."""
    LOG.info("Crawling Reddit...")

    subreddits = ["artificial", "SaaS", "AItools", "singularity"]
    reddit_ua = "T9OS-Revenue-Crawler/1.0 (by /u/t9os_bot; github.com/t9os; ai-tool-discovery)"
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=50"
        data = _fetch_json(url, headers={"User-Agent": reddit_ua})
        if not data or "data" not in data:
            LOG.warning("Reddit r/%s fetch failed or empty", sub)
            time.sleep(2)  # Reddit rate limit
            continue

        for child in data["data"].get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            post_url = post.get("url", "")
            selftext = post.get("selftext", "")
            text = f"{title} {selftext}"

            if not _is_ai_related(text):
                continue

            # Skip self-posts that are just discussions (no external URL)
            is_self = post.get("is_self", False)
            if is_self:
                # Use the reddit permalink as URL
                permalink = post.get("permalink", "")
                post_url = f"https://www.reddit.com{permalink}" if permalink else ""

            if not post_url:
                continue

            # Try to identify tool name from title
            name = title
            # Strip common reddit prefixes
            name = re.sub(
                r"^(\[.+?\]|I (?:built|created|made|launched)|We (?:built|created|made|launched)|"
                r"Introducing|Check out|New:?|Just launched:?)\s*",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()
            if len(name) > 80:
                name = name[:77] + "..."

            yield ToolEntry(
                name=name,
                url=post_url,
                description=title[:500],
                category="AI",
                source=f"reddit/r/{sub}",
                upvotes=post.get("ups", 0),
            )

        time.sleep(2)  # Respect Reddit rate limits


# ── Orchestrator ──────────────────────────────────────────────────
SOURCE_MAP: dict[str, type[Iterator]] = {
    "ph": crawl_product_hunt,
    "hn": crawl_hackernews,
    "reddit": crawl_reddit,
}


def run_crawl(sources: list[str] | None = None) -> dict[str, int]:
    """Run crawl for specified sources. Returns {source: new_count}."""
    if sources is None:
        sources = list(SOURCE_MAP.keys())

    conn = get_db()
    stats: dict[str, int] = {}

    for src_key in sources:
        crawl_fn = SOURCE_MAP.get(src_key)
        if not crawl_fn:
            LOG.warning("Unknown source: %s", src_key)
            continue

        new_count = 0
        try:
            for tool in crawl_fn():
                if insert_tool(conn, tool):
                    new_count += 1
                    LOG.info("NEW: [%s] %s — %s", tool.source, tool.name, tool.url)
        except Exception as exc:
            LOG.error("Source %s failed: %s", src_key, exc)

        stats[src_key] = new_count
        LOG.info("Source %s: %d new tools", src_key, new_count)

    conn.close()
    return stats


def list_recent(limit: int = 20) -> list[dict]:
    """List recently discovered tools."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM tools ORDER BY discovered_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CLI ───────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="AI Tool Crawler")
    parser.add_argument("--source", choices=list(SOURCE_MAP.keys()), help="Crawl specific source only")
    parser.add_argument("--list", action="store_true", help="List recent discoveries")
    parser.add_argument("--pending", action="store_true", help="List tools without articles")
    args = parser.parse_args()

    if args.list:
        for tool in list_recent():
            status = "done" if tool["article_generated"] else "pending"
            print(f"[{status}] {tool['name']} — {tool['source']} — {tool['url']}")
        return

    if args.pending:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM tools WHERE article_generated = 0 ORDER BY upvotes DESC, discovered_at DESC",
        ).fetchall()
        conn.close()
        for r in rows:
            print(f"[{r['upvotes']:>4} votes] {r['name']} — {r['source']}")
        print(f"\nTotal pending: {len(rows)}")
        return

    sources = [args.source] if args.source else None

    with pipeline_run("revenue_crawler", notify_on_fail=False):
        stats = run_crawl(sources)
        total = sum(stats.values())
        LOG.info("Crawl complete. Total new: %d", total)
        record("revenue_crawler", "OK", f"new={total} | {stats}")


if __name__ == "__main__":
    main()
