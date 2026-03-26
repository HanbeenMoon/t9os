#!/usr/bin/env bash
# SC41 + Calendar cron runner for WSL
# Usage:
#   sc41_cron_runner.sh          → run SC41 Canvas sync
#   sc41_cron_runner.sh calendar → run Google Calendar sync
#   sc41_cron_runner.sh all      → run both

set -euo pipefail

HANBEEN="/mnt/c/Users/winn/HANBEEN"
PIPES_DIR="${HANBEEN}/T9OS/pipes"

# Load environment variables
if [ -f "${HANBEEN}/_keys/.env.sh" ]; then
    source "${HANBEEN}/_keys/.env.sh"
fi

# Google OAuth 포함 모든 키가 _keys/.env.sh에 통합됨 (2026-03-23)

MODE="${1:-sc41}"

case "$MODE" in
    sc41)
        python3 "${PIPES_DIR}/sc41_cron.py"
        ;;
    calendar)
        python3 "${PIPES_DIR}/calendar_sync.py"
        ;;
    all)
        python3 "${PIPES_DIR}/sc41_cron.py"
        python3 "${PIPES_DIR}/calendar_sync.py"
        ;;
    *)
        echo "Usage: $0 {sc41|calendar|all}"
        exit 1
        ;;
esac
