# ADR-044: Gemini 모델 제한 — 2.x 금지, 3 Flash 또는 3.1 Pro만

- 날짜: 2026-03-10
- 상태: 채택됨
- 결정: Gemini CLI(gm)에서 Gemini 2.x 모델 사용을 절대 금지한다. gemini-3-flash 또는 gemini-3.1-pro만 허용한다. gm alias에 --approval-mode=yolo(무승인 모드)를 기본 적용한다.
- 이유: Gemini 2.x는 한국어 처리 품질이 낮고, 3.x 대비 정확도가 현저히 떨어짐. 한빈 직접 지시: "Gemini 2.x 절대 금지."
- 대안: Gemini 2.x 허용 (품질 저하), Gemini 사용 자체 금지 (무료 토큰 활용 불가)
- 결과: .bashrc alias 수정, memory/feedback_gemini_models.md 생성
- 출처: 20260310_CX_002_(noid)_015414_GM무승인기본실행.txt, memory/feedback_gemini_models.md

## Simondon Mapping
연합 환경의 모듈레이션: 환경 구성 요소(gm 모델)의 품질 하한을 설정하여 전체 시스템의 출력 품질을 보장.
