# ============================================================
# T9 OS Step 1 — WSL + Ubuntu 설치 (Windows PowerShell 관리자 권한)
# 새 컴퓨터에서 USB 꽂고 이 파일을 관리자 PowerShell에서 실행
# 실행: Set-ExecutionPolicy Bypass -Scope Process; D:\T9_DEPLOY\step1_install_wsl.ps1
# ============================================================

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " T9 OS Step 1: WSL + Ubuntu 설치" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. WSL 설치
Write-Host "[1/3] WSL + Ubuntu 설치 중..." -ForegroundColor Yellow
wsl --install -d Ubuntu --no-launch 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] WSL이 이미 설치되어 있거나 재부팅이 필요합니다." -ForegroundColor Yellow
}

# 2. HANBEEN 폴더 생성
$hanbeenPath = "C:\Users\$env:USERNAME\HANBEEN"
Write-Host "[2/3] HANBEEN 폴더 생성: $hanbeenPath" -ForegroundColor Yellow
if (-not (Test-Path $hanbeenPath)) {
    New-Item -ItemType Directory -Path $hanbeenPath -Force | Out-Null
}

# 3. USB에서 핵심 파일 복사 (Windows 레벨)
$usbDeploy = "D:\T9_DEPLOY"
Write-Host "[3/3] USB에서 데이터 복사 중..." -ForegroundColor Yellow

# robocopy로 빠른 복사
robocopy "$usbDeploy\T9OS" "$hanbeenPath\T9OS" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "$usbDeploy\.claude" "$hanbeenPath\.claude" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "$usbDeploy\data\_legacy" "$hanbeenPath\_legacy" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "$usbDeploy\data\_keys" "$hanbeenPath\_keys" /E /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "$usbDeploy\data\_ai" "$hanbeenPath\_ai" /E /NFL /NDL /NJH /NJS /NC /NS /NP

# 루트 파일
Copy-Item "$usbDeploy\CLAUDE.md" "$hanbeenPath\" -Force 2>$null
Copy-Item "$usbDeploy\AGENTS.md" "$hanbeenPath\" -Force 2>$null
Copy-Item "$usbDeploy\GEMINI.md" "$hanbeenPath\" -Force 2>$null
Copy-Item "$usbDeploy\.gitignore" "$hanbeenPath\" -Force 2>$null

# .stfolder (Syncthing 마커, 추후용)
New-Item -ItemType File -Path "$hanbeenPath\.stfolder" -Force 2>$null | Out-Null

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host " Step 1 완료!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. 컴퓨터 재부팅 (WSL 활성화)" -ForegroundColor White
Write-Host "  2. 재부팅 후 시작 메뉴 → Ubuntu 실행" -ForegroundColor White
Write-Host "  3. 사용자명/비밀번호 설정 (아무거나)" -ForegroundColor White
Write-Host "  4. Ubuntu 터미널에서:" -ForegroundColor White
Write-Host "     bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh" -ForegroundColor Yellow
Write-Host ""
Write-Host "재부팅하시겠습니까? (y/n)" -ForegroundColor Yellow
$reboot = Read-Host
if ($reboot -eq 'y') {
    Restart-Computer -Force
}
