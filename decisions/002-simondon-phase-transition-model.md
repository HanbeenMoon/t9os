# ADR-002: 시몽동 5단계 전이 모델 채택

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 모든 엔티티의 생명주기를 시몽동 개체화 이론 기반 12개 상태(preindividual, impulse, tension_detected, candidate_generated, individuating, stabilized, split, merged, suspended, archived, dissolved, reactivated)와 엄격한 전이 그래프로 관리한다.
- 이유:
  - 기존 "할 일 목록" 패러다임(TODO/DOING/DONE)은 입력의 잠재성을 무시한다. 설계자의 입력은 "할 일"이 아니라 "욕구, 긴장, 가능성"이다.
  - 시몽동의 핵심 통찰: 개체가 출발점이 아니라 과정이 원본이고 개체는 부분적 결과물이다. T9 OS의 전개체(preindividual)는 분류되기를 거부하는 잠재성이다.
  - 이접(disparation) 모델링: 양립 불가능한 차원 간 긴장이 해소될 때 상태 전이가 발생한다. `_detect_tension()` 함수가 텍스트에서 대립 키워드쌍(빠르/느리, build/buy, 단순/복잡, 혼자/협업)을 감지한다.
  - split/merged를 통한 재개체화: 하나의 엔티티가 분기되거나 합쳐질 때 새 개체화 사이클이 시작된다.
  - dissolved는 "폐기"가 아니라 "배경으로 가라앉음"이다 (시몽동: 전개체는 자연에서 사라지지 않는다).
  - sediment(침전)까지 추가하여 "삭제 아닌 가라앉음, 검색 가능, daily 제외" 개념을 구현했다.
- 대안:
  - **GTD 방식 (TODO/DOING/DONE)**: 잠재성 무시, 분기/합류 불가 — 폐기.
  - **칸반 (Backlog/In Progress/Done)**: 상태가 단순, 전이 이력 추적 불가 — 폐기.
  - **자유형 태그**: 일관성 없음, 상태 전이 규칙 강제 불가 — 폐기.
- 결과:
  - `TRANSITIONS` 딕셔너리가 허용된 전이만 정의하여 잘못된 상태 전이를 차단한다.
  - `PHASE_DIR` 매핑으로 상태에 따라 파일이 자동으로 적절한 디렉토리(field/inbox, spaces/active, spaces/archived 등)로 이동한다.
  - L2 해석 규칙이 각 전이의 이접 요소(dimension_a, dimension_b, resolution_dimension)를 명시한다.
  - `telos/SIMONDON.md`에 철학적 기반이 문서화되어 있다.
  - 미구현 시몽동 개념: Transduction 경로 추적, Associated Milieu 되먹임 로깅, Concretization 수준 측정.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 개체화(individuation) 전 과정 — 전개체에서 안정화까지의 위상 전이를 이접(disparation)과 전도(transduction)로 구현한다.
