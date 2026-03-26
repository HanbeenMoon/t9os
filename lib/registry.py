"""T9 OS 파이프라인 레지스트리 — 단일 소스 (SRBB 준수).

healthcheck.py와 integrity_check.py가 공유하는 파이프라인 목록.
새 파이프라인 추가 시 여기만 갱신하면 두 곳 모두 반영됨.
"""
from pathlib import Path

T9 = Path(__file__).resolve().parent.parent
PIPES = T9 / "pipes"

# (파일명, 설명, 유형, 데몬/cron 여부)
PIPELINE_REGISTRY = [
    {"file": "t9_seed.py", "path": T9 / "t9_seed.py", "desc": "시드 엔진", "type": "engine"},
    {"file": "t9_bot.py", "path": PIPES / "t9_bot.py", "desc": "텔레그램 봇", "type": "daemon"},
    {"file": "t9_auto.py", "path": PIPES / "t9_auto.py", "desc": "전개체 자동 분류", "type": "cron"},
    {"file": "gm_batch.py", "path": PIPES / "gm_batch.py", "desc": "감시단 batch", "type": "manual"},
    {"file": "deadline_notify.py", "path": PIPES / "deadline_notify.py", "desc": "마감일 알림", "type": "cron"},
    {"file": "t9_ceo_brief.py", "path": PIPES / "t9_ceo_brief.py", "desc": "CEO 브리프", "type": "cron"},
    {"file": "calendar_sync.py", "path": PIPES / "calendar_sync.py", "desc": "캘린더 동기화", "type": "cron"},
    {"file": "sc41_cron.py", "path": PIPES / "sc41_cron.py", "desc": "SC41 자동화", "type": "cron"},
    {"file": "integrity_check.py", "path": PIPES / "integrity_check.py", "desc": "데이터 무결성", "type": "check"},
    {"file": "healthcheck.py", "path": PIPES / "healthcheck.py", "desc": "상태 대시보드", "type": "check"},
    {"file": "session_lock.py", "path": PIPES / "session_lock.py", "desc": "세션 충돌 방지", "type": "lib"},
    {"file": "session_live_read.py", "path": PIPES / "session_live_read.py", "desc": "세션 JSONL 읽기", "type": "lib"},
    {"file": "safe_change.sh", "path": PIPES / "safe_change.sh", "desc": "변경 안전망", "type": "tool"},
    {"file": "tg_common.py", "path": PIPES / "tg_common.py", "desc": "텔레그램 공통", "type": "lib"},
    {"file": "adr_auto.py", "path": PIPES / "adr_auto.py", "desc": "ADR 자동 생성", "type": "hook"},
    {"file": "cron_runner.sh", "path": PIPES / "cron_runner.sh", "desc": "cron 통합 진입점", "type": "tool"},
    {"file": "hwp_convert.py", "path": PIPES / "hwp_convert.py", "desc": "HWP↔DOCX", "type": "tool"},
    {"file": "gdrive_upload.py", "path": PIPES / "gdrive_upload.py", "desc": "Google Drive 업로드", "type": "tool"},
    {"file": "overnight.py", "path": PIPES / "overnight.py", "desc": "오버나이트 정비", "type": "cron"},
]

# 데몬 프로세스 (ps에서 확인)
DAEMON_PROCESSES = ["t9_bot.py"]

# cron 식별자 (crontab -l에서 확인)
CRON_IDENTIFIERS = ["deadline", "ceo_brief", "calendar", "healthcheck", "sc41", "t9_auto"]
