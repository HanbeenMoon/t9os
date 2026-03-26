#!/bin/bash
# t9os-public 자동 동기화 스크립트
# 용도: post-commit hook 또는 수동 실행
# 민감정보 제외, 코드/문서만 동기화

T9="${1:-/mnt/c/Users/winn/HANBEEN/T9OS}"
PUBLIC="${2:-/mnt/c/Users/winn/HANBEEN/t9os-public}"

if [ ! -d "$PUBLIC" ]; then
    echo "[SKIP] t9os-public 폴더 없음"
    exit 0
fi

# 핵심 디렉토리 동기화 (민감정보 제외)
for dir in constitution lib pipes decisions tests telos; do
    if [ -d "$T9/$dir" ]; then
        rsync -a --delete \
            --exclude="__pycache__" \
            --exclude="*.pyc" \
            --exclude=".t9*" \
            "$T9/$dir/" "$PUBLIC/$dir/" 2>/dev/null
    fi
done

# 루트 파일 동기화
for f in t9_seed.py t9_viz.py BIBLE.md README.md LICENSE CITATION.cff \
         CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md SECURITY.md \
         .gitignore .editorconfig .gitattributes; do
    [ -f "$T9/$f" ] && cp "$T9/$f" "$PUBLIC/$f" 2>/dev/null
done

# pycache 정리
find "$PUBLIC" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

echo "[sync_public] $(date '+%H:%M:%S') 동기화 완료"
