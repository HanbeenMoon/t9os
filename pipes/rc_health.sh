#!/usr/bin/env bash
# RC 헬스체크 — claude-rc.service 상태 확인 + 자동 복구 + TG 알림 (스팸 방지)
set -uo pipefail

HANBEEN="/mnt/c/Users/winn/HANBEEN"
T9="${HANBEEN}/T9OS"
FAIL_FLAG="/tmp/.rc_health_notified"

# 비활성화된 서비스는 건드리지 않음 (의도적 중지 구분)
ENABLED=$(systemctl --user is-enabled claude-rc.service 2>/dev/null || echo "disabled")
if [ "$ENABLED" != "enabled" ]; then
    echo "[$(date)] RC disabled, skipping"
    exit 0
fi

STATUS=$(systemctl --user is-active claude-rc.service 2>/dev/null || echo "inactive")

if [ "$STATUS" = "active" ]; then
    rm -f "$FAIL_FLAG"
    echo "[$(date)] RC OK"
    exit 0
fi

# RC 다운 — 재시작 시도
echo "[$(date)] RC down ($STATUS) — restarting..."
systemctl --user restart claude-rc.service 2>/dev/null || true
sleep 3
NEW_STATUS=$(systemctl --user is-active claude-rc.service 2>/dev/null || echo "failed")

# TG 알림 — 스팸 방지 (첫 실패 + 6시간마다 재알림)
SEND_ALERT=0
if [ ! -f "$FAIL_FLAG" ]; then
    SEND_ALERT=1
else
    FLAG_AGE=$(( $(date +%s) - $(stat -c %Y "$FAIL_FLAG" 2>/dev/null || echo 0) ))
    if [ "$FLAG_AGE" -ge 21600 ]; then  # 6시간
        SEND_ALERT=1
    fi
fi

if [ "$SEND_ALERT" -eq 1 ]; then
    python3 -c "
import sys; sys.path.insert(0, '${T9}/pipes')
from tg_common import tg_send
tg_send('[RC Health] RC was ${STATUS} -> restarted -> now ${NEW_STATUS}')
" 2>/dev/null || true
    touch "$FAIL_FLAG"
fi

echo "[$(date)] RC restarted: $NEW_STATUS"
