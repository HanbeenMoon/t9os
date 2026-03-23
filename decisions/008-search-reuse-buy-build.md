# ADR-008: SRBB 원칙 (Search -> Reuse -> Buy -> Build)

- 날짜: 2026-03-15
- 상태: 채택됨
- 결정: 모든 새 작업 시작 전 반드시 Search -> Reuse -> Buy -> Build 순서를 따른다. Build는 "세상에 없는 것"에만 허용한다.
- 이유:
  - **12시간 삽질 사건**: Puppeteer -> 프록시 -> Zotero -> SeleniumBase 순서로 12시간 삽질한 끝에, Bright Data를 처음부터 검색했으면 1시간이면 끝날 일이었다.
  - 한빈의 핵심 철학: "Build는 세상에 없는 것(ODNAR)에만 허용. 반복/자동화는 Buy 우선." (`telos/MODELS.md`)
  - 과적합 방지: 파이프라인 1회 구축에 토큰 과소비하면 다른 프로젝트가 밀린다. 단순 작업에 2시간 이상 소비하면 중단하고 다음 단계로 전환.
  - Buy 소스 5개를 적극 활용한 결과물: PAI(TELOS), COG(스킬), codex-os(WORKING.md, VoxWatcher), CAO(오케스트레이션 패턴), Claude Code 공식(Agent Teams, Skills).
- 대안:
  - **항상 Build first**: 토큰/시간 낭비, "시스템 만드는 게 목적이 되어버린 상태"의 원인 — 폐기.
  - **항상 Buy first**: 요구사항에 정확히 맞는 도구가 없을 수 있음 — Search/Reuse를 앞에 둠.
  - **순서 없이 판단**: cc의 독자적 의사결정에 의존, 세션 간 일관성 없음 — 폐기.
- 결과:
  - L1 실행 규칙에 명시, G3 규칙 감시단이 SRBB 감사를 실행한다.
  - Reuse = 전도적 학습(transduction): 다른 프로젝트에서 만든 것을 가져다 쓸 수 있는가?
  - BIBLE v0.3의 Buy 로드맵(섹션 14)에 이행 현황이 기록되어 있다.
  - 구체적 Search 수단: grep, `t9_seed.py search`, git history, 로그 검색, `T9OS/data/conversations/`.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 구체화(concretization) — 추상적 해결을 위한 과잉 구축(Build) 대신, 이미 구체화된 기술 객체(Buy/Reuse)를 우선 채택하는 원리.
