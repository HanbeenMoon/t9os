#!/bin/bash
# T9OS 주간 건강검진 — cron: 0 9 * * 1 (매주 월요일 9시)
# 7가지 체크 → 문제 있으면 TG 알림

set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1

HANBEEN="/mnt/c/Users/winn/HANBEEN"
T9="$HANBEEN/T9OS"
DB="$HOME/.t9os_data/.t9.db"
REPORT=""

# 1. DB 무결성
DB_CHECK=$(sqlite3 "$DB" "PRAGMA integrity_check;" 2>&1)
[ "$DB_CHECK" != "ok" ] && REPORT+="❌ DB 무결성 실패: $DB_CHECK\n"

# 2. 중복 DB 파일
DB_COUNT=$(find "$HANBEEN" -name ".t9.db" -not -path "*/.git/*" -not -name "*.DEAD*" -not -name "*.sync" -not -name "*.bak*" 2>/dev/null | wc -l)
[ "$DB_COUNT" -gt 0 ] && REPORT+="❌ 유령 .t9.db ${DB_COUNT}개 존재\n"

# 3. 깨진 심볼릭 (T9OS만)
BROKEN=$(find "$T9" -xtype l 2>/dev/null | wc -l)
[ "$BROKEN" -gt 0 ] && REPORT+="❌ 깨진 심볼릭: ${BROKEN}개\n"

# 4. 하드코딩 DB 경로
HARDCODED=$(grep -rn '\.t9\.db' "$T9/" --include='*.py' 2>/dev/null | grep -v config.py | grep -v __pycache__ | grep -v "detail\|#\|DEAD\|snapshot\|legacy\|t9os_data\|_WSL_DB\|_wsl\|fallback\|from lib\|smoke_test\|verify_claims" | wc -l)
[ "$HARDCODED" -gt 0 ] && REPORT+="❌ 하드코딩 DB 경로: ${HARDCODED}건\n"

# 5. pycache
PYCACHE=$(find "$T9" -type d -name "__pycache__" 2>/dev/null | wc -l)
[ "$PYCACHE" -gt 0 ] && REPORT+="⚠️ pycache: ${PYCACHE}개 (자동 삭제)\n" && find "$T9" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 6. t9os-public 미러
PUBLIC="$HANBEEN/t9os-public"
if [ -d "$PUBLIC" ]; then
    DRIFT=$(diff -rq "$T9/constitution" "$PUBLIC/constitution" 2>/dev/null | wc -l)
    DRIFT=$((DRIFT + $(diff -q "$T9/t9_seed.py" "$PUBLIC/t9_seed.py" 2>/dev/null | wc -l)))
    [ "$DRIFT" -gt 0 ] && REPORT+="❌ t9os-public 불일치: ${DRIFT}건\n"
fi

# 7. digest 데이터 생존
DIGEST=$(sqlite3 "$DB" "SELECT COUNT(*) FROM entities WHERE filepath LIKE '%digested_final%';" 2>/dev/null)
[ "${DIGEST:-0}" -lt 90 ] && REPORT+="❌ digest 데이터 누락: ${DIGEST}건 (99건이어야 함)\n"

# 결과
DATE=$(date '+%Y-%m-%d')
if [ -n "$REPORT" ]; then
    MSG="🔧 T9OS 주간검진 $DATE\n$REPORT"
    echo -e "$MSG"
    # TG 알림
    source "$HANBEEN/_keys/.env.sh" 2>/dev/null
    if [ -n "${T9_TG_TOKEN:-}" ] && [ -n "${T9_TG_CHAT:-}" ]; then
        curl -s "https://api.telegram.org/bot${T9_TG_TOKEN}/sendMessage" \
            -d "chat_id=${T9_TG_CHAT}" \
            -d "text=$(echo -e "$MSG")" \
            -d "parse_mode=HTML" > /dev/null 2>&1
    fi
else
    echo "✅ T9OS 주간검진 $DATE: 전부 정상"
fi
