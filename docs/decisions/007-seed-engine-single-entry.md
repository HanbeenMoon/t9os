# ADR-007: T9 Seed 엔진 단일 진입점 설계

- 날짜: 2026-03-15
- 상태: 채택됨
- 결정: `t9_seed.py` 하나가 모든 엔티티 관리 명령의 단일 진입점이다. capture, reindex, search, status, daily, transition, compose, approve, reflect, consolidate, history, relate, claim, release, check 등 모든 명령이 이 파일을 통해 실행된다.
- 이유:
  - "파이프라인을 만드는 파이프라인"이라는 T9 OS 핵심 컨셉에서, 시드 엔진은 모든 개체화 과정의 씨앗(seed) 역할을 한다.
  - 분산된 여러 스크립트 대신 하나의 진입점을 두면: (1) 새 세션이 알아야 할 도구가 하나뿐이고, (2) DB 접근을 중앙화하여 스키마 일관성을 보장하고, (3) self_check()로 스키마 위반을 매 작업마다 검사할 수 있다.
  - 기능 확장은 코드가 아니라 DB 데이터와 규칙 문서에서 이루어져야 한다 (L1: "t9_seed.py 1000줄 상한"). 현재 761줄.
  - 확장 명령어는 `lib/commands.py`(daily, tidy, compose, approve)로 분리하여 줄 수를 관리한다.
  - 세션 잠금은 `pipes/session_lock.py`, 세션 간 통신은 `lib/ipc.py`로 위임하되 CLI는 t9_seed.py를 통해 접근한다.
- 대안:
  - **여러 독립 스크립트**: 세션마다 어떤 스크립트를 쓸지 기억해야 함, DB 접근 분산 — 폐기.
  - **웹 API 서버**: 서버 관리 오버헤드, 대학생 환경에서 과잉 — 불채택.
  - **Make/Task 러너**: 부분 도입 가능하나 DB 접근 로직이 핵심이므로 Python 단일 파일이 효율적 — 불채택.
- 결과:
  - session-start.sh 훅에서 `reindex` + `daily` 자동 호출.
  - 별칭 지원: `do` = `compose`, `idea` = `capture`, `done` = transition to stabilized, `go` = transition to individuating.
  - `main()` 함수가 CLI 파서 역할, 모든 명령을 라우팅한다.
  - 1000줄 상한을 초과할 경우 리팩터링으로 줄 수를 유지해야 한다 (G3 규칙 감시 대상).

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 씨앗(germ) — 개체화의 시작점이 되는 구조적 씨앗으로서, 모든 상태 전이의 단일 매개자 역할.
