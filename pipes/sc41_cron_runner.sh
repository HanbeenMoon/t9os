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

# Load .env.local for Google Calendar tokens (fallback handled in Python too)
if [ -f "${HANBEEN}/_legacy/PROJECTS/t9-dashboard/.env.local" ]; then
    set -a
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        export "$key"="$value"
    done < "${HANBEEN}/_legacy/PROJECTS/t9-dashboard/.env.local"
    set +a
fi

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
