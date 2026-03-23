#!/bin/bash
# ============================================================
# T9 OS — USB 패키지 준비 (서울PC에서 실행)
# D: 드라이브에 새 컴퓨터에서 바로 쓸 수 있는 패키지 생성
# 실행: bash T9OS/deploy/prepare_usb_package.sh
# ============================================================
set -euo pipefail

SRC="/mnt/c/Users/winn/HANBEEN"
USB="/mnt/d"
PKG="$USB/T9_DEPLOY"

echo "========================================="
echo " T9 OS USB 패키지 준비"
echo " 소스: $SRC"
echo " 대상: $PKG"
echo "========================================="

# USB 확인
if [ ! -d "$USB" ]; then
  echo "[FAIL] D: 드라이브가 마운트되어 있지 않습니다."
  exit 1
fi
AVAIL=$(df -BG "$USB" | tail -1 | awk '{print $4}' | tr -d 'G')
echo "[INFO] USB 여유: ${AVAIL}GB"
echo ""

# 기존 패키지 삭제
if [ -d "$PKG" ]; then
  echo "[INFO] 기존 T9_DEPLOY 삭제 중..."
  rm -rf "$PKG"
fi
mkdir -p "$PKG"/{config/ssh,data/_legacy,data/_keys,data/_ai/logs/cc,data/_ai/logs/cx,data/_ai/logs/gm}

# ============================
echo "[1/9] T9 OS 코어 (t9_seed, BIBLE, constitution, telos, field, spaces)..."
rsync -r --no-perms --no-owner --no-group --copy-links \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='data/cc_sessions_raw' \
  --exclude='data/notion_dump' \
  --exclude='data/personal_dump' \
  --exclude='logs' \
  "$SRC/T9OS/" "$PKG/T9OS/"
echo "  → $(du -sh "$PKG/T9OS/" | cut -f1)"

# ============================
echo "[2/9] .claude 인프라 (hooks, skills, agents, rules, settings)..."
rsync -r --no-perms --no-owner --no-group --copy-links "$SRC/.claude/" "$PKG/.claude/"
echo "  → $(du -sh "$PKG/.claude/" | cut -f1)"

# ============================
echo "[3/9] 루트 설정 파일..."
for f in CLAUDE.md AGENTS.md GEMINI.md .gitignore; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$PKG/"
done

# ============================
echo "[4/9] API 키 (_keys)..."
if [ -f "$SRC/_legacy/_keys/.env.txt" ]; then
  cp "$SRC/_legacy/_keys/.env.txt" "$PKG/data/_keys/.env.txt"
elif [ -f "$SRC/_keys/.env.txt" ]; then
  cp "$SRC/_keys/.env.txt" "$PKG/data/_keys/.env.txt"
fi
echo "  → $(du -sh "$PKG/data/_keys/" | cut -f1)"

# ============================
echo "[5/9] 노션 아카이브 (_notion_dump ~115MB)..."
if [ -d "$SRC/_legacy/_notion_dump" ]; then
  rsync -r --no-perms --no-owner --no-group --copy-links "$SRC/_legacy/_notion_dump/" "$PKG/data/_legacy/_notion_dump/"
  echo "  → $(du -sh "$PKG/data/_legacy/_notion_dump/" | cut -f1)"
fi

# ============================
echo "[6/9] 개인 아카이브 (_personal_dump ~123MB)..."
if [ -d "$SRC/_legacy/_personal_dump" ]; then
  rsync -r --no-perms --no-owner --no-group --copy-links "$SRC/_legacy/_personal_dump/" "$PKG/data/_legacy/_personal_dump/"
  echo "  → $(du -sh "$PKG/data/_legacy/_personal_dump/" | cut -f1)"
fi

# ============================
echo "[7/9] 작업 로그 (3월분만)..."
for subdir in cc cx gm; do
  if [ -d "$SRC/_ai/logs/$subdir" ]; then
    find "$SRC/_ai/logs/$subdir/" -maxdepth 1 -name "202603*" -type f 2>/dev/null | \
      while read f; do cp "$f" "$PKG/data/_ai/logs/$subdir/"; done
  fi
done
echo "  → $(du -sh "$PKG/data/_ai/" | cut -f1)"

# ============================
echo "[8/9] SSH 키 + 설정..."
if [ -f ~/.ssh/id_ed25519 ]; then
  cp ~/.ssh/id_ed25519 "$PKG/config/ssh/"
  cp ~/.ssh/id_ed25519.pub "$PKG/config/ssh/"
  echo "  → SSH 키 복사 완료"
fi

# ============================
echo "[9/9] 셋업 스크립트 복사..."
cp "$SRC/T9OS/deploy/step1_install_wsl.ps1" "$PKG/"
cp "$SRC/T9OS/deploy/step2_setup_wsl.sh" "$PKG/"
cp "$SRC/T9OS/deploy/SETUP_GUIDE.md" "$PKG/"
# LF 보장
for f in "$PKG/step2_setup_wsl.sh"; do
  sed -i 's/\r$//' "$f" 2>/dev/null || true
done

# ============================
# README (USB 루트에)
cat > "$PKG/README.txt" << 'README_EOF'
========================================
 T9 OS 환경 셋업 패키지
 생성: 서울PC (DESKTOP-AI2ATA5)
========================================

새 컴퓨터에서 2단계로 완료:

[Step 1] Windows PowerShell (관리자 권한)에서:
  Set-ExecutionPolicy Bypass -Scope Process
  D:\T9_DEPLOY\step1_install_wsl.ps1

  → WSL + Ubuntu 설치 + 데이터 복사
  → 재부팅 필요

[Step 2] 재부팅 후 Ubuntu 터미널에서:
  bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh

  → Node.js, Claude Code, Codex, Gemini CLI 설치
  → 심볼릭링크, bashrc, SSH 키, Git 설정
  → 자동 검증 (18항목)

[완료 후]
  source ~/.bashrc
  cc    ← Claude Code 시작 (T9 OS 자동 로드)

상세 가이드: SETUP_GUIDE.md 참조
========================================
README_EOF

echo ""
echo "========================================="
echo " USB 패키지 완료!"
echo "========================================="
du -sh "$PKG"
echo ""
echo "내용물:"
du -sh "$PKG"/* 2>/dev/null | sort -rh
echo ""
echo "새 컴퓨터에서:"
echo "  Step 1: PowerShell(관리자) → D:\\T9_DEPLOY\\step1_install_wsl.ps1"
echo "  Step 2: Ubuntu → bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh"
