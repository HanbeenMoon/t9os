#!/bin/bash
# T9OS 인사이트 추출 파이프라인
# 용도: 카카오톡/옵시디언 원본에서 인사이트를 추출하고 사고 지도를 생성
# 사용: bash T9OS/pipelines/digest_insights.sh [파일경로] [출력디렉토리]
# 의존: gemini CLI (gemini-3.1-pro-preview)
# 생성일: 2026-03-16

set -euo pipefail

# === 설정 ===
MODEL="gemini-3.1-pro-preview"
PROMPT_FILE="$(dirname "$0")/prompts/insight_extract.md"
SYNTHESIS_PROMPT="$(dirname "$0")/prompts/thought_map_synthesis.md"
MAX_LINES_PER_CHUNK=6500
FILTER_MIN_LENGTH=40  # 그룹채팅에서 한빈 메시지 필터링 최소 길이

# === 입력 검증 ===
INPUT_PATH="${1:?Usage: $0 <input_file_or_dir> [output_dir]}"
OUTPUT_DIR="${2:-/tmp/t9_insights}"
mkdir -p "$OUTPUT_DIR"

if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: 프롬프트 파일 없음: $PROMPT_FILE"
    echo "T9OS/pipelines/prompts/ 디렉토리에 프롬프트가 있어야 합니다."
    exit 1
fi

PROMPT=$(cat "$PROMPT_FILE")

# === 함수 ===

extract_file() {
    local input="$1"
    local output="$2"
    local basename=$(basename "$input" | sed 's/\.[^.]*$//')
    local lines=$(wc -l < "$input")

    echo "[추출] $basename ($lines줄)"

    if [ "$lines" -gt "$MAX_LINES_PER_CHUNK" ]; then
        # 큰 파일: 청크 분할
        echo "  → 청크 분할 ($MAX_LINES_PER_CHUNK줄씩)"
        local chunk_dir="$OUTPUT_DIR/chunks_${basename}"
        mkdir -p "$chunk_dir"
        split -l "$MAX_LINES_PER_CHUNK" -d "$input" "${chunk_dir}/chunk_"

        for chunk in "${chunk_dir}"/chunk_*; do
            local chunk_name=$(basename "$chunk")
            echo "  → 처리 중: $chunk_name"
            cat "$chunk" | gemini -m "$MODEL" -p "$PROMPT" > "${OUTPUT_DIR}/${basename}_${chunk_name}_insights.md" 2>/dev/null &
        done
        wait

        # 청크 결과 합치기
        cat "${OUTPUT_DIR}/${basename}_chunk_"*"_insights.md" > "${OUTPUT_DIR}/${basename}_insights.md" 2>/dev/null
        rm -f "${OUTPUT_DIR}/${basename}_chunk_"*"_insights.md"
        rm -rf "$chunk_dir"
    else
        # 작은 파일: 직접 처리
        cat "$input" | gemini -m "$MODEL" -p "$PROMPT" > "${OUTPUT_DIR}/${basename}_insights.md" 2>/dev/null
    fi

    local size=$(wc -c < "${OUTPUT_DIR}/${basename}_insights.md" 2>/dev/null || echo 0)
    echo "  → 완료: ${size} bytes"
}

filter_hanbin_messages() {
    # 그룹채팅에서 한빈의 긴 메시지만 필터링
    local input="$1"
    local output="$2"
    grep -E "^-{5,}|(\[문 한빈\].{${FILTER_MIN_LENGTH},})" "$input" > "$output" 2>/dev/null || true
}

# === 메인 로직 ===

echo "=== T9OS 인사이트 추출 파이프라인 ==="
echo "모델: $MODEL"
echo "출력: $OUTPUT_DIR"
echo ""

if [ -d "$INPUT_PATH" ]; then
    # 디렉토리 모드: 모든 txt 파일 처리
    echo "[모드] 디렉토리 — $(ls "$INPUT_PATH"/*.txt 2>/dev/null | wc -l)개 파일"
    echo ""

    for f in "$INPUT_PATH"/*.txt; do
        lines=$(wc -l < "$f")
        basename=$(basename "$f")

        # 그룹채팅 (100K+ 줄) → 한빈 메시지만 필터링
        if [ "$lines" -gt 50000 ]; then
            echo "[필터] $basename → 한빈 긴 메시지만 추출"
            filtered="${OUTPUT_DIR}/filtered_${basename}"
            filter_hanbin_messages "$f" "$filtered"
            extract_file "$filtered" "$OUTPUT_DIR" &
        else
            extract_file "$f" "$OUTPUT_DIR" &
        fi

        # 동시 실행 수 제한 (gm rate limit 고려)
        while [ $(jobs -r | wc -l) -ge 5 ]; do
            sleep 5
        done
    done
    wait

else
    # 단일 파일 모드
    echo "[모드] 단일 파일"
    extract_file "$INPUT_PATH" "$OUTPUT_DIR"
fi

echo ""
echo "=== 인사이트 추출 완료 ==="

# === 사고 지도 통합 ===
echo ""
echo "[통합] 사고 지도 생성 중..."

# 모든 인사이트 합치기
cat "${OUTPUT_DIR}"/*_insights.md > "${OUTPUT_DIR}/ALL_raw_insights.md" 2>/dev/null

TOTAL_INSIGHTS=$(grep -c "\-\-\-" "${OUTPUT_DIR}/ALL_raw_insights.md" 2>/dev/null || echo 0)
echo "  → 총 인사이트: ${TOTAL_INSIGHTS}개"

if [ -f "$SYNTHESIS_PROMPT" ] && [ "$TOTAL_INSIGHTS" -gt 5 ]; then
    SYNTH_PROMPT=$(cat "$SYNTHESIS_PROMPT")
    cat "${OUTPUT_DIR}/ALL_raw_insights.md" | gemini -m "$MODEL" -p "$SYNTH_PROMPT" > "${OUTPUT_DIR}/THOUGHT_MAP.md" 2>/dev/null
    echo "  → 사고 지도: ${OUTPUT_DIR}/THOUGHT_MAP.md ($(wc -c < "${OUTPUT_DIR}/THOUGHT_MAP.md") bytes)"
else
    echo "  → 통합 프롬프트 없거나 인사이트 부족 — 사고 지도 스킵"
fi

echo ""
echo "=== 전체 완료 ==="
echo "결과:"
ls -la "${OUTPUT_DIR}"/*.md 2>/dev/null | awk '{print "  " $NF " (" $5 " bytes)"}'
