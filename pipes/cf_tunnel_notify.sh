#!/usr/bin/env bash
# Cloudflare Quick Tunnel URL 변경 감지 → TG 알림
LOG="$HOME/.t9os_data/cloudflare-tunnel.log"
LAST_URL_FILE="/tmp/.cf_tunnel_last_url"

URL=$(grep "trycloudflare.com" "$LOG" 2>/dev/null | tail -1 | grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com')

if [ -z "$URL" ]; then
    exit 0
fi

LAST_URL=$(cat "$LAST_URL_FILE" 2>/dev/null)
if [ "$URL" != "$LAST_URL" ]; then
    echo "$URL" > "$LAST_URL_FILE"
    # TG 알림
    # 셸 스크립트는 config.py 경유 불가 — 여기만 하드코딩 허용
    HANBEEN="/mnt/c/Users/winn/HANBEEN"
    python3 -c "
import sys; sys.path.insert(0, '${HANBEEN}/T9OS/pipes')
from tg_common import tg_send
tg_send('[CF Tunnel] SSH 백업 URL 변경:\n${URL}\n\n노트북에서: ssh -o ProxyCommand=\"cloudflared access ssh --hostname ${URL}\" winn@${URL}')
" 2>/dev/null || true
    echo "[$(date)] URL notified: $URL"
fi
