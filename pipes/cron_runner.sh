#!/usr/bin/env bash
# T9 OS 범용 cron runner — 모든 파이프라인의 단일 진입점.
export PYTHONDONTWRITEBYTECODE=1
# config.py가 env 파일을 직접 파싱하므로 source는 백업용.
#
# Usage:
#   cron_runner.sh <파이프라인명>
#   cron_runner.sh deadline_notify
#   cron_runner.sh ceo_brief
#   cron_runner.sh t9_auto
#   cron_runner.sh calendar
#   cron_runner.sh sc41
#   cron_runner.sh tidy
#   cron_runner.sh healthcheck

set -euo pipefail

# 셸 스크립트는 config.py 경유 불가 — 여기만 하드코딩 허용 (ADR-024)
HANBEEN="/mnt/c/Users/winn/HANBEEN"
T9="${HANBEEN}/T9OS"
PIPES="${T9}/pipes"
LOG_DIR="${HANBEEN}/_ai/logs/cc"

# 환경변수 로드 (백업 — config.py가 이미 파일에서 읽지만 os.environ도 채워줌)
[ -f "${HANBEEN}/_keys/.env.sh" ] && source "${HANBEEN}/_keys/.env.sh"

MODE="${1:-help}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

case "$MODE" in
    deadline_notify|deadline)
        python3 "${PIPES}/deadline_notify.py" >> "${LOG_DIR}/deadline_notify_cron.log" 2>&1
        ;;
    ceo_brief|brief)
        python3 "${PIPES}/t9_ceo_brief.py" >> "${LOG_DIR}/ceo_brief_cron.log" 2>&1
        ;;
    t9_auto|auto)
        python3 "${PIPES}/t9_auto.py" >> "${LOG_DIR}/t9_auto_cron.log" 2>&1
        ;;
    calendar)
        python3 "${PIPES}/calendar_sync.py" >> "${LOG_DIR}/calendar_cron.log" 2>&1
        ;;
    sc41)
        python3 "${PIPES}/sc41_cron.py" >> "${LOG_DIR}/sc41_cron.log" 2>&1
        ;;
    tidy)
        # tidy = 주간 정비 (일/수 10:00)
        # 1. 기존 tidy (inbox→active/archived 정리)
        python3 "${T9}/t9_seed.py" tidy >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 2. 고아 엔티티 자동 정리
        python3 "${T9}/t9_seed.py" orphans --fix >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 3. 아카이브→메모리 통합
        python3 "${T9}/t9_seed.py" consolidate >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 4. FTS5 인덱스 재구축 (검색 정합성 유지)
        python3 "${T9}/t9_seed.py" rebuild-fts >> "${LOG_DIR}/tidy_cron.log" 2>&1
        ;;
    weekly_health|weekly)
        bash "${PIPES}/weekly_health.sh" >> "${LOG_DIR}/weekly_health.log" 2>&1
        ;;
    healthcheck|health)
        python3 "${PIPES}/healthcheck.py" --tg >> "${LOG_DIR}/healthcheck_cron.log" 2>&1
        ;;
    rc_health|rc)
        bash "${PIPES}/rc_health.sh" >> "${LOG_DIR}/rc_health.log" 2>&1
        ;;
    overnight)
        python3 "${PIPES}/overnight.py" >> "${LOG_DIR}/overnight_cron.log" 2>&1
        ;;
    db_sync)
        # WSL 네이티브 DB → NTFS 복사 (Syncthing 동기화용)
        WSL_DB="/home/winn/.t9os_data/.t9.db"
        NTFS_DB="${T9}/.t9.db.sync"
        if [ -f "$WSL_DB" ]; then
            cp "$WSL_DB" "$NTFS_DB" 2>/dev/null && echo "[$(date)] DB sync OK" >> "${LOG_DIR}/db_sync.log"
        fi
        ;;
    *)
        echo "Usage: $0 {deadline_notify|ceo_brief|t9_auto|calendar|sc41|tidy|overnight|healthcheck}"
        exit 1
        ;;
esac
