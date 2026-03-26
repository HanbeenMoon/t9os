# ADR-057: 토큰 경제 — cc 토큰=수명, 긴 작업 직접 금지

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: cc(Claude Code)의 토큰 소비를 최소화한다. 긴 스크립트/코드 생성은 cx(Codex, GPT Plus)에 위임한다. cc는 resume+보고수령+라우팅 용도로만 사용한다. "토큰=수명"이며, 단순 작업에 2시간 이상 소비하면 중단하고 다음 단계로 전환한다.
- 이유: cc(Opus)는 cx(GPT)보다 토큰 단가가 높음. cc가 코드를 직접 작성하면 전략적 판단에 쓸 토큰이 부족해짐. "과적합 금지 → 파이프라인 1회 구축에 토큰 과소비하면 다른 프로젝트가 밀림."
- 대안: cc가 모든 작업 직접 수행 (토큰 고갈), cx만 사용 (전략 판단 부재)
- 결과: memory/feedback_cc_role_resume.md, memory/feedback_token_accuracy.md, CLAUDE.md 섹션 8 과적합 금지
- 출처: memory/feedback_cc_role_resume.md, memory/feedback_token_accuracy.md

## Simondon Mapping
에너지 경제(energetics): 시몽동의 에너지론에서 시스템은 유한한 퍼텐셜을 최적 배분해야 함. cc의 토큰은 시스템의 퍼텐셜이며, 전략적 판단에 집중 투입.
