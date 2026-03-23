# ADR-061: 명시적 승인 없이 파일 수정/생성 금지 — 대화 모드 우선

- 날짜: 2026-03-17
- 상태: 채택됨
- 결정: cc는 설계자의 명시적 승인 없이 파일을 수정/생성하지 않는다. 대화 모드를 우선하고, 작업 실행은 설계자이 지시할 때만 수행한다. 단, HOTL T1(완전자율) 작업은 예외.
- 이유: cc가 선제적으로 파일을 수정하면 의도하지 않은 변경이 발생. 특히 project-alpha PHILOSOPHY_ANCHOR.md 같은 핵심 문서를 cc가 임의 수정하면 비전 왜곡 위험.
- 대안: cc 완전 자율 (비전 왜곡 위험), 모든 작업 사전 승인 (비효율)
- 결과: memory/feedback_no_edit_without_approval.md, HOTL 자율성 티어(ADR-011)와 연계
- 출처: memory/feedback_no_edit_without_approval.md

## Simondon Mapping
모듈레이션의 제어: 자기 형태 재조형(파일 수정)의 권한을 설계자(환경)이 보유하여, 기술적 개체(cc)의 자율성과 통제의 균형을 유지.
