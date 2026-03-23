"""T9 OS 공통 설정 — 환경변수, 경로, API 키를 한 곳에서 관리.

모든 파이프라인은 이 모듈에서 import해서 사용한다.
중복 로드 코드를 각 파이프라인에 두지 않는다.

사용법:
    from lib.config import GEMINI_KEY, TG_TOKEN, TG_CHAT, WORKSPACE, T9, DB_PATH
"""
import os
from pathlib import Path

# ─── 경로 상수 ────────────────────────────────────────────────
T9 = Path(__file__).resolve().parent.parent          # T9OS/
WORKSPACE = T9.parent                                   # ~/code/WORKSPACE/
DB_PATH = T9 / ".t9.db"
INBOX_DIR = T9 / "field" / "inbox"
LOG_DIR = WORKSPACE / "_ai" / "logs" / "cc"
PIPES_DIR = T9 / "pipes"

# ─── 환경변수 로드 (단일 진입점) ──────────────────────────────
# 우선순위: os.environ > .env.sh > .env.txt > .env.local
_ENV_FILES = [
    WORKSPACE / "_keys" / ".env.sh",
    WORKSPACE / "_keys" / ".env.txt",
    WORKSPACE / "_legacy" / "PROJECTS" / "t9-dashboard" / ".env.local",
]

_loaded: dict[str, str] = {}


def _parse_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE 또는 export KEY=VALUE 형식 파일 파싱."""
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
        v = v.strip().strip('"').strip("'")
        result[k] = v
    return result


def _load_all() -> dict[str, str]:
    """모든 env 파일을 역순으로 로드 (나중 파일이 먼저 덮이도록)."""
    global _loaded
    if _loaded:
        return _loaded
    merged: dict[str, str] = {}
    # 역순으로 로드 → 앞의 파일이 우선
    for f in reversed(_ENV_FILES):
        merged.update(_parse_env_file(f))
    # os.environ이 최우선
    merged.update(os.environ)
    _loaded = merged
    return _loaded


def get(key: str, default: str = "") -> str:
    """환경변수 조회. os.environ > .env.sh > .env.txt > .env.local 순."""
    return _load_all().get(key, default)


# ─── 자주 쓰는 키 (import 즉시 사용 가능) ─────────────────────

def _init_keys():
    """모듈 로드 시 키 초기화."""
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
