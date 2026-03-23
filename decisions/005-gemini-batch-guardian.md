# ADR-005: Gemini batch로 감시단 실행 (cc 토큰 절약)

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 감시단 하위직원 21명을 Gemini API 기반 batch 실행(`gm_batch.py guardian`)으로 처리하고, cc(Claude Code)는 감시단장 역할(결과 취합 + P0 판단 + 수정)만 수행한다.
- 이유:
  - cc(Claude Code)의 토큰은 비싸고 제한적이다 (프리미엄 플랜을 써도 토큰이 부족한 상황이 발생). 감시단 21명을 cc 토큰으로 실행하면 실제 작업에 쓸 토큰이 부족해진다.
  - Gemini 3 Flash / 3.1 Pro는 무료이거나 매우 저렴하다. 대량 반복 검사에 최적이다.
  - 각 하위직원에게 전문 프롬프트를 부여하여 병렬 실행하면 검사 품질도 유지된다: G1(보안스캐너, 코드품질, BuildVsBuy, 에러핸들링), G2(금지어스캔, 필수어확인, 비전축소감지, 원문왜곡감지), G3(로그형식, SRBB감사) 등.
  - 결과는 `_ai/logs/gm/{timestamp}_guardian_brief.md` (CEO 브리프)로 자동 생성되어 설계자은 P0만 읽으면 된다.
- 대안:
  - **cc가 직접 전부 실행**: 토큰 과소비, 실제 작업 시간 감소 — 폐기.
  - **cx(Codex)로 실행**: GPT Plus 토큰은 cc보다 저렴하지만 무료가 아님, 코드 생성에 집중시키는 것이 효율적 — 불채택.
  - **감시단 생략**: 검증 없는 산출물은 품질 보장 불가 — 폐기.
  - **GitHub Actions CI**: 외부 서비스 의존, 로컬 파일 접근 제한 — 불채택.
- 결과:
  - `pipes/gm_batch.py`가 감시단 실행의 핵심 도구 (50KB, guardian/review/inline/summarize 모드 지원).
  - 리뷰어 프리셋: economics(10명), general(5명), code(3명), guardian(7그룹 21명).
  - CLI: `python3 T9OS/pipes/gm_batch.py guardian -t <파일> --mode light|default|full --anchor <ANCHOR> -g G1 G2 ...`
  - P0 자동 수정 워크플로우: gm_batch 실행 -> CEO brief 읽기 -> suggestion 적용 -> 재실행(회귀 검증) -> P0=0 확인.
  - Gemini 2.x 사용은 절대 금지 (L1 규칙). 3 Flash 또는 3.1 Pro만.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 기술적 앙상블(technical ensemble) — 개별 기술 객체(gm)가 상위 체계(cc 감시단장)와 역할 분담하여 전체 효율을 높이는 구조.
