# ADR-024: WSL 우분투를 단일 CLI 환경으로 확정

- 날짜: 2026-03-10
- 상태: 채택됨
- 결정: 모든 CLI 작업(cc, cx, gm, git, 스크립트 실행)을 WSL 우분투에서 수행한다. PowerShell은 L2U T9_Agent 전용으로만 사용하고, 그 외 CLI 작업에서는 완전히 배제한다. SSH 키, 환경변수, gemini alias 등을 WSL에 최종 설정한다.
- 이유:
  - PowerShell과 WSL 간 경로 혼란(`/mnt/c/` vs `C:\`)이 지속적으로 발생했다.
  - Python, Node.js, git 등 개발 도구가 WSL에서 더 안정적으로 동작한다.
  - 심볼릭링크(`~/code/HANBEEN → /mnt/c/Users/winn/HANBEEN`)로 경로를 통일한다.
  - SSH 키를 WSL에서 관리하면 git push/pull이 단순해진다.
  - gemini CLI alias를 WSL bashrc에 설정하여 `gm` 명령어로 즉시 접근 가능.
- 대안:
  - **PowerShell 전면 사용**: Unix 도구 호환성 문제, 스크립트 호환 어려움 — 폐기.
  - **WSL + PowerShell 혼용**: 경로 혼란 지속, 환경 설정 이중 관리 — 폐기.
  - **네이티브 Linux**: Windows 앱(한컴, 카카오톡 등) 사용 불가 — 불채택.
- 결과:
  - `~/code/HANBEEN` 심볼릭링크로 Windows 파일시스템에 접근.
  - `.bashrc`에 gemini alias, 환경변수 설정 완료.
  - SSH 키 생성 및 GitHub 등록 완료.
  - AGENTS.md에 WSL 환경 명시.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 기술적 환경의 단일화(unification du milieu) — 분열된 기술 환경(PowerShell/WSL)을 하나로 통일하여, 에이전트가 환경 전환 비용 없이 작업에 집중할 수 있게 한다.
