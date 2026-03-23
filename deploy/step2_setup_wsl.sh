#!/bin/bash
# ============================================================
# T9 OS Step 2 — WSL Ubuntu 내부 환경 셋업 (완전 새 컴퓨터)
# Ubuntu 터미널에서 실행: bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh
# ============================================================
set -euo pipefail

echo "========================================="
echo " T9 OS Step 2: WSL 환경 셋업"
echo " 호스트: $(hostname)"
echo " 시각: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

# === 설정 ===
# Windows 사용자명 감지 (여러 방법 시도)
WIN_USER=""
# 방법 1: HANBEEN 폴더가 이미 있는 사용자 찾기
for u in /mnt/c/Users/*/; do
  uname=$(basename "$u")
  [[ "$uname" == "Public" || "$uname" == "Default" || "$uname" == "Default User" || "$uname" == "All Users" ]] && continue
  if [ -d "/mnt/c/Users/$uname/HANBEEN" ]; then
    WIN_USER="$uname"
    break
  fi
done
# 방법 2: HANBEEN 없으면 Desktop이 있는 일반 사용자
if [ -z "$WIN_USER" ]; then
  for u in /mnt/c/Users/*/; do
    uname=$(basename "$u")
    [[ "$uname" == "Public" || "$uname" == "Default" || "$uname" == "Default User" || "$uname" == "All Users" || "$uname" == "desktop.ini" ]] && continue
    if [ -d "/mnt/c/Users/$uname/Desktop" ]; then
      WIN_USER="$uname"
      break
    fi
  done
fi
if [ -z "$WIN_USER" ]; then
  echo "[FAIL] Windows 사용자를 찾을 수 없습니다."
  echo "  → 수동 지정: WIN_USER=사용자명 bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh"
  exit 1
fi
echo "[INFO] Windows 사용자: $WIN_USER"
HANBEEN_WIN="/mnt/c/Users/$WIN_USER/HANBEEN"
HANBEEN_WSL="$HOME/code/HANBEEN"

# Step 1에서 이미 Windows에 복사했는지 확인
if [ ! -f "$HANBEEN_WIN/CLAUDE.md" ]; then
  echo "[WARN] Step 1이 아직 안 됐거나 HANBEEN 폴더가 비어있습니다."
  echo "  → USB에서 직접 복사합니다..."

  # USB 찾기
  PKG=""
  for drv in d e f g; do
    if [ -d "/mnt/$drv/T9_DEPLOY" ]; then
      PKG="/mnt/$drv/T9_DEPLOY"
      break
    fi
  done

  if [ -z "$PKG" ]; then
    echo "[FAIL] USB의 T9_DEPLOY 폴더를 찾을 수 없습니다."
    echo "  → USB 마운트: sudo mkdir -p /mnt/d && sudo mount -t drvfs D: /mnt/d"
    exit 1
  fi

  echo "USB 감지: $PKG"
  mkdir -p "$HANBEEN_WIN"

  # 데이터 복사
  echo "  T9OS 복사 중..."
  cp -r "$PKG/T9OS" "$HANBEEN_WIN/"
  echo "  .claude 복사 중..."
  cp -r "$PKG/.claude" "$HANBEEN_WIN/"
  echo "  루트 파일 복사 중..."
  cp "$PKG/CLAUDE.md" "$HANBEEN_WIN/" 2>/dev/null || true
  cp "$PKG/AGENTS.md" "$HANBEEN_WIN/" 2>/dev/null || true
  cp "$PKG/GEMINI.md" "$HANBEEN_WIN/" 2>/dev/null || true
  cp "$PKG/.gitignore" "$HANBEEN_WIN/" 2>/dev/null || true
  echo "  _legacy 복사 중..."
  [ -d "$PKG/data/_legacy" ] && cp -r "$PKG/data/_legacy" "$HANBEEN_WIN/_legacy"
  echo "  _keys 복사 중..."
  [ -d "$PKG/data/_keys" ] && mkdir -p "$HANBEEN_WIN/_keys" && cp -r "$PKG/data/_keys/"* "$HANBEEN_WIN/_keys/"
  echo "  _ai 복사 중..."
  [ -d "$PKG/data/_ai" ] && cp -r "$PKG/data/_ai" "$HANBEEN_WIN/_ai"
  echo "[PASS] 데이터 복사 완료"
fi

echo ""
echo "=== [1/8] 시스템 패키지 ==="
sudo apt-get update -qq 2>/dev/null
sudo apt-get install -y -qq \
  git curl wget jq python3 python3-pip python3-venv \
  ripgrep build-essential unzip 2>/dev/null
echo "[PASS]"

echo ""
echo "=== [2/8] NVM + Node.js v22 ==="
if [ ! -d "$HOME/.nvm" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh 2>/dev/null | bash
fi
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

if ! node --version 2>/dev/null | grep -q "v22"; then
  nvm install 22
  nvm use 22
  nvm alias default 22
fi
echo "[PASS] Node $(node --version)"

echo ""
echo "=== [3/8] AI CLI 도구 ==="
command -v claude &>/dev/null || npm install -g @anthropic-ai/claude-code
command -v codex &>/dev/null || npm install -g @openai/codex
command -v gemini &>/dev/null || npm install -g @google/gemini-cli
echo "[PASS] claude=$(claude --version 2>/dev/null || echo 'installed')"
echo "       codex=$(codex --version 2>/dev/null || echo 'installed')"
echo "       gemini=$(gemini --version 2>/dev/null || echo 'installed')"

echo ""
echo "=== [4/8] Python 패키지 ==="
pip3 install --user --quiet --break-system-packages \
  requests beautifulsoup4 PyMuPDF openai 2>/dev/null || \
pip3 install --user --quiet \
  requests beautifulsoup4 PyMuPDF openai 2>/dev/null || true
echo "[PASS]"

echo ""
echo "=== [5/8] 심볼릭링크 ==="
mkdir -p "$HOME/code"
[ -L "$HANBEEN_WSL" ] && rm "$HANBEEN_WSL"
[ -e "$HANBEEN_WSL" ] && rm -rf "$HANBEEN_WSL"
ln -sf "$HANBEEN_WIN" "$HANBEEN_WSL"
echo "[PASS] ~/code/HANBEEN → $HANBEEN_WIN"

# T9OS 내부 심볼릭링크
T9DATA="$HANBEEN_WIN/T9OS/data"
mkdir -p "$T9DATA" 2>/dev/null || true

# 기존 심볼릭링크 제거 후 재생성 (서울PC 경로 → 대상PC 경로)
rm -f "$T9DATA/notion_dump" "$T9DATA/personal_dump" "$T9DATA/cc_sessions_raw" 2>/dev/null || true

[ -d "$HANBEEN_WIN/_legacy/_notion_dump" ] && \
  ln -sf "$HANBEEN_WIN/_legacy/_notion_dump" "$T9DATA/notion_dump"
[ -d "$HANBEEN_WIN/_legacy/_personal_dump" ] && \
  ln -sf "$HANBEEN_WIN/_legacy/_personal_dump" "$T9DATA/personal_dump"

# cc_sessions_raw → 로컬 Claude 프로젝트
CLAUDE_PROJ="$HOME/.claude/projects/-mnt-c-Users-${WIN_USER}-HANBEEN"
mkdir -p "$CLAUDE_PROJ" 2>/dev/null || true
ln -sf "$CLAUDE_PROJ" "$T9DATA/cc_sessions_raw"

# T9OS/logs → _ai/logs
rm -f "$HANBEEN_WIN/T9OS/logs" 2>/dev/null || true
[ -d "$HANBEEN_WIN/_ai/logs" ] && ln -sf "$HANBEEN_WIN/_ai/logs" "$HANBEEN_WIN/T9OS/logs"

echo "[PASS] 심볼릭링크 생성"

echo ""
echo "=== [6/8] bashrc T9 설정 ==="
BASHRC_MARKER="# === T9 OS CONFIG ==="
if ! grep -q "$BASHRC_MARKER" ~/.bashrc 2>/dev/null; then
  cat >> ~/.bashrc << 'BASHRC_BLOCK'

# === T9 OS CONFIG ===

# Windows 경로 제거 (WSL 속도 향상)
export PATH=$(echo "$PATH" | tr ":" "\n" | grep -v "/mnt/c" | tr "\n" ":")

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# 로그 함수
log-cc() {
  local logdir=~/code/HANBEEN/_ai/logs/cc
  mkdir -p "$logdir"
  local date=$(date +%Y%m%d) time=$(date +%H%M%S)
  local count=$(ls "$logdir"/${date}_CC_*.txt 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local name="${1:-작업}" id="${2:-noid}"
  local file="${logdir}/${date}_CC_${num}_(${id})_${time}_${name}.txt"
  cat > "$file"
  echo "로그 저장: $file"
}
log-cx() {
  local logdir=~/code/HANBEEN/_ai/logs/cx
  mkdir -p "$logdir"
  local date=$(date +%Y%m%d) time=$(date +%H%M%S)
  local count=$(ls "$logdir"/${date}_CX_*.txt 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local name="${1:-작업}" id="${2:-noid}"
  local file="${logdir}/${date}_CX_${num}_(${id})_${time}_${name}.txt"
  cat > "$file"
  echo "로그 저장: $file"
}
log_gm() {
  local logdir=~/code/HANBEEN/_ai/logs/gm
  mkdir -p "$logdir"
  local count=$(find "$logdir" -maxdepth 1 -name "*.txt" 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local date_str=$(date +%Y%m%d) time_str=$(date +%H%M%S)
  local name="${1:-작업}"
  local filepath="${logdir}/${date_str}_GM_${num}_${time_str}_${name}.txt"
  cat > "$filepath"
  echo "로그 저장: $filepath"
}

# API 키 자동 로드
_T9_ENV=""
[ -f ~/code/HANBEEN/_keys/.env.txt ] && _T9_ENV=~/code/HANBEEN/_keys/.env.txt
[ -z "$_T9_ENV" ] && [ -f ~/code/HANBEEN/_legacy/_keys/.env.txt ] && _T9_ENV=~/code/HANBEEN/_legacy/_keys/.env.txt
if [ -n "$_T9_ENV" ]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" || "$line" =~ ^[[:space:]] ]] && continue
    key="${line%%=*}"; value="${line#*=}"
    [[ -z "$key" || "$key" == "GOOGLE_API_KEY" || "$key" == "GEMINI_API_KEY" ]] && continue
    export "$key=$value" 2>/dev/null
  done < "$_T9_ENV"
fi

# CLI 별칭
alias cc="cd ~/code/HANBEEN && claude --dangerously-skip-permissions"
alias cx="cd ~/code/HANBEEN && codex --dangerously-bypass-approvals-and-sandbox"
gm() { cd ~/code/HANBEEN && env -u GOOGLE_API_KEY -u GEMINI_API_KEY gemini --approval-mode=yolo "$@"; }

# Windows 파일 열기
wopen() {
  /mnt/c/Windows/System32/cmd.exe /c start "" "$(wslpath -w "$1" 2>/dev/null || echo "$1")" 2>/dev/null
}
export -f wopen

# === T9 OS CONFIG END ===
BASHRC_BLOCK
  echo "[PASS] bashrc 설정 추가"
else
  echo "[SKIP] 이미 설정됨"
fi

echo ""
echo "=== [7/8] SSH 키 + Git ==="
# SSH 키 (USB에서 복사)
PKG=""
for drv in d e f g; do
  [ -d "/mnt/$drv/T9_DEPLOY/config/ssh" ] && PKG="/mnt/$drv/T9_DEPLOY" && break
done
if [ -n "$PKG" ] && [ -d "$PKG/config/ssh" ] && [ ! -f ~/.ssh/id_ed25519 ]; then
  mkdir -p ~/.ssh
  cp "$PKG/config/ssh/id_ed25519" ~/.ssh/
  cp "$PKG/config/ssh/id_ed25519.pub" ~/.ssh/
  chmod 600 ~/.ssh/id_ed25519
  chmod 644 ~/.ssh/id_ed25519.pub
  echo "[PASS] SSH 키 설치"
elif [ -f ~/.ssh/id_ed25519 ]; then
  echo "[SKIP] SSH 키 이미 존재"
else
  echo "[WARN] SSH 키 없음 — 나중에 수동 생성: ssh-keygen -t ed25519"
fi

git config --global user.name "HanbeenMoon" 2>/dev/null || true
git config --global user.email "sgimoon24213@gmail.com" 2>/dev/null || true
echo "[PASS] Git 설정 완료"

echo ""
echo "=== [8/8] 로그 폴더 생성 ==="
mkdir -p "$HANBEEN_WIN/_ai/logs/cc" "$HANBEEN_WIN/_ai/logs/cx" "$HANBEEN_WIN/_ai/logs/gm"
mkdir -p "$HANBEEN_WIN/T9OS/field/inbox"
mkdir -p "$HANBEEN_WIN/T9OS/spaces/active" "$HANBEEN_WIN/T9OS/spaces/suspended" "$HANBEEN_WIN/T9OS/spaces/archived"
mkdir -p "$HANBEEN_WIN/T9OS/artifacts"
mkdir -p "$HANBEEN_WIN/T9OS/memory"
echo "[PASS]"

# === 최종 검증 ===
echo ""
echo "========================================="
echo " 최종 검증"
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

check "HANBEEN 폴더"       "[ -d '$HANBEEN_WIN' ]"
check "T9OS"               "[ -d '$HANBEEN_WIN/T9OS' ]"
check ".claude"            "[ -d '$HANBEEN_WIN/.claude' ]"
check "CLAUDE.md"          "[ -f '$HANBEEN_WIN/CLAUDE.md' ]"
check "t9_seed.py"         "[ -f '$HANBEEN_WIN/T9OS/t9_seed.py' ]"
check ".t9.db"             "[ -f '$HANBEEN_WIN/T9OS/.t9.db' ]"
check "심볼릭링크"          "[ -L '$HANBEEN_WSL' ]"
check "_keys"              "[ -f '$HANBEEN_WIN/_keys/.env.txt' ] || [ -f '$HANBEEN_WIN/_legacy/_keys/.env.txt' ]"
check "hooks"              "[ -f '$HANBEEN_WIN/.claude/hooks/session-start.sh' ]"
check "skills"             "[ -d '$HANBEEN_WIN/.claude/skills/t9-daily' ]"
check "constitution"       "[ -f '$HANBEEN_WIN/T9OS/constitution/L1_execution.md' ]"
check "node"               "command -v node"
check "python3"            "command -v python3"
check "git"                "command -v git"
check "claude"             "command -v claude"
check "codex"              "command -v codex"
check "gemini"             "command -v gemini"
check "로그 폴더"           "[ -d '$HANBEEN_WIN/_ai/logs/cc' ]"

echo ""
echo "========================================="
if [ "$FAIL" -eq 0 ]; then
  echo " ALL PASS ($PASS/$PASS) — T9 OS 준비 완료!"
else
  echo " PASS=$PASS / FAIL=$FAIL"
fi
echo "========================================="
echo ""
echo "사용법:"
echo "  source ~/.bashrc"
echo "  cc                # Claude Code 시작 (T9 OS 자동 로드)"
echo "  cx                # Codex 시작"
echo "  gm                # Gemini CLI 시작"
echo ""
echo "T9 Seed 테스트:"
echo "  cd ~/code/HANBEEN"
echo "  python3 T9OS/t9_seed.py status"
echo "  python3 T9OS/t9_seed.py daily"
echo ""
echo "완료: $(date '+%Y-%m-%d %H:%M:%S')"
