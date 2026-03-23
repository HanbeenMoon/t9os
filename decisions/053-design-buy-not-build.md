# ADR-053: 디자인은 Buy — cc가 직접 만들지 않는다

- 날짜: 2026-03-17
- 상태: 채택됨
- 결정: 디자인 작업은 v0.dev API 등 외부 도구를 사용한다(Buy). cc가 직접 Three.js 코드로 디자인을 생성하는 것을 금지한다. project-alpha Three.js 홈페이지는 cx(Codex)가 생성하되, 디자인 품질은 G7(디자인 감시단)이 검증한다.
- 이유: cc는 디자인 전문가가 아니며, Three.js 코드로 직접 디자인하면 토큰 과소비 + 품질 미달. v0.dev 등 디자인 특화 도구가 더 효율적.
- 대안: cc가 직접 디자인 (토큰 낭비, 품질 저하), 외부 디자이너 고용 (비용)
- 결과: memory/feedback_design_buy_not_build.md 생성
- 출처: memory/feedback_design_buy_not_build.md, 20260307_CX_008_(project-alpha)_103847_인터랙티브홈페이지Threejs구현.txt

## Simondon Mapping
SRBB 원칙의 구체적 적용: Build 금지 영역을 명확히 구획하여 자원(토큰)의 과적합을 방지.
