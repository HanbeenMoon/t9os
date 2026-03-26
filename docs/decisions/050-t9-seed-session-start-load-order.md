# ADR-050: 세션 시작 로드 순서 — L1 → L2 → WORKING.md → state.md

- 날짜: 2026-03-15 (T9OS 초기), 2026-03-16 (v0.2 확정)
- 상태: 채택됨
- 결정: cc 세션 시작 시 반드시 L1 → L2 → WORKING.md → state.md 순서로 컨텍스트를 로드한다. session-start.sh 훅에서 T9 Seed 엔진의 reindex + daily도 자동 호출한다.
- 이유: 로드 순서가 없으면 cc가 규칙을 모른 채 작업을 시작하여 L1 위반이 발생. WORKING.md(중단 작업)와 state.md(열린 루프)를 읽어야 이전 세션의 맥락을 이어받을 수 있음.
- 대안: CLAUDE.md만 읽기 (규칙 상세 누락), 전부 자유 순서 (중요도 구분 불가)
- 결과: 체크리스트 10항목 확립, session-start.sh 자동화
- 출처: CLAUDE.md 섹션 10-11, L1_execution.md

## Simondon Mapping
전도적 전파의 시간적 순서화: 이전 세션의 잔여 전개체성(WORKING.md)이 다음 세션으로 구조적으로 전파되는 경로를 확정.
