#!/bin/bash
# ============================================================
# T9 OS — 준비된 패키지를 USB로 복사하는 간단 스크립트
# USB 꽂은 후 실행: bash T9OS/deploy/copy_to_usb.sh
# ============================================================
set -euo pipefail

SRC="/mnt/c/Users/winn/HANBEEN"

# USB 드라이브 자동 탐지
USB=""
for drv in d e f g; do
  if [ -d "/mnt/$drv" ] 2>/dev/null; then
    USB="/mnt/$drv"
    break
  fi
done

if [ -z "$USB" ]; then
  echo "[!] USB 드라이브를 찾을 수 없습니다."
  echo ""
  echo "1. USB를 PC에 꽂으세요"
  echo "2. Windows에서 드라이브 문자를 확인하세요 (예: D:, E:)"
  echo "3. WSL에서 마운트:"
  echo "   sudo mkdir -p /mnt/d && sudo mount -t drvfs D: /mnt/d"
  echo "4. 이 스크립트를 다시 실행하세요"
  exit 1
fi

PKG_DIR="$USB/T9_DEPLOY"
echo "USB 감지: $USB"
echo "패키지 위치: $PKG_DIR"
echo ""

# prepare_usb_package.sh 호출
bash "$SRC/T9OS/deploy/prepare_usb_package.sh"
