# ADR-074: T9OS 대수술 (2026-03-23)

- 날짜: 2026-03-23
- 상태: Active
- 결정: T9OS 코드베이스 전수 점검 및 품질 대수술 실행. bare except 전량 제거, DB 오염 복구, 엔티티 대량 트리아지, smoke test 도입, OLA Phase 0+1 구현, 감시단 cx 전환, codex 토큰 최적화.
- 이유:
  - 세션 간 전달되지 않는 stale 정보 축적 (WORKING.md 오염, TECH_DEBT 미갱신)
  - bare except로 에러가 숨겨지던 코드 품질 문제
  - DB integrity malformed 상태 발견
  - 감시단 마지막 실행이 6일 전
  - 긴급 엔티티 291건 중 대부분 false positive
  - T9OS 변경에 대한 설계자 두려움 (안전망 부재)
- 결과:
  - bare except 0건 (t9_seed.py 8개소 + pipes/ 5개소 + hooks 1개소)
  - DB dump+rebuild로 완전 복구
  - smoke test 37항목 ALL CLEAR
  - 엔티티 트리아지 350건+ 전이
  - safe_change.sh 스냅샷/검증/롤백 체계
  - OLA Phase 1 Orient 훅 가동 (관찰+리마인더, 차단 없음)
  - 감시단 G1~G7 cx 엔진 전체 실행 (P0 0건)
  - codex 토큰 최적화 (19회→7회 호출, ~60% 절약)
  - lib/registry.py 파이프라인 단일 소스 (SRBB 해소)
  - 6개 신규 도구 전부 자동화 체계 편입

## Simondon Mapping

- **준안정 상태 복원**: 과안정(경직)에서 준안정(변화 잠재력 보존)으로. safe_change.sh가 변조(modulation) 가능성을 열어둠.
- **전도(transduction)**: AT1 세션의 OLA 인사이트가 T9OS에 전파. 프로젝트 간 패턴 전이의 실례.
