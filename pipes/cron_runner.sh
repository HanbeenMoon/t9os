#!/usr/bin/env bash
# T9 OS 범용 cron runner — 모든 파이프라인의 단일 진입점.
# config.py가 env 파일을 직접 파싱하므로 source는 백업용.
#
# Usage:
#   cron_runner.sh <파이프라인명>
#   cron_runner.sh deadline_notify
#   cron_runner.sh ceo_brief
#   cron_runner.sh t9_auto
#   cron_runner.sh calendar
#   cron_runner.sh coursework
#   cron_runner.sh tidy
#   cron_runner.sh healthcheck

set -euo pipefail

WORKSPACE="${T9OS_WORKSPACE:-/path/to/workspace}"
T9="${WORKSPACE}/T9OS"
PIPES="${T9}/pipes"
LOG_DIR="${WORKSPACE}/_ai/logs/cc"

# 환경변수 로드 (백업 — config.py가 이미 파일에서 읽지만 os.environ도 채워줌)
[ -f "${WORKSPACE}/_keys/.env.sh" ] && source "${WORKSPACE}/_keys/.env.sh"

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
    coursework)
        python3 "${PIPES}/coursework_cron.py" >> "${LOG_DIR}/coursework_cron.log" 2>&1
        ;;
    tidy)
        python3 "${T9}/t9_seed.py" tidy >> "${LOG_DIR}/tidy_cron.log" 2>&1
        ;;
    healthcheck|health)
        python3 "${PIPES}/healthcheck.py" --tg >> "${LOG_DIR}/healthcheck_cron.log" 2>&1
        ;;
    *)
        echo "Usage: $0 {deadline_notify|ceo_brief|t9_auto|calendar|coursework|tidy|healthcheck}"
        exit 1
        ;;
esac
