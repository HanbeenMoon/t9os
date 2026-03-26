#!/usr/bin/env bash
# T9 OS cron runner — pipelinesingle entry point.
# config.pyenv filesourcebackup.
#
# Usage:
# cron_runner.sh <pipeline>
#   cron_runner.sh deadline_notify
#   cron_runner.sh ceo_brief
#   cron_runner.sh t9_auto
#   cron_runner.sh calendar
#   cron_runner.sh sc41
#   cron_runner.sh tidy
#   cron_runner.sh healthcheck

set -euo pipefail

HANBEEN="/mnt/c/Users/winn/HANBEEN"
T9="${HANBEEN}/T9OS"
PIPES="${T9}/pipes"
LOG_DIR="${HANBEEN}/_ai/logs/cc"

# env var (backup — config.pyfileos.environ)
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
        # tidy = (/10:00)
        # 1. existing tidy (inbox→active/archived clean up)
        python3 "${T9}/t9_seed.py" tidy >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 2. auto clean up
        python3 "${T9}/t9_seed.py" orphans --fix >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 3. archive→Integrate
        python3 "${T9}/t9_seed.py" consolidate >> "${LOG_DIR}/tidy_cron.log" 2>&1
        # 4. FTS5 index (search consistency )
        python3 "${T9}/t9_seed.py" rebuild-fts >> "${LOG_DIR}/tidy_cron.log" 2>&1
        ;;
    healthcheck|health)
        python3 "${PIPES}/healthcheck.py" --tg >> "${LOG_DIR}/healthcheck_cron.log" 2>&1
        ;;
    db_sync)
        # WSL DB → NTFS copy (Syncthing sync)
        WSL_DB="/home/winn/.t9os_data/.t9.db"
        NTFS_DB="${T9}/.t9.db.sync"
        if [ -f "$WSL_DB" ]; then
            cp "$WSL_DB" "$NTFS_DB" 2>/dev/null && echo "[$(date)] DB sync OK" >> "${LOG_DIR}/db_sync.log"
        fi
        ;;
    *)
        echo "Usage: $0 {deadline_notify|ceo_brief|t9_auto|calendar|sc41|tidy|healthcheck}"
        exit 1
        ;;
esac
