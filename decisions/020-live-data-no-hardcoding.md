# ADR-020: 라이브 데이터 원칙 — 하드코딩 제거 + Notion DB화

- 날짜: 2026-03-05
- 상태: 채택됨
- 결정: Dashboard의 모든 데이터를 라이브 소스(Notion DB, GitHub API, 파일시스템)에서 가져온다. 하드코딩된 프로젝트 목록, 로그, 마감일을 전면 제거하고, Notion DB를 프로젝트/마감일의 단일 소스(SSOT)로 지정한다. 이후(03-17) Dashboard에서 Projects 섹션 자체를 삭제하여 "죽은 데이터" 원천 차단.
- 이유:
  - 하드코딩은 "죽은 데이터"다. 실제 상태와 괴리가 생기면 대시보드가 거짓말을 한다.
  - Notion DB는 이미 프로젝트 관리에 사용 중이었다. 중복 입력을 제거하려면 Notion이 SSOT여야 한다.
  - 한빈의 명시적 피드백: "하드코딩은 죽은 데이터. 라이브 아니면 제거. 개체화 될 거니까" (memory `feedback_no_hardcoding.md`).
  - Projects 섹션 삭제 결정(03-17)은 하드코딩 프로젝트 카드가 Notion DB와 이중으로 존재하는 문제를 근본적으로 해결한다.
- 대안:
  - **하드코딩 유지 + 수동 갱신**: 갱신 누락 불가피, 데이터 신뢰도 하락 — 폐기.
  - **JSON 파일 기반 설정**: 빌드타임에만 반영, 실시간성 부족 — prebuild export와 조합하여 부분 채택.
  - **전부 SQLite**: Vercel 서버리스에서 로컬 DB 접근 불가 — 불채택 (prebuild export로 우회).
- 결과:
  - `/api/projects`, `/api/deadlines` 라우트가 Notion DB를 실시간 조회.
  - 로딩 UI 추가하여 API 호출 중 상태를 시각적으로 표시.
  - Projects 섹션 제거 후 Dashboard는 "상세 운영 정보", Briefing은 "핵심 요약"으로 역할 분리.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 죽은 형태(형태질료설)를 거부하고 살아있는 정보(개체화 과정)를 선택 — 하드코딩은 고정된 형태(forme)이고, 라이브 데이터는 계속 개체화되는 정보다. 시몽동이 형태질료설(hylomorphisme)을 비판한 것과 동일한 논리.
