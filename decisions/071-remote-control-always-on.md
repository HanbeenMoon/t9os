# ADR-071: Remote Control 상시 활성화

- 날짜: 2026-03-23
- 상태: 채택됨
- 결정: Claude Code `--rc` 플래그를 bashrc alias에 추가하여 모든 세션에서 remote control 자동 활성화.
- 이유:
  - 설계자이 멀티세션 운영 + 모바일 접근이 필요하다.
  - 보안 리스크는 개인 PC + Anthropic 계정 인증으로 negligible.
  - 매 세션마다 수동 활성화하는 것은 반복 노동이며, 누락 시 모바일 접근 불가.
- 대안:
  - **`/config` UI 설정**: 스키마에 해당 키 없음 — 불가.
  - **`settings.json`**: remote control 관련 설정 키 없음 — 불가.
  - **bashrc alias가 유일한 방법**: `alias cc="cd ~/code/workspace && claude --dangerously-skip-permissions --rc"` 채택.
- 결과:
  - bashrc alias에 `--rc` 플래그 추가 완료.
  - 모든 세션에서 remote control 자동 활성화.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 개체화 — 세션 단위 수동 활성화(전개체적 반복)가 시스템 수준 자동 활성화(개체화된 설정)로 전이. 매번의 의식적 행위가 구조적 자동화로 결정화된다.
