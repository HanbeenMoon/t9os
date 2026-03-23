# ADR-006: 세션 충돌 방지 claim/release 방식

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 멀티 세션 동시 운영 시 프로젝트/파일 단위로 claim/release 잠금을 사용하여 충돌을 방지한다. `.session_locks.json`에 사람이 읽을 수 있는 형태로 상태를 기록한다.
- 이유:
  - 설계자은 cc 세션을 여러 개 동시에 운영한다 (최대 3일 장기 세션 + 멀티 세션). 같은 파일을 모르고 건드리는 문제가 현실적으로 발생한다.
  - L1 절대 규칙: "같은 파일 동시 접근 금지. 병렬 실행 시 작업 겹침 확인 필수."
  - 프로젝트 단위 claim은 파일 패턴 매핑(`_DEFAULT_PROJECT_PATTERNS`)으로 관련 파일을 일괄 잠금한다. 예: "project-alpha" claim 시 `PROJECTS/project-alpha/*`, `T9OS/artifacts/project-alpha_*/*` 전체 잠금.
  - 30분 heartbeat 타임아웃으로 stale 세션 자동 정리한다.
- 대안:
  - **Git branch 분리**: 머지 충돌 해결 비용이 높고, 같은 branch에서 작업하는 경우 해결 불가 — 보완책으로만 사용.
  - **파일 잠금 (flock)**: OS 레벨 잠금은 WSL-NTFS 크로스에서 불안정 — 불채택.
  - **구두 약속**: 자동화 불가, 사람이 기억해야 함 — 폐기.
  - **Notion DB 기반 잠금**: Notion API 의존 제거 원칙에 위배 — 폐기.
- 결과:
  - `pipes/session_lock.py`에 전체 구현 (stdlib만 사용, 단일 파일, 경로 하드코딩 금지).
  - `t9_seed.py`에서 `claim/claim-file/sessions/release/check` 서브커맨드로 통합 접근.
  - 커스텀 패턴: `T9OS/config/project_patterns.json`으로 오버라이드 가능.
  - `sync_working_md()`로 `.claude/WORKING.md`의 `[SESSIONS]` 섹션을 자동 갱신.
  - 충돌 감지 시 "해당 세션이 release할 때까지 대기하거나 수동 조율 필요" 메시지 출력.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 연합된 환경의 안정화 — 다중 세션이 공유 환경(파일시스템)에서 충돌 없이 개체화를 진행할 수 있도록 환경 자체를 조율한다.
