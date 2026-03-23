#!/bin/bash
# ============================================================
# T9 OS — Syncthing 동기화 후 환경 설정 스크립트
# Syncthing으로 HANBEEN 폴더가 이미 동기화된 상태에서 실행
# 즉, USB 없이 Syncthing만으로 환경 복제할 때 사용
#
# 전제: C:\Users\{user}\HANBEEN 폴더가 Syncthing으로 동기화 완료
# 실행: bash /mnt/c/Users/{user}/HANBEEN/T9OS/deploy/setup_via_syncthing.sh
# ============================================================
set -euo pipefail

# 사용자명 자동 감지
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
HANBEEN_WIN="/mnt/c/Users/$WIN_USER/HANBEEN"
HANBEEN_WSL="$HOME/code/HANBEEN"

if [ ! -d "$HANBEEN_WIN/T9OS" ]; then
  echo "[FAIL] $HANBEEN_WIN/T9OS 가 없습니다."
  echo "  → Syncthing 동기화가 완료되었는지 확인하세요."
  exit 1
fi

echo "========================================="
echo " T9 OS 환경 설정 (Syncthing 경유)"
echo " HANBEEN: $HANBEEN_WIN"
echo "========================================="

# === Phase 1: 시스템 패키지 ===
echo "[1] 시스템 패키지 설치..."
sudo apt-get update -qq
sudo apt-get install -y -qq git curl wget jq python3 python3-pip python3-venv ripgrep build-essential 2>/dev/null
echo "[PASS]"

# === Phase 2: NVM + Node ===
echo "[2] NVM + Node.js..."
if [ ! -d "$HOME/.nvm" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
if ! node --version 2>/dev/null | grep -q "v22"; then
  nvm install 22 && nvm use 22 && nvm alias default 22
fi
echo "[PASS]"

# === Phase 3: CLI 도구 ===
echo "[3] AI CLI 도구..."
command -v claude &>/dev/null || npm install -g @anthropic-ai/claude-code
command -v codex &>/dev/null || npm install -g @openai/codex
command -v gemini &>/dev/null || npm install -g @google/gemini-cli
echo "[PASS]"

# === Phase 4: Python 패키지 ===
echo "[4] Python 패키지..."
pip3 install --user --quiet requests beautifulsoup4 PyMuPDF openai 2>/dev/null || true
echo "[PASS]"

# === Phase 5: 심볼릭링크 ===
echo "[5] 심볼릭링크..."
mkdir -p "$HOME/code"
[ -L "$HANBEEN_WSL" ] && rm "$HANBEEN_WSL"
ln -sf "$HANBEEN_WIN" "$HANBEEN_WSL"
echo "[PASS] ~/code/HANBEEN → $HANBEEN_WIN"

# === Phase 6: bashrc ===
echo "[6] bashrc 설정..."
BASHRC_MARKER="# === T9 OS CONFIG ==="
if ! grep -q "$BASHRC_MARKER" ~/.bashrc 2>/dev/null; then
  BASHRC_SRC="$HANBEEN_WIN/T9OS/deploy/config_bashrc_t9.sh"
  if [ -f "$BASHRC_SRC" ]; then
    echo "" >> ~/.bashrc
    echo "$BASHRC_MARKER" >> ~/.bashrc
    cat "$BASHRC_SRC" >> ~/.bashrc
    echo "# === T9 OS CONFIG END ===" >> ~/.bashrc
  else
    # 인라인 최소 설정
    cat >> ~/.bashrc << 'INLINE_EOF'

# === T9 OS CONFIG ===
export PATH=$(echo "$PATH" | tr ":" "\n" | grep -v "/mnt/c" | tr "\n" ":")
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
if [ -f ~/code/HANBEEN/_keys/.env.txt ]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" || "$line" =~ ^[[:space:]] ]] && continue
    key="${line%%=*}"; value="${line#*=}"
    [[ -z "$key" || "$key" == "GOOGLE_API_KEY" || "$key" == "GEMINI_API_KEY" ]] && continue
    export "$key=$value" 2>/dev/null
  done < ~/code/HANBEEN/_keys/.env.txt
fi
alias cc="cd ~/code/HANBEEN && claude --dangerously-skip-permissions"
alias cx="cd ~/code/HANBEEN && codex --dangerously-bypass-approvals-and-sandbox"
gm() { cd ~/code/HANBEEN && env -u GOOGLE_API_KEY -u GEMINI_API_KEY gemini --approval-mode=yolo "$@"; }
wopen() { /mnt/c/Windows/System32/cmd.exe /c start "" "$(wslpath -w "$1" 2>/dev/null || echo "$1")" 2>/dev/null; }
export -f wopen
# === T9 OS CONFIG END ===
INLINE_EOF
  fi
  echo "[PASS] bashrc 설정 추가"
else
  echo "[SKIP] 이미 설정됨"
fi

# === Phase 7: 검증 ===
echo ""
echo "=== 검증 ==="
PASS=0; FAIL=0
check() { if eval "$2" &>/dev/null; then echo "  [PASS] $1"; PASS=$((PASS+1)); else echo "  [FAIL] $1"; FAIL=$((FAIL+1)); fi; }
check "HANBEEN"       "[ -d '$HANBEEN_WIN' ]"
check "T9OS"          "[ -d '$HANBEEN_WIN/T9OS' ]"
check ".claude"       "[ -d '$HANBEEN_WIN/.claude' ]"
check "CLAUDE.md"     "[ -f '$HANBEEN_WIN/CLAUDE.md' ]"
check "t9_seed.py"    "[ -f '$HANBEEN_WIN/T9OS/t9_seed.py' ]"
check "symlink"       "[ -L '$HANBEEN_WSL' ]"
check "claude"        "command -v claude"
check "codex"         "command -v codex"
check "gemini"        "command -v gemini"
echo ""
echo "PASS=$PASS / FAIL=$FAIL"
echo ""
echo "완료! source ~/.bashrc 후 cc로 시작하세요."
