# ADR-056: Notion UI → 로컬 cc 중심 체제 전면 이관

- 날짜: 2026-03-15
- 상태: 채택됨
- Supersedes: ADR-029 (Notion 실행큐/아카이브 DB 분리)
- 결정: T9 오케스트레이션의 중심을 Notion 웹 UI에서 로컬 cc 기반 체제로 전면 이관한다. 작업큐, 프로젝트 관리, 마감일 추적, 일일 브리프 등 모든 운영 기능을 T9 Seed 엔진 + 로컬 파일시스템으로 이전한다. Notion은 데이터 소스(SSOT)로만 유지.
- 이유: Notion UI는 AI 에이전트가 직접 조작하기 어렵고, 웹 의존성으로 오프라인 불가. cc가 직접 파일 생성/수정/검색이 가능한 로컬 체제가 자동화에 적합. 설계자 피드백: "이관 시 데이터뿐 아니라 운영기능(알림/캘린더)까지 이관해야 완료."
- 대안: Notion API 중심 운영 유지 (지연, 오프라인 불가), 다른 SaaS (동일 문제)
- 결과: Notion DB 9개 이관, 작업큐 320건+ResultArchive 131건 로컬 검색 가능, T9 Seed가 모든 운영 기능 대체
- 출처: 20260315_0114b06a.md (세션 대화), memory/project_t9os_migration.md, memory/feedback_migration_completeness.md

## Simondon Mapping
기술적 개체의 환경 이전: 기술적 앙상블(T9 OS)이 클라우드(Notion) 연합 환경에서 로컬(파일시스템+SQLite) 연합 환경으로 이주. 환경 변화에 맞춰 개체도 재구조화됨.
