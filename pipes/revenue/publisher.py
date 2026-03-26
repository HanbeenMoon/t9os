#!/usr/bin/env python3
"""Article publisher — Markdown to GitHub Pages (Jekyll) deployment.

Converts generated articles to Jekyll-ready format, manages the blog
repository, and pushes to GitHub Pages for auto-deployment.

Usage:
    python3 T9OS/pipes/revenue/publisher.py                    # stage only (safe)
    python3 T9OS/pipes/revenue/publisher.py --auto-deploy      # stage + deploy
    python3 T9OS/pipes/revenue/publisher.py --publish          # deploy staged (alias)
    python3 T9OS/pipes/revenue/publisher.py --init             # initialize blog repo
    python3 T9OS/pipes/revenue/publisher.py --preview          # list unpublished
    python3 T9OS/pipes/revenue/publisher.py --file article.md  # publish specific file
    python3 T9OS/pipes/revenue/publisher.py --status           # show publish status
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# ── T9OS imports ──────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from lib.config import GITHUB_TOKEN  # noqa: E402
from lib.logger import pipeline_run, record  # noqa: E402

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# ── Constants ─────────────────────────────────────────────────────
ARTICLES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "revenue" / "articles"
BLOG_DIR = Path.home() / ".t9os_data" / "revenue-blog"
POSTS_DIR = BLOG_DIR / "_posts"
STAGING_DIR = BLOG_DIR / "_staging"
PUBLISHED_LOG = Path.home() / ".t9os_data" / "revenue_published.json"
PUBLISH_LOG_PATH = Path.home() / ".t9os_data" / "revenue_publisher.log"
LOG_MAX_BYTES = 100 * 1024  # 100KB

# Blog configuration
BLOG_REPO_NAME = "ai-tool-reviews"  # GitHub repo name
BLOG_TITLE = "AI Tool Insider"
BLOG_DESCRIPTION = "Honest reviews of the latest AI tools — updated daily"
BLOG_URL = ""  # Set after repo creation

LOG = logging.getLogger("revenue.publisher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


# ── Published tracking ────────────────────────────────────────────
def _load_published() -> dict[str, str]:
    """Load set of published article filenames → publish dates."""
    if PUBLISHED_LOG.exists():
        try:
            return json.loads(PUBLISHED_LOG.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_published(data: dict[str, str]) -> None:
    PUBLISHED_LOG.parent.mkdir(parents=True, exist_ok=True)
    PUBLISHED_LOG.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ── Jekyll blog initialization ────────────────────────────────────
JEKYLL_CONFIG = dedent("""\
    title: "{title}"
    description: "{description}"
    url: ""
    baseurl: "/{repo_name}"
    theme: minima
    permalink: /:categories/:title/

    # SEO
    plugins:
      - jekyll-feed
      - jekyll-sitemap
      - jekyll-seo-tag

    # Analytics (add your GA4 ID)
    google_analytics: ""

    # Social
    twitter_username: ""
    github_username: ""

    # Exclude
    exclude:
      - README.md
      - LICENSE
      - Gemfile.lock
    """)

GEMFILE = dedent("""\
    source "https://rubygems.org"
    gem "github-pages", group: :jekyll_plugins
    gem "jekyll-feed"
    gem "jekyll-sitemap"
    gem "jekyll-seo-tag"
    """)

INDEX_PAGE = dedent("""\
    ---
    layout: home
    title: AI Tool Insider
    ---

    Welcome to **AI Tool Insider** — your daily source for honest, in-depth
    reviews of the latest AI tools. We test and compare so you don't have to.
    """)

ABOUT_PAGE = dedent("""\
    ---
    layout: page
    title: About
    permalink: /about/
    ---

    **AI Tool Insider** publishes honest, detailed reviews of AI tools
    across every category — from writing assistants to code generators,
    design tools to data analysis platforms.

    Our reviews are structured, comparable, and updated regularly.
    We highlight both strengths and weaknesses so you can make informed decisions.

    New reviews are published daily. Subscribe via RSS to stay updated.
    """)

ROBOTS_TXT = dedent("""\
    User-agent: *
    Allow: /
    Sitemap: {url}/sitemap.xml
    """)


def init_blog() -> bool:
    """Initialize Jekyll blog structure for GitHub Pages."""
    LOG.info("Initializing blog at %s", BLOG_DIR)

    if BLOG_DIR.exists() and (BLOG_DIR / "_config.yml").exists():
        LOG.info("Blog already initialized at %s", BLOG_DIR)
        return True

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(exist_ok=True)

    # _config.yml
    config = JEKYLL_CONFIG.format(
        title=BLOG_TITLE,
        description=BLOG_DESCRIPTION,
        repo_name=BLOG_REPO_NAME,
    )
    (BLOG_DIR / "_config.yml").write_text(config, encoding="utf-8")

    # Gemfile
    (BLOG_DIR / "Gemfile").write_text(GEMFILE, encoding="utf-8")

    # index.md
    (BLOG_DIR / "index.md").write_text(INDEX_PAGE, encoding="utf-8")

    # about.md
    (BLOG_DIR / "about.md").write_text(ABOUT_PAGE, encoding="utf-8")

    # robots.txt — resolve sitemap URL via gh CLI if possible
    site_url = ""
    try:
        whoami = subprocess.run(
            ["gh", "api", "user", "-q", ".login"],
            capture_output=True, text=True, timeout=10,
        )
        username = whoami.stdout.strip()
        if username:
            site_url = f"https://{username}.github.io/{BLOG_REPO_NAME}"
    except Exception:
        pass
    if not site_url:
        site_url = f"https://example.com/{BLOG_REPO_NAME}"
        LOG.warning("Could not determine GitHub username. robots.txt uses placeholder URL.")
    (BLOG_DIR / "robots.txt").write_text(
        ROBOTS_TXT.format(url=site_url),
        encoding="utf-8",
    )

    # .gitignore
    (BLOG_DIR / ".gitignore").write_text(
        "_site/\n.sass-cache/\n.jekyll-cache/\n.jekyll-metadata\nGemfile.lock\n",
        encoding="utf-8",
    )

    # README
    (BLOG_DIR / "README.md").write_text(
        f"# {BLOG_TITLE}\n\n{BLOG_DESCRIPTION}\n\nPowered by T9OS revenue pipeline.\n",
        encoding="utf-8",
    )

    # Initialize git
    _run_git("init", cwd=BLOG_DIR)
    _run_git("checkout", "-b", "main", cwd=BLOG_DIR)
    _run_git("add", ".", cwd=BLOG_DIR)
    _run_git("commit", "-m", "Initial Jekyll blog setup", cwd=BLOG_DIR)

    LOG.info("Blog initialized. Next: create GitHub repo and set remote.")
    LOG.info("  gh repo create %s --public --source=%s --push", BLOG_REPO_NAME, BLOG_DIR)
    return True


# ── Git helpers ───────────────────────────────────────────────────
def _run_git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run git command, return result."""
    cmd = ["git"] + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd or BLOG_DIR,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 and "--" not in args[0]:
        LOG.warning("git %s failed: %s", " ".join(args[:2]), result.stderr.strip())
    return result


def _has_remote() -> bool:
    """Check if blog repo has a remote configured."""
    result = _run_git("remote", "-v", cwd=BLOG_DIR)
    return bool(result.stdout.strip())


def _setup_remote() -> bool:
    """Create GitHub repo and set remote using gh CLI."""
    if not shutil.which("gh"):
        LOG.warning("gh CLI not found. Manual remote setup needed.")
        return False

    # Check if repo already exists
    check = subprocess.run(
        ["gh", "repo", "view", BLOG_REPO_NAME],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if check.returncode != 0:
        # Create the repo
        LOG.info("Creating GitHub repo: %s", BLOG_REPO_NAME)
        create = subprocess.run(
            [
                "gh", "repo", "create", BLOG_REPO_NAME,
                "--public",
                "--description", BLOG_DESCRIPTION,
                "--source", str(BLOG_DIR),
                "--push",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if create.returncode != 0:
            LOG.error("Failed to create repo: %s", create.stderr)
            return False
        LOG.info("Repo created and pushed")
    else:
        # Repo exists, ensure remote is set
        if not _has_remote():
            # Get username
            whoami = subprocess.run(
                ["gh", "api", "user", "-q", ".login"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            username = whoami.stdout.strip()
            if username:
                _run_git(
                    "remote", "add", "origin",
                    f"https://github.com/{username}/{BLOG_REPO_NAME}.git",
                    cwd=BLOG_DIR,
                )

    # Enable GitHub Pages
    subprocess.run(
        [
            "gh", "api", "-X", "POST",
            f"repos/{{owner}}/{BLOG_REPO_NAME}/pages",
            "-f", "source[branch]=main",
            "-f", "source[path]=/",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    return True


# ── Article processing ────────────────────────────────────────────
def _inject_seo_extras(content: str, frontmatter: dict) -> str:
    """Enhance article with additional SEO elements."""
    # Add canonical URL hint in frontmatter if missing
    # Add reading time estimate
    word_count = len(content.split())
    reading_time = max(1, word_count // 200)

    # Insert reading time after frontmatter
    if "---" in content:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            # Add reading_time to frontmatter
            fm = parts[1].rstrip()
            if "reading_time" not in fm:
                fm += f"\nreading_time: {reading_time}\n"
            content = f"---{fm}---{parts[2]}"

    return content


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm_text = parts[1].strip()
    body = parts[2]

    # Simple YAML-like parsing (no PyYAML dependency)
    fm: dict = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            fm[key] = value

    return fm, body


def process_article(source_path: Path) -> Path | None:
    """Process a source article into Jekyll-ready format.

    Returns the destination path if successful.
    """
    content = source_path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)

    if not fm.get("title"):
        LOG.warning("Article has no title: %s", source_path.name)
        return None

    # Ensure Jekyll-compatible frontmatter
    enhanced = _inject_seo_extras(content, fm)

    # Jekyll post filename: YYYY-MM-DD-slug.md
    # Source files should already follow this pattern
    dest_name = source_path.name
    if not re.match(r"\d{4}-\d{2}-\d{2}-", dest_name):
        date = fm.get("date", datetime.now().strftime("%Y-%m-%d"))
        slug = fm.get("slug", source_path.stem)
        dest_name = f"{date}-{slug}.md"

    # Add layout to frontmatter if missing
    if "layout:" not in enhanced:
        enhanced = enhanced.replace("---\n", "---\nlayout: post\n", 1)

    dest_path = POSTS_DIR / dest_name
    dest_path.write_text(enhanced, encoding="utf-8")
    return dest_path


# ── Publishing orchestrator ───────────────────────────────────────
def _rotate_log() -> None:
    """Truncate publish log if it exceeds LOG_MAX_BYTES."""
    if PUBLISH_LOG_PATH.exists() and PUBLISH_LOG_PATH.stat().st_size > LOG_MAX_BYTES:
        content = PUBLISH_LOG_PATH.read_text(encoding="utf-8", errors="replace")
        # Keep last 50% of content
        truncated = content[len(content) // 2:]
        PUBLISH_LOG_PATH.write_text(f"[truncated at {datetime.now().isoformat()}]\n{truncated}", encoding="utf-8")
        LOG.info("Log rotated: %s", PUBLISH_LOG_PATH)


def stage_articles(dry_run: bool = False) -> dict[str, int]:
    """Stage all new articles to _staging/ without deploying."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    published = _load_published()
    articles = sorted(ARTICLES_DIR.glob("*.md")) if ARTICLES_DIR.exists() else []

    if not articles:
        LOG.info("No articles found in %s", ARTICLES_DIR)
        return {"staged": 0, "skipped": 0}

    new_count = 0
    skipped = 0

    for article_path in articles:
        if article_path.name in published:
            skipped += 1
            continue

        LOG.info("Staging: %s", article_path.name)
        if dry_run:
            print(f"  Would stage: {article_path.name}")
            new_count += 1
            continue

        dest = STAGING_DIR / article_path.name
        shutil.copy2(str(article_path), str(dest))
        new_count += 1
        LOG.info("Staged: %s → %s", article_path.name, dest)

    LOG.info("Staging complete: %d staged, %d skipped", new_count, skipped)
    return {"staged": new_count, "skipped": skipped}


def publish_all(dry_run: bool = False, auto_deploy: bool = False) -> dict[str, int]:
    """Publish all new articles to the blog.

    Without --auto-deploy, articles are only staged (not deployed).
    Use --publish to deploy staged articles.
    """
    _rotate_log()

    if not auto_deploy:
        return stage_articles(dry_run=dry_run)

    if not BLOG_DIR.exists() or not (BLOG_DIR / "_config.yml").exists():
        LOG.info("Blog not initialized. Run with --init first.")
        init_blog()

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    published = _load_published()
    # Publish from staging if available, else from articles dir
    source_dir = STAGING_DIR if STAGING_DIR.exists() and list(STAGING_DIR.glob("*.md")) else ARTICLES_DIR
    articles = sorted(source_dir.glob("*.md")) if source_dir.exists() else []

    if not articles:
        LOG.info("No articles found in %s", source_dir)
        return {"published": 0, "skipped": 0}

    new_count = 0
    skipped = 0

    for article_path in articles:
        if article_path.name in published:
            skipped += 1
            continue

        LOG.info("Processing: %s", article_path.name)

        if dry_run:
            print(f"  Would publish: {article_path.name}")
            new_count += 1
            continue

        dest = process_article(article_path)
        if dest:
            published[article_path.name] = datetime.now().isoformat()
            new_count += 1
            LOG.info("Published: %s → %s", article_path.name, dest.name)
        else:
            LOG.warning("Failed to process: %s", article_path.name)

    if not dry_run and new_count > 0:
        # Git commit and push
        _run_git("add", "_posts/", cwd=BLOG_DIR)
        commit_msg = f"Publish {new_count} new article{'s' if new_count > 1 else ''} [{datetime.now():%Y-%m-%d}]"
        _run_git("commit", "-m", commit_msg, cwd=BLOG_DIR)

        deploy_success = False
        if _has_remote():
            result = _run_git("push", "origin", "main", cwd=BLOG_DIR)
            if result.returncode == 0:
                LOG.info("Pushed to GitHub. Pages will auto-deploy.")
                deploy_success = True
            else:
                LOG.warning("Push failed. Manual push needed: cd %s && git push", BLOG_DIR)
        else:
            # Vercel deploy (no GitHub remote needed)
            try:
                vercel_bin = Path.home() / ".nvm/versions/node/v22.22.1/bin/vercel"
                vercel_cmd = str(vercel_bin) if vercel_bin.exists() else "vercel"
                vercel_result = subprocess.run(
                    [vercel_cmd, "--yes", "--prod"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(BLOG_DIR),
                )
                if vercel_result.returncode == 0:
                    LOG.info("Vercel deploy complete.")
                    deploy_success = True
                else:
                    LOG.warning("Vercel deploy failed: %s", vercel_result.stderr[:200])
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                LOG.warning("Vercel CLI unavailable: %s", e)

        # P1-8: Only save published state after successful deploy
        if deploy_success:
            _save_published(published)
            # Clean staged files that were published
            if STAGING_DIR.exists():
                for f in STAGING_DIR.glob("*.md"):
                    if f.name in published:
                        f.unlink()
        else:
            LOG.warning("Deploy failed — published state NOT saved. Re-run to retry.")

    return {"published": new_count, "skipped": skipped}


def publish_file(filepath: str) -> bool:
    """Publish a specific article file."""
    source = Path(filepath)
    if not source.exists():
        # Try relative to articles dir
        source = ARTICLES_DIR / filepath
    if not source.exists():
        LOG.error("File not found: %s", filepath)
        return False

    if not BLOG_DIR.exists():
        init_blog()

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = process_article(source)

    if dest:
        published = _load_published()
        published[source.name] = datetime.now().isoformat()
        _save_published(published)

        _run_git("add", str(dest.relative_to(BLOG_DIR)), cwd=BLOG_DIR)
        _run_git("commit", "-m", f"Publish: {source.stem}", cwd=BLOG_DIR)

        if _has_remote():
            _run_git("push", "origin", "main", cwd=BLOG_DIR)

        LOG.info("Published: %s", dest.name)
        return True

    return False


def show_status() -> None:
    """Show publishing status summary."""
    published = _load_published()
    articles = sorted(ARTICLES_DIR.glob("*.md")) if ARTICLES_DIR.exists() else []

    print(f"\nBlog directory: {BLOG_DIR}")
    print(f"Blog initialized: {(BLOG_DIR / '_config.yml').exists()}")
    print(f"Remote configured: {_has_remote() if BLOG_DIR.exists() else False}")
    print(f"\nArticles in source: {len(articles)}")
    print(f"Already published: {len(published)}")
    print(f"Pending: {len(articles) - len([a for a in articles if a.name in published])}")

    pending = [a for a in articles if a.name not in published]
    if pending:
        print("\nPending articles:")
        for a in pending[:20]:
            print(f"  - {a.name}")


# ── CLI ───────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Revenue Article Publisher")
    parser.add_argument("--init", action="store_true", help="Initialize blog repo")
    parser.add_argument("--preview", action="store_true", help="Preview unpublished articles")
    parser.add_argument("--file", type=str, help="Publish specific article file")
    parser.add_argument("--status", action="store_true", help="Show publish status")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    parser.add_argument("--auto-deploy", action="store_true", help="Actually deploy (without this, only stage)")
    parser.add_argument("--publish", action="store_true", help="Deploy staged articles (alias for --auto-deploy)")
    args = parser.parse_args()

    if args.init:
        init_blog()
        return

    if args.status:
        show_status()
        return

    if args.file:
        with pipeline_run("revenue_publisher", notify_on_fail=False):
            publish_file(args.file)
        return

    if args.preview:
        published = _load_published()
        articles = sorted(ARTICLES_DIR.glob("*.md")) if ARTICLES_DIR.exists() else []
        pending = [a for a in articles if a.name not in published]
        for a in pending:
            print(f"  {a.name}")
        print(f"\n{len(pending)} articles ready to publish")
        return

    auto_deploy = args.auto_deploy or args.publish
    with pipeline_run("revenue_publisher", notify_on_fail=False):
        stats = publish_all(dry_run=args.dry_run, auto_deploy=auto_deploy)
        LOG.info("Publisher complete: %s", stats)
        record("revenue_publisher", "OK", json.dumps(stats))


if __name__ == "__main__":
    main()
