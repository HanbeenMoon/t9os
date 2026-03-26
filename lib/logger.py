"""T9 OS pipeline — execution result record + failed Telegram notification.

except:pass pattern. pipeline.

Usage:
    from lib.logger import pipeline_run, log_error

    with pipeline_run("deadline_notify"):
        # task
        notify()
    # → success/failed auto record, failed TG notification
"""
import json
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .config import TG_TOKEN, TG_CHAT, LOG_DIR, T9

# ─── state DB (JSON, ) ────────────────────────────────────────
STATUS_FILE = T9 / ".pipe_status.json"


def _load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_status(data: dict):
    STATUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _tg_send_raw(text: str):
    """Telegram (tg_common )."""
    if not TG_TOKEN or not TG_CHAT:
        return
    import urllib.parse
    import urllib.request
    api = f"https://api.telegram.org/bot{TG_TOKEN}"
    for i in range(0, max(len(text), 1), 4000):
        chunk = text[i:i + 4000]
        data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": chunk}).encode()
        try:
            urllib.request.urlopen(f"{api}/sendMessage", data, timeout=10)
        except Exception:
            pass  # notification failedskip ()


# ─── API ────────────────────────────────────────

def record(pipeline: str, status: str, detail: str = ""):
    """pipeline execution result record."""
    data = _load_status()
    data[pipeline] = {
        "status": status,
        "time": _now(),
        "detail": detail[:500] if detail else "",
    }
    _save_status(data)


def log_error(pipeline: str, error: Exception, notify: bool = True):
    """record + optionalTelegram notification."""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    detail = "".join(tb[-3:])
    record(pipeline, "FAIL", detail)

    # log filerecord
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now():%Y%m%d}_pipe_errors.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{_now()}] {pipeline} FAIL\n{detail}\n")

    if notify:
        _tg_send_raw(f"⚠️ T9 pipeline failed\n\n{pipeline}\n{str(error)[:200]}")


@contextmanager
def pipeline_run(name: str, notify_on_fail: bool = True):
    """pipeline execution . success/failed auto record.

    with pipeline_run("deadline_notify"):
        do_work()
    """
    try:
        yield
        record(name, "OK")
    except Exception as e:
        log_error(name, e, notify=notify_on_fail)
        raise  # call


def get_all_status() -> dict:
    """total pipeline state return (healthcheck)."""
    return _load_status()
