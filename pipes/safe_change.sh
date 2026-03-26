#!/bin/bash
# safe_change.sh — T9OS change
# change snapshot + change smoke test
# use:
# bash T9OS/pipes/safe_change.sh snapshot     # change : snapshot create
# bash T9OS/pipes/safe_change.sh verify       # change : smoke test + compare
# bash T9OS/pipes/safe_change.sh rollback     # : snapshot
# bash T9OS/pipes/safe_change.sh auto         # total auto: snapshot → () → verify

T9OS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT_DIR="$T9OS_DIR/data/snapshots"
LATEST="$SNAPSHOT_DIR/latest"
SMOKE_TEST="$T9OS_DIR/tests/smoke_test.py"

mkdir -p "$SNAPSHOT_DIR"

cmd_snapshot() {
    TS=$(date '+%Y%m%d_%H%M%S')
    SNAP="$SNAPSHOT_DIR/$TS"
    mkdir -p "$SNAP"

    # filesnapshot (total copy)
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

    # DB size + entity count record
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

    # smoke test execution (baseline)
    if [ -f "$SMOKE_TEST" ]; then
        cd "$T9OS_DIR" && python3 "$SMOKE_TEST" > "$SNAP/smoke_baseline.txt" 2>&1
        PASS=$(grep "PASS=" "$SNAP/smoke_baseline.txt" | grep -oP 'PASS=\K\d+')
        FAIL=$(grep "FAIL=" "$SNAP/smoke_baseline.txt" | grep -oP 'FAIL=\K\d+')
        echo "$PASS/$((PASS+FAIL))" > "$SNAP/smoke_score.txt"
    fi

    # latest
    rm -f "$LATEST"
    ln -s "$SNAP" "$LATEST"

    echo "  [snapshot] $TS ($(cat "$SNAP/smoke_score.txt" 2>/dev/null || echo '?') PASS)"
    echo "  path: $SNAP"
}

cmd_verify() {
    if [ ! -L "$LATEST" ] && [ ! -d "$LATEST" ]; then
        echo "  [ERROR] snapshot not found.  'safe_change.sh snapshot' execution"
        exit 1
    fi

    SNAP=$(readlink -f "$LATEST")
    echo "  [verify] snapshot: $(basename "$SNAP")"

    # smoke test execution
    if [ -f "$SMOKE_TEST" ]; then
        cd "$T9OS_DIR" && python3 "$SMOKE_TEST" > /tmp/smoke_after.txt 2>&1
        PASS_AFTER=$(grep "PASS=" /tmp/smoke_after.txt | grep -oP 'PASS=\K\d+')
        FAIL_AFTER=$(grep "FAIL=" /tmp/smoke_after.txt | grep -oP 'FAIL=\K\d+')
        PASS_BEFORE=$(cat "$SNAP/smoke_score.txt" 2>/dev/null | cut -d/ -f1)

        echo "  smoke test: BEFORE=$PASS_BEFORE AFTER=$PASS_AFTER FAIL=$FAIL_AFTER"

        if [ "$FAIL_AFTER" -gt 0 ]; then
            echo "  [WARN] smoke test failed $FAIL_AFTERitems!"
            echo "  : bash T9OS/pipes/safe_change.sh rollback"
            grep "FAIL" /tmp/smoke_after.txt
            return 1
        else
            echo "  [OK] change  check"
            return 0
        fi
    else
        echo "  [SKIP] smoke_test.py not found"
        return 0
    fi
}

cmd_rollback() {
    if [ ! -L "$LATEST" ] && [ ! -d "$LATEST" ]; then
        echo "  [ERROR] snapshot not found"
        exit 1
    fi

    SNAP=$(readlink -f "$LATEST")
    echo "  [rollback] snapshot: $(basename "$SNAP")"
    echo "  warning: snapshot file current file ."
    echo ""

    #
    find "$SNAP" -type f -not -name "*.json" -not -name "*.txt" | while read f; do
        rel=${f#$SNAP/}
        dest="$T9OS_DIR/$rel"
        if [ -f "$dest" ]; then
            cp "$f" "$dest"
            echo "  : $rel"
        fi
    done

    echo ""
    echo "  [rollback] completed. smoke test execution ."
}

case "${1:-help}" in
    snapshot) cmd_snapshot ;;
    verify)   cmd_verify ;;
    rollback) cmd_rollback ;;
    auto)
        cmd_snapshot
        echo ""
        echo "  --- task   'safe_change.sh verify' execution ---"
        ;;
    *)
        echo "use: safe_change.sh {snapshot|verify|rollback|auto}"
        echo ""
        echo "  snapshot  — change  snapshot create"
        echo "  verify    — change  smoke test compare"
        echo "  rollback  — snapshot "
        echo "  auto      — snapshot +  "
        ;;
esac
