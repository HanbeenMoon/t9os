# ADR-072: 세션 데이터 JSONL 직접 읽기 원칙

- 날짜: 2026-03-23
- 상태: Active
- 결정: 세션 대화 데이터는 JSONL을 직접 읽는다. MD 변환은 부산물이며 세션 종료를 기다리지 않는다.
- 이유:
  - 기존: session-end.sh에서 세션 종료 시에만 JSONL→MD 변환 → 활성 세션 데이터 접근 불가
  - 한빈 피드백: "세션 안 꺼도 다른 세션이 접근할 수 있어야 한다" (3/23 두 세션에서 반복 지적)
  - 제1원칙: JSONL은 실시간으로 디스크에 쓰여지고 있다. 변환을 기다릴 이유가 없다.
- 대안:
  - session-end.sh에서만 변환 (기존) → 세션 종료 전 접근 불가. 탈락.
  - cron으로 주기적 변환 → 지연 발생. 탈락.
  - JSONL 직접 읽기 → 즉시 접근. 채택.
- 결과:
  - `T9OS/pipes/session_live_read.py` 생성 (--search, --session, --sync)
  - session-start.sh에서 자동 --sync 실행
  - CLAUDE.md에 "세션 데이터 접근 원칙" 섹션 추가
  - session_recover.py는 레거시로 유지 (브리프 생성 용도)

## Simondon Mapping
전개체(JSONL) → 개체(conversations/ MD)로의 변환을 기다리는 것은 전개체의 접근성을 차단하는 것.
전개체 자체가 이미 접근 가능한 상태(실시간 디스크 기록)이므로, 변환 없이 직접 읽는 것이 시몽동의 "전개체의 잠재력 보존" 원칙에 부합.
