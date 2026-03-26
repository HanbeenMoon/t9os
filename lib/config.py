"""T9 OS shared config — env vars, paths, API keys in one place.

All pipelines import from this module.
No duplicate loading code in individual pipelines.

Usage:
    from lib.config import GEMINI_KEY, TG_TOKEN, TG_CHAT, HANBEEN, T9, DB_PATH
"""
import os
from pathlib import Path

# ─── Path constants ────────────────────────────────────────────────
T9 = Path(__file__).resolve().parent.parent          # T9OS/
HANBEEN = T9.parent                                   # project root
# DB uses WSL native path (NTFS lock prevention, ADR-074)
# fallback: T9OS/.t9.db (NTFS, legacy compat)
_WSL_DB = Path.home() / ".t9os_data" / ".t9.db"
DB_PATH = _WSL_DB if _WSL_DB.exists() else T9 / ".t9.db"
INBOX_DIR = T9 / "field" / "inbox"
LOG_DIR = HANBEEN / "_ai" / "logs" / "cc"
PIPES_DIR = T9 / "pipes"

# ─── Env var loading (single entry point) ──────────────────────────────
# Load from env files if present, os.environ takes priority
_ENV_FILES_CANDIDATES = [
    HANBEEN / "_keys" / ".env.sh",     # primary
    HANBEEN / ".env",                   # alternative
]
_ENV_FILES = [f for f in _ENV_FILES_CANDIDATES if f.exists()]

_loaded: dict[str, str] = {}


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE or export KEY=VALUE format files."""
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # export KEY=VALUE → KEY=VALUE
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'").strip('\r\n')
        result[k] = v
    return result


def _load_all() -> dict[str, str]:
    """Load all env files in reverse order (later files get overwritten by earlier ones)."""
    global _loaded
    if _loaded:
        return _loaded
    merged: dict[str, str] = {}
    # Reverse load → earlier files take priority
    for f in reversed(_ENV_FILES):
        merged.update(_parse_env_file(f))
    # os.environ takes priority (strip \r\n to prevent NTFS contamination)
    merged.update({k: v.strip('\r\n') for k, v in os.environ.items()})
    _loaded = merged
    return _loaded


def get(key: str, default: str = "") -> str:
    """Env var lookup. os.environ > env file priority."""
    return _load_all().get(key, default)


# ─── Frequently used keys (available on import) ─────────────────────

def _init_keys():
    """Initialize keys on module load."""
    env = _load_all()
    return {
        "GEMINI_KEY": env.get("GEMINI_API_KEY", env.get("GOOGLE_API_KEY", "")),
        "TG_TOKEN": env.get("T9_TG_TOKEN", ""),
        "TG_CHAT": env.get("T9_TG_CHAT", ""),
        "NOTION_TOKEN": env.get("T9_NOTION_TOKEN", env.get("NOTION_TOKEN", "")),
        "GITHUB_TOKEN": env.get("GITHUB_TOKEN", ""),
        "OPENAI_KEY": env.get("OPENAI_API_KEY", ""),
        "ANTHROPIC_KEY": env.get("ANTHROPIC_API_KEY", ""),
        "CANVAS_TOKEN": env.get("CANVAS_TOKEN", ""),
        "GOOGLE_CLIENT_ID": env.get("GOOGLE_CLIENT_ID", ""),
        "GOOGLE_CLIENT_SECRET": env.get("GOOGLE_CLIENT_SECRET", ""),
        "GOOGLE_REFRESH_TOKEN": env.get("GOOGLE_REFRESH_TOKEN", ""),
    }


_keys = _init_keys()

GEMINI_KEY: str = _keys["GEMINI_KEY"]
TG_TOKEN: str = _keys["TG_TOKEN"]
TG_CHAT: str = _keys["TG_CHAT"]
NOTION_TOKEN: str = _keys["NOTION_TOKEN"]
GITHUB_TOKEN: str = _keys["GITHUB_TOKEN"]
OPENAI_KEY: str = _keys["OPENAI_KEY"]
ANTHROPIC_KEY: str = _keys["ANTHROPIC_KEY"]
CANVAS_TOKEN: str = _keys["CANVAS_TOKEN"]
GOOGLE_CLIENT_ID: str = _keys["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET: str = _keys["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN: str = _keys["GOOGLE_REFRESH_TOKEN"]
