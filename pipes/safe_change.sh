#!/bin/bash
# safe_change.sh — T9OS 변경 안전망
# 변경 전 스냅샷 + 변경 후 smoke test
# 사용법:
#   bash T9OS/pipes/safe_change.sh snapshot     # 변경 전: 스냅샷 생성
#   bash T9OS/pipes/safe_change.sh verify       # 변경 후: smoke test + 비교
#   bash T9OS/pipes/safe_change.sh rollback     # 문제 시: 스냅샷으로 복원
#   bash T9OS/pipes/safe_change.sh auto         # 전체 자동: snapshot → (대기) → verify

T9OS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT_DIR="$T9OS_DIR/data/snapshots"
LATEST="$SNAPSHOT_DIR/latest"
SMOKE_TEST="$T9OS_DIR/tests/smoke_test.py"

mkdir -p "$SNAPSHOT_DIR"

cmd_snapshot() {
    TS=$(date '+%Y%m%d_%H%M%S')
    SNAP="$SNAPSHOT_DIR/$TS"
    mkdir -p "$SNAP"

    # 핵심 파일만 스냅샷 (전체 복사는 무거움)
    TARGETS=(
        "t9_seed.py"
        "lib/config.py" "lib/commands.py" "lib/parsers.py" "lib/ipc.py"
        "pipes/healthcheck.py" "pipes/gm_batch.py" "pipes/t9_auto.py"
        "constitution/L1_execution.md" "constitution/GUARDIANS.md"
        "BIBLE.md"
    )
    for f in "${TARGETS[@]}"; do
        src="$T9OS_DIR/$f"
        if [ -f "$src" ]; then
            dir=$(dirname "$SNAP/$f")
            mkdir -p "$dir"
            cp "$src" "$SNAP/$f"
        fi
    done

    # DB 크기 + entity count 기록
    python3 -c "
import sqlite3
import pathlib; _wsl = pathlib.Path.home() / '.t9os_data' / '.t9.db'
conn = sqlite3.connect(str(_wsl) if _wsl.exists() else '$T9OS_DIR/.t9.db', timeout=5)
count = conn.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
phases = dict(conn.execute('SELECT phase, COUNT(*) FROM entities GROUP BY phase').fetchall())
conn.close()
import json
json.dump({'entities': count, 'phases': phases, 'timestamp': '$TS'}, open('$SNAP/db_state.json', 'w'))
" 2>/dev/null || echo '{"entities": "?", "error": "db_locked"}' > "$SNAP/db_state.json"

    # smoke test 실행 (baseline)
    if [ -f "$SMOKE_TEST" ]; then
        cd "$T9OS_DIR" && python3 "$SMOKE_TEST" > "$SNAP/smoke_baseline.txt" 2>&1
        PASS=$(grep "PASS=" "$SNAP/smoke_baseline.txt" | grep -oP 'PASS=\K\d+')
        FAIL=$(grep "FAIL=" "$SNAP/smoke_baseline.txt" | grep -oP 'FAIL=\K\d+')
        echo "$PASS/$((PASS+FAIL))" > "$SNAP/smoke_score.txt"
    fi

    # latest 심볼릭 링크
    rm -f "$LATEST"
    ln -s "$SNAP" "$LATEST"

    echo "  [snapshot] $TS ($(cat "$SNAP/smoke_score.txt" 2>/dev/null || echo '?') PASS)"
    echo "  경로: $SNAP"
}

cmd_verify() {
    if [ ! -L "$LATEST" ] && [ ! -d "$LATEST" ]; then
        echo "  [ERROR] 스냅샷 없음. 먼저 'safe_change.sh snapshot' 실행"
        exit 1
    fi

    SNAP=$(readlink -f "$LATEST")
    echo "  [verify] 스냅샷: $(basename "$SNAP")"

    # smoke test 실행
    if [ -f "$SMOKE_TEST" ]; then
        cd "$T9OS_DIR" && python3 "$SMOKE_TEST" > /tmp/smoke_after.txt 2>&1
        PASS_AFTER=$(grep "PASS=" /tmp/smoke_after.txt | grep -oP 'PASS=\K\d+')
        FAIL_AFTER=$(grep "FAIL=" /tmp/smoke_after.txt | grep -oP 'FAIL=\K\d+')
        PASS_BEFORE=$(cat "$SNAP/smoke_score.txt" 2>/dev/null | cut -d/ -f1)

        echo "  smoke test: BEFORE=$PASS_BEFORE AFTER=$PASS_AFTER FAIL=$FAIL_AFTER"

        if [ "$FAIL_AFTER" -gt 0 ]; then
            echo "  [WARN] smoke test 실패 $FAIL_AFTER건!"
            echo "  복원: bash T9OS/pipes/safe_change.sh rollback"
            grep "FAIL" /tmp/smoke_after.txt
            return 1
        else
            echo "  [OK] 변경 안전 확인"
            return 0
        fi
    else
        echo "  [SKIP] smoke_test.py 없음"
        return 0
    fi
}

cmd_rollback() {
    if [ ! -L "$LATEST" ] && [ ! -d "$LATEST" ]; then
        echo "  [ERROR] 스냅샷 없음"
        exit 1
    fi

    SNAP=$(readlink -f "$LATEST")
    echo "  [rollback] 스냅샷: $(basename "$SNAP")"
    echo "  경고: 스냅샷 파일로 현재 파일을 덮어씁니다."
    echo ""

    # 복원
    find "$SNAP" -type f -not -name "*.json" -not -name "*.txt" | while read f; do
        rel=${f#$SNAP/}
        dest="$T9OS_DIR/$rel"
        if [ -f "$dest" ]; then
            cp "$f" "$dest"
            echo "  복원: $rel"
        fi
    done

    echo ""
    echo "  [rollback] 완료. smoke test 재실행 권장."
}

case "${1:-help}" in
    snapshot) cmd_snapshot ;;
    verify)   cmd_verify ;;
    rollback) cmd_rollback ;;
    auto)
        cmd_snapshot
        echo ""
        echo "  --- 작업 수행 후 'safe_change.sh verify' 실행 ---"
        ;;
    *)
        echo "사용법: safe_change.sh {snapshot|verify|rollback|auto}"
        echo ""
        echo "  snapshot  — 변경 전 스냅샷 생성"
        echo "  verify    — 변경 후 smoke test 비교"
        echo "  rollback  — 스냅샷으로 복원"
        echo "  auto      — snapshot + 대기 안내"
        ;;
esac
