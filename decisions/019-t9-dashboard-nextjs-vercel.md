# ADR-019: T9 Dashboard — Next.js + Vercel 배포 아키텍처

- 날짜: 2026-03-05
- 상태: 채택됨
- 결정: T9 OS의 시각화 대시보드를 Next.js(App Router) + Tailwind CSS로 구현하고, Vercel에 배포한다. prebuild 스크립트(`export-t9data.sh`)로 로컬 데이터를 JSON으로 export하여 빌드에 포함한다.
- 이유:
  - Notion 대시보드에서 벗어나기 위해 자체 UI가 필요했다. Notion은 커스터마이징 한계, API 불안정, 외부 의존성 문제가 있었다.
  - Next.js App Router는 API Routes를 내장하여 별도 백엔드 없이 Notion/GitHub/Calendar API를 프록시할 수 있다.
  - Vercel은 Next.js 네이티브 지원, 무료 Hobby 플랜, 자동 배포(git push)를 제공한다.
  - prebuild export 패턴으로 로컬 전용 데이터(t9.db, 파일시스템)를 Vercel 환경에서도 사용할 수 있다.
  - Tailwind CSS는 유틸리티 퍼스트로 빠른 프로토타이핑에 적합하다.
- 대안:
  - **Notion 대시보드 유지**: 커스터마이징 불가, API 의존 — 폐기.
  - **정적 사이트 (Astro/Hugo)**: API Routes 미지원, 실시간 데이터 연동 어려움 — 불채택.
  - **CLI 대시보드 (blessed/ink)**: 모바일 접근 불가, 비개발자 UX 열악 — 불채택.
  - **자체 서버 (Express/FastAPI)**: 서버 관리 오버헤드, 대학생 환경에서 과잉 — 불채택.
- 결과:
  - `PROJECTS/t9-dashboard/` 디렉토리에 독립 Next.js 프로젝트 생성.
  - Notion(프로젝트/마감일), GitHub(커밋/로그), Google Calendar(일정) API Routes 구현.
  - Vercel 환경변수로 API 키 관리.
  - `export-t9data.sh`가 빌드 전 `t9data.json`, `arch-data.json`, `integrity.json` 생성.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 기술적 대상의 구체화(concrétisation) — 분산된 데이터 소스(Notion, GitHub, Calendar, SQLite)를 하나의 통합 인터페이스로 구체화하여, 시스템 전체의 상태를 단일 지점에서 파악 가능하게 한다.
