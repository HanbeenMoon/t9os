# ADR-033: T9 OS UX 5원칙 — Zero Decision 중심 설계

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: T9 OS UX를 5원칙으로 정립한다: (1) Zero Decision(선택지 제거), (2) One Breath(한숨에 끝나는 인터랙션), (3) Ambient Awareness(존재감 없는 정보 제공), (4) Graceful Degradation(우아한 저하), (5) Progressive Disclosure(점진적 공개). 단축 명령(idea/do/go/done)과 t9 alias를 도입한다.
- 이유: PKM 도구 연구에서 "캡처 시 분류를 요구하면 캡처율이 급락" 확인. 설계자 피드백 "UX가 나빠서 안 쓰게 된다"에 대응. Steve Krug "Don't Make Me Think", Calm Technology 원칙 참조.
- 대안: 기존 CLI 명령어 체계 유지 (진입장벽 높음), GUI 대시보드 개발 (Build vs Buy 위반)
- 결과: UX_PRINCIPLES.md 생성, L1에 "설계자 메시지 우선/UX 우선/맥락 이해 우선" 규칙 추가
- 출처: 20260316_CC_005_130000_전수조사_정리_UX.txt

## Simondon Mapping
구체화(concretization): 분리된 기능(캡처, 분류, 전이)이 사용자 의도 기반의 단일 인터페이스로 수렴하여 다기능적 통합 달성.
