# ADR-023: Google Calendar 직접 API 연동

- 날짜: 2026-03-06
- 상태: 채택됨
- 결정: Google Calendar API를 직접 호출하여 Dashboard에 Schedule 섹션을 추가한다. OAuth2 refresh token 방식으로 인증하고, `/api/calendar` 라우트에서 향후 7일간의 일정을 조회한다.
- 이유:
  - 일정 관리는 T9 OS의 핵심 기능이다. 마감일(Notion DB)과 별개로 시간 기반 일정(수업, 회의 등)을 표시해야 한다.
  - Google Calendar는 이미 한빈의 주요 일정 관리 도구다. 데이터를 이중 입력하지 않으려면 직접 연동해야 한다.
  - 3rd party 캘린더 서비스(Cal.com 등)는 추가 비용 + 설정 오버헤드 — SRBB 원칙상 Search(기존 Google Calendar)가 먼저다.
  - OAuth2 refresh token은 만료 없이(갱신 가능) 사용 가능하여 서버리스 환경에 적합하다.
- 대안:
  - **iCal 파싱**: 읽기 전용, 실시간성 부족 — 불채택.
  - **Notion 캘린더**: Google Calendar 대비 기능 빈약 — 불채택.
  - **캘린더 미표시**: 일정 파악을 위해 별도 앱을 열어야 함 — 폐기.
- 결과:
  - Dashboard에 오늘/내일 일정 표시. 시작/종료 시간, 제목 포함.
  - Briefing 페이지에도 오늘 일정 요약 표시.
  - 환경변수: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.
  - `calendar_sync.py` 파이프라인과 연동하여 양방향 동기화 가능(향후).

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 기술적 앙상블(ensemble technique)의 통합 — 독립된 기술적 대상(Google Calendar)을 T9 OS 앙상블에 편입시켜, 시간 정보가 시스템 전체의 개체화 과정에 참여하게 한다.
