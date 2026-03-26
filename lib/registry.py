"""T9 OS pipeline — single source (SRBB compliance).

healthcheck.pyintegrity_check.pypipeline list.
pipeline add update.
"""
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
PIPES = T9 / "pipes"

# (file, , type, /cron )
PIPELINE_REGISTRY = [
    {"file": "t9_seed.py", "path": T9 / "t9_seed.py", "desc": " engine", "type": "engine"},
    {"file": "t9_bot.py", "path": PIPES / "t9_bot.py", "desc": "Telegram bot", "type": "daemon"},
    {"file": "t9_auto.py", "path": PIPES / "t9_auto.py", "desc": "Preindividual auto classify", "type": "cron"},
    {"file": "gm_batch.py", "path": PIPES / "gm_batch.py", "desc": "guardian batch", "type": "manual"},
    {"file": "deadline_notify.py", "path": PIPES / "deadline_notify.py", "desc": "deadline notification", "type": "cron"},
    {"file": "t9_ceo_brief.py", "path": PIPES / "t9_ceo_brief.py", "desc": "CEO brief", "type": "cron"},
    {"file": "calendar_sync.py", "path": PIPES / "calendar_sync.py", "desc": "calendar sync", "type": "cron"},
    {"file": "sc41_cron.py", "path": PIPES / "sc41_cron.py", "desc": "SC41 auto", "type": "cron"},
    {"file": "integrity_check.py", "path": PIPES / "integrity_check.py", "desc": " integrity", "type": "check"},
    {"file": "healthcheck.py", "path": PIPES / "healthcheck.py", "desc": "state ", "type": "check"},
    {"file": "session_lock.py", "path": PIPES / "session_lock.py", "desc": "session  ", "type": "lib"},
    {"file": "session_live_read.py", "path": PIPES / "session_live_read.py", "desc": "session JSONL ", "type": "lib"},
    {"file": "safe_change.sh", "path": PIPES / "safe_change.sh", "desc": "change ", "type": "tool"},
    {"file": "tg_common.py", "path": PIPES / "tg_common.py", "desc": "Telegram common", "type": "lib"},
    {"file": "adr_auto.py", "path": PIPES / "adr_auto.py", "desc": "ADR auto create", "type": "hook"},
    {"file": "cron_runner.sh", "path": PIPES / "cron_runner.sh", "desc": "cron Integrate ", "type": "tool"},
    {"file": "hwp_convert.py", "path": PIPES / "hwp_convert.py", "desc": "HWP↔DOCX", "type": "tool"},
    {"file": "gdrive_upload.py", "path": PIPES / "gdrive_upload.py", "desc": "Google Drive ", "type": "tool"},
]

# process (pscheck)
DAEMON_PROCESSES = ["t9_bot.py"]

# cron (crontab -lcheck)
CRON_IDENTIFIERS = ["deadline", "ceo_brief", "calendar", "healthcheck", "sc41", "t9_auto"]
