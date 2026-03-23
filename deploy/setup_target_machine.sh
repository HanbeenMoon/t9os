#!/bin/bash
# ============================================================
# T9 OS — 대상 머신 원클릭 셋업 스크립트
# 세종PC 또는 노트북의 WSL에서 실행
# 실행: bash /mnt/d/T9_DEPLOY/scripts/setup_target_machine.sh
# ============================================================
set -euo pipefail

echo "========================================="
echo " T9 OS 환경 셋업 시작"
echo " 대상: $(hostname)"
echo " 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# === 설정 ===
# USB 패키지 경로 자동 감지
if [ -d "/mnt/d/T9_DEPLOY" ]; then
  PKG="/mnt/d/T9_DEPLOY"
elif [ -d "/mnt/e/T9_DEPLOY" ]; then
  PKG="/mnt/e/T9_DEPLOY"
else
  echo "[FAIL] T9_DEPLOY 폴더를 찾을 수 없습니다."
  echo "  → USB가 마운트되었는지 확인: ls /mnt/d/ 또는 ls /mnt/e/"
  echo "  → 수동 마운트: sudo mkdir -p /mnt/d && sudo mount -t drvfs D: /mnt/d"
  exit 1
fi

HANBEEN_WIN="/mnt/c/Users/$(whoami)/HANBEEN"
HANBEEN_WSL="$HOME/code/HANBEEN"

echo "[INFO] 패키지 위치: $PKG"
echo "[INFO] 설치 위치:   $HANBEEN_WIN"
echo ""

# === Phase 1: 기본 패키지 설치 ===
echo "=== Phase 1: 시스템 패키지 ==="

sudo apt-get update -qq
sudo apt-get install -y -qq \
  git curl wget jq python3 python3-pip python3-venv \
  ripgrep build-essential 2>/dev/null

echo "[PASS] 시스템 패키지 설치 완료"

# === Phase 2: NVM + Node.js ===
echo ""
echo "=== Phase 2: NVM + Node.js ==="

if [ ! -d "$HOME/.nvm" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  echo "[PASS] NVM 설치 완료"
else
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  echo "[SKIP] NVM 이미 설치됨"
fi

# Node 22 설치 (서울PC와 동일)
if ! node --version 2>/dev/null | grep -q "v22"; then
  nvm install 22
  nvm use 22
  nvm alias default 22
  echo "[PASS] Node.js v22 설치 완료"
else
  echo "[SKIP] Node.js v22 이미 설치됨"
fi

# === Phase 3: CLI 도구 설치 ===
echo ""
echo "=== Phase 3: AI CLI 도구 ==="

# Claude Code
if ! command -v claude &>/dev/null; then
  npm install -g @anthropic-ai/claude-code
  echo "[PASS] Claude Code 설치 완료"
else
  echo "[SKIP] Claude Code 이미 설치됨 ($(claude --version 2>/dev/null || echo 'unknown'))"
fi

# Codex
if ! command -v codex &>/dev/null; then
  npm install -g @openai/codex
  echo "[PASS] Codex 설치 완료"
else
  echo "[SKIP] Codex 이미 설치됨"
fi

# Gemini CLI
if ! command -v gemini &>/dev/null; then
  npm install -g @google/gemini-cli
  echo "[PASS] Gemini CLI 설치 완료"
else
  echo "[SKIP] Gemini CLI 이미 설치됨"
fi

# === Phase 4: Python 패키지 ===
echo ""
echo "=== Phase 4: Python 패키지 ==="

pip3 install --user --quiet \
  requests beautifulsoup4 PyMuPDF openai 2>/dev/null || true
echo "[PASS] Python 핵심 패키지 설치 완료"
echo "[INFO] GPU 의존 패키지(paddleocr, faster-whisper)는 수동 설치 필요"

# === Phase 5: 폴더 구조 + 데이터 배치 ===
echo ""
echo "=== Phase 5: 폴더 구조 생성 + 데이터 복사 ==="

# HANBEEN 루트 생성
mkdir -p "$HANBEEN_WIN"
mkdir -p "$HANBEEN_WIN/_ai/logs/cc" "$HANBEEN_WIN/_ai/logs/cx" "$HANBEEN_WIN/_ai/logs/gm"
mkdir -p "$HANBEEN_WIN/_legacy"
mkdir -p "$HANBEEN_WIN/PROJECTS"

# T9 OS 코어 복사
echo "  [5a] T9 OS 코어..."
rsync -a "$PKG/T9OS/" "$HANBEEN_WIN/T9OS/"

# .claude 인프라 복사
echo "  [5b] .claude 인프라..."
rsync -a "$PKG/.claude/" "$HANBEEN_WIN/.claude/"

# 루트 설정 파일
echo "  [5c] 루트 설정..."
cp "$PKG/CLAUDE.md" "$HANBEEN_WIN/"
[ -f "$PKG/AGENTS.md" ] && cp "$PKG/AGENTS.md" "$HANBEEN_WIN/"
[ -f "$PKG/GEMINI.md" ] && cp "$PKG/GEMINI.md" "$HANBEEN_WIN/"
[ -f "$PKG/.gitignore" ] && cp "$PKG/.gitignore" "$HANBEEN_WIN/"

# _keys (API 키) — 루트와 _legacy 양쪽에 배치
if [ -d "$PKG/data/_keys" ]; then
  echo "  [5d] API 키..."
  mkdir -p "$HANBEEN_WIN/_keys"
  cp -r "$PKG/data/_keys/"* "$HANBEEN_WIN/_keys/"
  # _legacy/_keys에도 복사 (호환성)
  mkdir -p "$HANBEEN_WIN/_legacy/_keys"
  cp -r "$PKG/data/_keys/"* "$HANBEEN_WIN/_legacy/_keys/"
fi

# _legacy (아카이빙 데이터)
if [ -d "$PKG/data/_legacy" ]; then
  echo "  [5e] 아카이빙 데이터 (시간 소요)..."
  rsync -a --progress "$PKG/data/_legacy/" "$HANBEEN_WIN/_legacy/"
fi

# 작업 로그
if [ -d "$PKG/data/_ai" ]; then
  echo "  [5f] 작업 로그..."
  rsync -a "$PKG/data/_ai/" "$HANBEEN_WIN/_ai/"
fi

# PROJECTS
if [ -d "$PKG/data/PROJECTS" ]; then
  echo "  [5g] PROJECTS..."
  rsync -a "$PKG/data/PROJECTS/" "$HANBEEN_WIN/PROJECTS/"
fi

echo "[PASS] 데이터 복사 완료"

# === Phase 6: 심볼릭링크 생성 ===
echo ""
echo "=== Phase 6: 심볼릭링크 ==="

# ~/code/HANBEEN → /mnt/c/Users/.../HANBEEN
mkdir -p "$HOME/code"
if [ -L "$HANBEEN_WSL" ]; then
  rm "$HANBEEN_WSL"
fi
ln -sf "$HANBEEN_WIN" "$HANBEEN_WSL"
echo "[PASS] ~/code/HANBEEN → $HANBEEN_WIN"

# T9OS/data 내부 심볼릭링크
T9DATA="$HANBEEN_WIN/T9OS/data"
# notion_dump
if [ -d "$HANBEEN_WIN/_legacy/_notion_dump" ]; then
  ln -sf "$HANBEEN_WIN/_legacy/_notion_dump" "$T9DATA/notion_dump" 2>/dev/null || true
fi
# personal_dump
if [ -d "$HANBEEN_WIN/_legacy/_personal_dump" ]; then
  ln -sf "$HANBEEN_WIN/_legacy/_personal_dump" "$T9DATA/personal_dump" 2>/dev/null || true
fi
echo "[PASS] T9OS/data 심볼릭링크 생성"

# T9OS/logs → _ai/logs
if [ -d "$HANBEEN_WIN/_ai/logs" ]; then
  rm -f "$HANBEEN_WIN/T9OS/logs" 2>/dev/null || true
  ln -sf "$HANBEEN_WIN/_ai/logs" "$HANBEEN_WIN/T9OS/logs" 2>/dev/null || true
fi

# T9OS/data/cc_sessions_raw → 로컬 Claude 세션 (대상 PC)
CLAUDE_PROJ_DIR="$HOME/.claude/projects/-mnt-c-Users-$(whoami)-HANBEEN"
mkdir -p "$CLAUDE_PROJ_DIR" 2>/dev/null || true
rm -f "$T9DATA/cc_sessions_raw" 2>/dev/null || true
ln -sf "$CLAUDE_PROJ_DIR" "$T9DATA/cc_sessions_raw" 2>/dev/null || true

# .stfolder (Syncthing 마커)
touch "$HANBEEN_WIN/.stfolder" 2>/dev/null || true

# === Phase 7: bashrc 설정 ===
echo ""
echo "=== Phase 7: bashrc 설정 ==="

BASHRC_MARKER="# === T9 OS CONFIG ==="
if ! grep -q "$BASHRC_MARKER" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "$BASHRC_MARKER" >> ~/.bashrc
  cat "$PKG/config/bashrc_t9_append.sh" >> ~/.bashrc
  echo "# === T9 OS CONFIG END ===" >> ~/.bashrc
  echo "[PASS] bashrc T9 설정 추가 완료"
else
  echo "[SKIP] bashrc에 T9 설정이 이미 있음"
fi

# === Phase 8: SSH 키 (선택) ===
echo ""
echo "=== Phase 8: SSH 키 ==="

if [ -d "$PKG/config/ssh" ] && [ ! -f ~/.ssh/id_ed25519 ]; then
  mkdir -p ~/.ssh
  cp "$PKG/config/ssh/id_ed25519" ~/.ssh/
  cp "$PKG/config/ssh/id_ed25519.pub" ~/.ssh/
  chmod 600 ~/.ssh/id_ed25519
  chmod 644 ~/.ssh/id_ed25519.pub
  echo "[PASS] SSH 키 설치 완료"
elif [ -f ~/.ssh/id_ed25519 ]; then
  echo "[SKIP] SSH 키 이미 존재"
else
  echo "[WARN] USB에 SSH 키 없음. 필요 시 수동 복사"
fi

# === Phase 9: Git 설정 ===
echo ""
echo "=== Phase 9: Git 설정 ==="

git config --global user.name "HanbeenMoon" 2>/dev/null || true
git config --global user.email "hanbeen@t9os.dev" 2>/dev/null || true
echo "[PASS] Git 사용자 설정 완료"

# === Phase 10: .stignore ===
if [ -f "$PKG/config/.stignore" ] && [ ! -f "$HANBEEN_WIN/.stignore" ]; then
  cp "$PKG/config/.stignore" "$HANBEEN_WIN/.stignore"
  echo "[PASS] .stignore 복사 완료"
fi

# === Phase 11: Syncthing 설치 안내 ===
echo ""
echo "=== Phase 11: Syncthing (선택) ==="
echo "[INFO] Syncthing 설치는 Windows에서 수동으로:"
echo "  1. https://syncthing.net/downloads/ 에서 Windows 64-bit 다운로드"
echo "  2. 설치 후 실행 → http://localhost:8384"
echo "  3. 서울PC 장치 ID 추가: MDL6VSN-YF5RFNG-WRFVUZF-5OP5YGQ-YYRSXXZ-YVP5DQL-EQX4RUP-55J2XAP"
echo "  4. 공유 폴더 HANBEEN 추가: C:\\Users\\$(whoami)\\HANBEEN"
echo "  5. 서울PC에서도 이 장치 ID 추가"
echo ""
echo "  서울PC Syncthing device ID (참고):"
echo "  seoul-desktop: MDL6VSN-YF5RFNG-WRFVUZF-5OP5YGQ-YYRSXXZ-YVP5DQL-EQX4RUP-55J2XAP"
echo "  sejong-pc:     SCAZ77M-UFT7MUN-DG53SAK-4HAXETP-WOOXSZI-Z5YWWRP-2A2TW2H-3EIBVA4"

# === 검증 ===
echo ""
echo "========================================="
echo " 설치 검증"
echo "========================================="

PASS=0
FAIL=0

check() {
  if eval "$2" &>/dev/null; then
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $1"
    FAIL=$((FAIL + 1))
  fi
}

check "HANBEEN 폴더"        "[ -d '$HANBEEN_WIN' ]"
check "T9OS 폴더"           "[ -d '$HANBEEN_WIN/T9OS' ]"
check ".claude 폴더"        "[ -d '$HANBEEN_WIN/.claude' ]"
check "CLAUDE.md"            "[ -f '$HANBEEN_WIN/CLAUDE.md' ]"
check "t9_seed.py"           "[ -f '$HANBEEN_WIN/T9OS/t9_seed.py' ]"
check "심볼릭링크"            "[ -L '$HANBEEN_WSL' ]"
check "_keys"                "[ -d '$HANBEEN_WIN/_keys' ]"
check "hooks"                "[ -f '$HANBEEN_WIN/.claude/hooks/session-start.sh' ]"
check "skills"               "[ -d '$HANBEEN_WIN/.claude/skills/t9-daily' ]"
check "node"                 "command -v node"
check "claude"               "command -v claude"
check "codex"                "command -v codex"
check "gemini"               "command -v gemini"
check "python3"              "command -v python3"
check "git"                  "command -v git"

echo ""
echo "========================================="
echo " 결과: PASS=$PASS / FAIL=$FAIL"
echo "========================================="
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "모든 검증 통과! T9 OS 사용 준비 완료."
  echo ""
  echo "사용법:"
  echo "  source ~/.bashrc    # 설정 리로드"
  echo "  cc                  # Claude Code 시작 (T9 OS 자동 로드)"
  echo "  cx                  # Codex 시작"
  echo "  gm                  # Gemini CLI 시작"
else
  echo "$FAIL 건 실패. 위 로그를 확인하세요."
fi

echo ""
echo "설치 완료: $(date '+%Y-%m-%d %H:%M:%S')"
