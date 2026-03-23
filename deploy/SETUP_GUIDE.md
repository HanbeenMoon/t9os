# T9 OS 환경 복제 가이드
# 새 컴퓨터 (WSL 없음, 아무것도 없음) → T9 OS 완전 구동

---

## 전제
- Windows 10/11 PC (세종PC, 노트북 등)
- WSL 없음, 개발 도구 없음, 완전 백지
- USB(D:)에 이 패키지가 들어있음

## 소요시간: 15~20분 (인터넷 속도에 따라)

---

## Step 1: WSL + 데이터 복사 (Windows, 5분)

1. USB를 PC에 꽂는다
2. **Windows PowerShell을 관리자 권한으로 실행** (시작 → PowerShell 검색 → 마우스 우클릭 → 관리자로 실행)
3. 다음 명령 입력:

```powershell
Set-ExecutionPolicy Bypass -Scope Process
D:\T9_DEPLOY\step1_install_wsl.ps1
```

이 스크립트가:
- WSL + Ubuntu 설치
- USB에서 C:\Users\{사용자}\HANBEEN\ 으로 데이터 복사
- 재부팅 안내

4. **재부팅** (y 누르면 자동)

---

## Step 2: WSL 환경 셋업 (Ubuntu, 10~15분)

1. 재부팅 후 **시작 메뉴 → Ubuntu** 실행
2. 첫 실행 시 사용자명/비밀번호 설정 (아무거나)
3. Ubuntu 터미널에서:

```bash
bash /mnt/d/T9_DEPLOY/step2_setup_wsl.sh
```

이 스크립트가 자동으로:
- git, python3, jq, ripgrep 등 시스템 패키지
- NVM + Node.js v22
- Claude Code, Codex, Gemini CLI (npm)
- Python 패키지 (requests, PyMuPDF, openai 등)
- ~/code/HANBEEN 심볼릭링크
- T9OS/data 내부 심볼릭링크 (notion_dump, personal_dump 등)
- bashrc에 T9 설정 추가 (alias cc/cx/gm, 로그함수, API키 로드)
- SSH 키 복사
- Git 설정
- **18항목 자동 검증**

---

## Step 3: 확인 (2분)

```bash
source ~/.bashrc
cc    # Claude Code 시작 → "T9 OS 세션 시작" 출력 확인
```

T9 Seed 테스트:
```bash
cd ~/code/HANBEEN
python3 T9OS/t9_seed.py status
python3 T9OS/t9_seed.py daily
```

---

## 트러블슈팅

### "WSL이 설치 안 됨" / "Ubuntu가 안 보임"
- Windows 버전이 너무 오래됨 → Windows Update 먼저
- BIOS에서 가상화 기능(VT-x) 비활성화 → BIOS 진입해서 켜기
- 수동: `wsl --install -d Ubuntu` 후 재부팅

### "D: 드라이브가 안 보임"
```bash
# WSL에서 수동 마운트
sudo mkdir -p /mnt/d
sudo mount -t drvfs D: /mnt/d
ls /mnt/d/T9_DEPLOY/
```

### "claude 명령어를 찾을 수 없음"
```bash
source ~/.bashrc
# 또는
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
npm install -g @anthropic-ai/claude-code
```

### "API 키 로드 안 됨"
```bash
# 키 파일 확인
cat ~/code/HANBEEN/_keys/.env.txt
# 없으면:
cat ~/code/HANBEEN/_legacy/_keys/.env.txt
# 그래도 없으면 서울PC에서 복사
```

### "t9_seed.py 에러"
```bash
cd ~/code/HANBEEN
python3 T9OS/t9_seed.py reindex
```

---

## 패키지 내용물

```
D:\T9_DEPLOY\
├── step1_install_wsl.ps1    ← Step 1 (PowerShell)
├── step2_setup_wsl.sh       ← Step 2 (Ubuntu)
├── SETUP_GUIDE.md           ← 이 파일
├── README.txt               ← 간단 안내
├── CLAUDE.md                ← 프로젝트 컨텍스트
├── AGENTS.md                ← 에이전트 설정
├── GEMINI.md                ← Gemini 설정
├── .gitignore
├── T9OS/                    ← T9 OS 코어 (~540MB)
│   ├── BIBLE.md
│   ├── t9_seed.py
│   ├── .t9.db
│   ├── constitution/
│   ├── telos/
│   ├── field/inbox/
│   └── ...
├── .claude/                 ← Claude Code 인프라
│   ├── hooks/
│   ├── skills/ (14개)
│   ├── agents/ (3개)
│   ├── rules/ (2개)
│   └── settings.json
├── config/
│   └── ssh/                 ← SSH 키
└── data/
    ├── _keys/               ← API 키
    ├── _legacy/
    │   ├── _notion_dump/    ← 노션 아카이브 (~115MB)
    │   └── _personal_dump/  ← 개인 아카이브 (~123MB)
    └── _ai/logs/            ← 3월 작업 로그
```

---

*생성: 2026-03-16, 서울PC (cc)*
