# ============================================================
# T9 OS — bashrc 추가 설정
# 이 파일을 ~/.bashrc 끝에 추가하면 T9 환경 완성
# ============================================================

# Windows 경로 제거 (WSL 속도 향상)
export PATH=$(echo "$PATH" | tr ":" "\n" | grep -v "/mnt/c" | tr "\n" ":")

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# 클코 로그 함수
log-cc() {
  local logdir=~/code/HANBEEN/_ai/logs/cc
  mkdir -p "$logdir"
  local date=$(date +%Y%m%d)
  local time=$(date +%H%M%S)
  local count=$(ls "$logdir"/${date}_CC_*.txt 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local name="${1:-작업}"
  local id="${2:-noid}"
  local file="${logdir}/${date}_CC_${num}_(${id})_${time}_${name}.txt"
  cat > "$file"
  echo "로그 저장: $file"
}

# 코덱스 로그 함수
log-cx() {
  local logdir=~/code/HANBEEN/_ai/logs/cx
  mkdir -p "$logdir"
  local date=$(date +%Y%m%d)
  local time=$(date +%H%M%S)
  local count=$(ls "$logdir"/${date}_CX_*.txt 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local name="${1:-작업}"
  local id="${2:-noid}"
  local file="${logdir}/${date}_CX_${num}_(${id})_${time}_${name}.txt"
  cat > "$file"
  echo "로그 저장: $file"
}

# Gemini 로그 함수
log_gm() {
  local logdir=~/code/HANBEEN/_ai/logs/gm
  mkdir -p "$logdir"
  local count=$(find "$logdir" -maxdepth 1 -name "*.txt" 2>/dev/null | wc -l)
  local num=$(printf "%03d" $((count + 1)))
  local date_str=$(date +%Y%m%d)
  local time_str=$(date +%H%M%S)
  local name="${1:-작업}"
  local filepath="${logdir}/${date_str}_GM_${num}_${time_str}_${name}.txt"
  cat > "$filepath"
  echo "로그 저장: $filepath"
}

# _keys/.env.txt 자동 로드 (루트 또는 _legacy에서)
_T9_ENV=""
if [ -f ~/code/HANBEEN/_keys/.env.txt ]; then
  _T9_ENV=~/code/HANBEEN/_keys/.env.txt
elif [ -f ~/code/HANBEEN/_legacy/_keys/.env.txt ]; then
  _T9_ENV=~/code/HANBEEN/_legacy/_keys/.env.txt
fi
if [ -n "$_T9_ENV" ]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" || "$line" =~ ^[[:space:]] ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    [[ -z "$key" ]] && continue
    if [[ "$key" == "GOOGLE_API_KEY" || "$key" == "GEMINI_API_KEY" ]]; then
      continue
    fi
    export "$key=$value" 2>/dev/null
  done < "$_T9_ENV"
fi

# CLI 별칭
alias cc="cd ~/code/HANBEEN && claude --dangerously-skip-permissions"
alias cx="cd ~/code/HANBEEN && codex --dangerously-bypass-approvals-and-sandbox"
gm() { cd ~/code/HANBEEN && env -u GOOGLE_API_KEY -u GEMINI_API_KEY gemini --approval-mode=yolo "$@"; }

# WSL에서 Windows 파일 열기
wopen() {
  local win_path
  win_path=$(wslpath -w "$1" 2>/dev/null || echo "$1")
  /mnt/c/Windows/System32/cmd.exe /c start "" "$win_path" 2>/dev/null
}
export -f wopen
