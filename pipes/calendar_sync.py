"""Google Calendar → T9 OS field/inbox sync.

Fetches today's and tomorrow's events from Google Calendar via OAuth2
and writes an MD file into field/inbox/ for t9_seed.py reindex.

Required env vars (from _keys/.env.sh via lib/config.py):
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN

Usage (cron):
    30 7 * * * /mnt/c/Users/winn/HANBEEN/T9OS/pipes/sc41_cron_runner.sh calendar
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import (
    HANBEEN, INBOX_DIR, LOG_DIR, T9,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN,
)

T9_SEED = T9 / "t9_seed.py"

KST = timezone(timedelta(hours=9))

TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


# # _load_env_local / _get_env remove — lib/config.pyIntegrate


def _refresh_access_token(
    client_id: str, client_secret: str, refresh_token: str
) -> str:
    """Exchange refresh token for a short-lived access token."""
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())

    if "access_token" not in body:
        raise RuntimeError(f"Token refresh failed: {body}")
    return body["access_token"]


def _fetch_events(access_token: str, days: int = 2) -> list[dict]:
    """Fetch calendar events for the next `days` days."""
    now = datetime.now(KST)
    time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    time_max = (now + timedelta(days=days)).replace(
        hour=23, minute=59, second=59
    ).isoformat()

    params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": "50",
        "timeZone": "Asia/Seoul",
    })

    url = f"{CALENDAR_URL}?{params}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {access_token}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())

    events = []
    for item in body.get("items", []):
        start_raw = item.get("start", {})
        end_raw = item.get("end", {})
        events.append({
            "id": item.get("id", ""),
            "summary": item.get("summary", "(title not found)"),
            "start": start_raw.get("dateTime", start_raw.get("date", "")),
            "end": end_raw.get("dateTime", end_raw.get("date", "")),
            "all_day": bool(start_raw.get("date") and not start_raw.get("dateTime")),
            "location": item.get("location", ""),
            "description": (item.get("description", "") or "")[:200],
        })
    return events


def _format_time(iso_str: str) -> str:
    """Extract HH:MM from ISO datetime, or return 'all-day'."""
    if not iso_str or len(iso_str) <= 10:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except ValueError:
        return iso_str


def _write_inbox_md(events: list[dict], today: str) -> Path:
    """Write events as an MD file in field/inbox/."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{today}_GoogleCalendar_schedulesync.md"
    filepath = INBOX_DIR / filename

    lines = [
        f"# Google Calendar schedule ({today})",
        "",
        f"sync : {datetime.now(KST):%Y-%m-%d %H:%M:%S KST}",
        f"schedule : {len(events)}items",
        "",
    ]

    if not events:
        lines.append("(/Tomorrow schedule not found)")
    else:
        # Group by date
        by_date: dict[str, list[dict]] = {}
        for ev in events:
            date_key = ev["start"][:10] if ev["start"] else today
            by_date.setdefault(date_key, []).append(ev)

        for date_key in sorted(by_date):
            day_label = "" if date_key == today else "Tomorrow"
            lines.append(f"## {date_key} ({day_label})")
            lines.append("")
            for ev in by_date[date_key]:
                start_t = _format_time(ev["start"])
                end_t = _format_time(ev["end"])
                time_str = start_t if start_t == "" else f"{start_t}-{end_t}"
                lines.append(f"- [{time_str}] {ev['summary']}")
                if ev["location"]:
                    lines.append(f"  : {ev['location']}")
            lines.append("")

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filepath


def _next_log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    existing = sorted(LOG_DIR.glob(f"{date_part}_CC_*_calendar_sync_*"))
    seq = len(existing) + 1
    return LOG_DIR / f"{date_part}_CC_{seq:03d}_calendar_sync_{time_part}_result.txt"


def main() -> int:
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
        log_lines.append(line)
        print(line)

    log("Calendar sync start")

    client_id = GOOGLE_CLIENT_ID
    client_secret = GOOGLE_CLIENT_SECRET
    refresh_token = GOOGLE_REFRESH_TOKEN

    if not all([client_id, client_secret, refresh_token]):
        log("ERROR: Missing Google Calendar credentials. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN")
        return 1

    try:
        log("Refreshing access token...")
        access_token = _refresh_access_token(client_id, client_secret, refresh_token)
        log("Access token obtained")

        log("Fetching events (today + tomorrow)...")
        events = _fetch_events(access_token, days=2)
        log(f"Fetched {len(events)} events")

        today = datetime.now(KST).strftime("%Y%m%d")
        md_path = _write_inbox_md(events, today)
        log(f"Written to: {md_path}")

        # Trigger reindex
        log("Running t9_seed.py reindex...")
        result = subprocess.run(
            [sys.executable, str(T9_SEED), "reindex"],
            capture_output=True,
            text=True,
            cwd=str(HANBEEN),
            timeout=120,
        )
        log(f"reindex exit code: {result.returncode}")

    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        log(f"HTTP Error {e.code}: {body[:300]}")
        return 1
    except Exception as e:
        log(f"ERROR: {e}")
        return 1

    # Save log
    log_path = _next_log_path()
    log(f"Log saved: {log_path}")
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
