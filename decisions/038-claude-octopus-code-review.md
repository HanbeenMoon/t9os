# ADR-038: claude-octopus 플러그인 기반 멀티 에이전트 코드 리뷰

- 날짜: 2026-03-16 (도입), 2026-03-17 (검증)
- 상태: 채택됨
- 결정: cc 코드 작업 완료 후 claude-octopus 플러그인(v9.2.0)으로 cx(gpt-5.4) + gm(gemini-3.1-pro/flash) + cc(claude-opus-4.6) 3개 프로바이더의 코드 리뷰를 자율 실행한다. P0/P1 발견 시 즉시 수정한다.
- 이유: 단일 LLM 리뷰는 맹점이 있음. 3개 모델의 교차 검증으로 하드코딩 토큰, 파싱 버그 등을 cc 단독으로는 놓치는 문제를 발견. 특히 sc41 크리덴셜 하드코딩(P0)을 octopus가 포착.
- 대안: cc 단독 리뷰 (맹점), 수동 리뷰 (시간 소모), GitHub Actions CI (설정 복잡)
- 결과: L1 + memory에 "코드 리뷰 자율 실행" 규칙 추가, orchestrate.sh 파싱 버그 발견+패치
- 출처: 20260316_CC_003_041500_T9OS_v02_시몽동개정_FinBot_ODNAR.txt, 20260317_e7c9a78f.md

## Simondon Mapping
연합 환경(associated milieu)의 다중화: 3개 기술적 개체(cc/cx/gm)가 동일 코드에 대해 독립적으로 검토하여 되먹임 루프의 해상도를 높임.
