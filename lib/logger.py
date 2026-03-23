"""T9 OS 파이프라인 로거 — 실행 결과 기록 + 실패 시 텔레그램 알림.

except:pass 패턴을 없앤다. 모든 파이프라인은 이걸 쓴다.

사용법:
    from lib.logger import pipeline_run, log_error

    with pipeline_run("deadline_notify"):
        # 작업 수행
        notify()
    # → 성공/실패 자동 기록, 실패 시 TG 알림
"""
import json
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .config import TG_TOKEN, TG_CHAT, LOG_DIR, T9

# ─── 상태 DB (JSON, 가볍게) ──────────────────────────────────
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
    """텔레그램 직접 발송 (tg_common 의존 없이)."""
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
            pass  # 알림 실패는 무시 (무한루프 방지)


# ─── 공개 API ─────────────────────────────────────────────────

def record(pipeline: str, status: str, detail: str = ""):
    """파이프라인 실행 결과 기록."""
    data = _load_status()
    data[pipeline] = {
        "status": status,
        "time": _now(),
        "detail": detail[:500] if detail else "",
    }
    _save_status(data)


def log_error(pipeline: str, error: Exception, notify: bool = True):
    """에러 기록 + 선택적 텔레그램 알림."""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    detail = "".join(tb[-3:])  # 마지막 3줄만
    record(pipeline, "FAIL", detail)

    # 로그 파일에도 기록
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now():%Y%m%d}_pipe_errors.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{_now()}] {pipeline} FAIL\n{detail}\n")

    if notify:
        _tg_send_raw(f"⚠️ T9 파이프라인 실패\n\n{pipeline}\n{str(error)[:200]}")


@contextmanager
def pipeline_run(name: str, notify_on_fail: bool = True):
    """파이프라인 실행 컨텍스트. 성공/실패 자동 기록.

    with pipeline_run("deadline_notify"):
        do_work()
    """
    try:
        yield
        record(name, "OK")
    except Exception as e:
        log_error(name, e, notify=notify_on_fail)
        raise  # 호출자가 원하면 잡을 수 있도록


def get_all_status() -> dict:
    """전체 파이프라인 상태 반환 (healthcheck용)."""
    return _load_status()
