# ADR-014: T9 Dashboard 아키텍처 시각화 페이지

- 날짜: 2026-03-19
- 상태: 채택됨
- 결정: T9 Dashboard(T9D)에 시스템맵(Mermaid 다이어그램), ADR 목록, 기술부채 현황을 시각화하는 `/architecture` 페이지를 추가한다. `SYSTEM_MAP.md`, `INDEX.md`, `TECH_DEBT.md`를 파싱하여 `arch-data.json`으로 빌드타임 export한다.
- 이유:
  - T9 OS는 파일이 분산되어 있어 전체 구조를 한눈에 파악하기 어렵다. 시스템맵이 없으면 새 세션이 아키텍처를 이해하는 데 토큰을 낭비한다.
  - ADR은 "왜 이렇게 결정했는가"를 기록하지만, 마크다운 파일 탐색은 비효율적이다. 웹 UI로 검색+필터가 가능해야 한다.
  - 기술부채를 시각화하면 우선순위 판단이 빨라진다.
  - SRBB 원칙: Mermaid는 이미 있는 도구(Search), arch-data.json export도 기존 패턴(Reuse).
- 대안:
  - **Notion 대시보드**: Notion 의존 제거 원칙 위배 — 폐기.
  - **별도 문서 사이트**: 빌드+배포 오버헤드, T9D에 통합이 더 단순 — 불채택.
  - **CLI만**: 시각적 파악 불가, 비개발자(설계자) 접근성 낮음 — 폐기.
- 결과:
  - T9D `/architecture` 페이지 구현. Mermaid 렌더링 + ADR 카드 + 기술부채 목록.
  - `export-t9data.sh`에서 `arch-data.json` 자동 생성.
  - Vercel 배포 시 자동 갱신.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 시스템 자체의 투명성 = 메타인지 자동화의 전제 — 시스템이 자신의 구조를 시각화하는 것은 메타안정성 감시의 기본 조건이다. 보이지 않는 것은 관리할 수 없다.
