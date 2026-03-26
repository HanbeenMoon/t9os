# ADR-021: GitHub 경유 데이터 프록시 — 로컬 로그를 Dashboard에 연동

- 날짜: 2026-03-05
- 상태: 채택됨
- 결정: 로컬 파일시스템의 CC/CX 로그를 GitHub API를 경유하여 Vercel 배포된 Dashboard에서 조회한다. git push로 로그를 GitHub에 동기화하고, Dashboard의 `/api/logs` 라우트가 GitHub Contents API로 로그 파일 목록과 내용을 가져온다.
- 이유:
  - Vercel 서버리스 환경에서 로컬 파일시스템에 직접 접근할 수 없다.
  - 로컬 PC에 API 서버를 띄우면 네트워크 구성(포트 포워딩, DDNS 등) 오버헤드가 크다.
  - GitHub는 이미 레포 호스팅에 사용 중이므로 추가 인프라 비용이 0이다.
  - git push만 하면 데이터가 자동으로 GitHub에 동기화된다 — 기존 워크플로우에 자연스럽게 통합된다.
- 대안:
  - **로컬 API 서버**: 항상 켜져 있어야 함, 네트워크 설정 복잡 — 폐기.
  - **S3/GCS 업로드**: 추가 서비스 비용 + 설정 — 불채택.
  - **Syncthing → 공유 경로**: Vercel에서 접근 불가 — 불채택.
  - **로그 미표시**: 핵심 운영 데이터 누락 — 폐기.
- 결과:
  - `_ai/logs/cc/`, `_ai/logs/cx/` 디렉토리의 로그가 Dashboard Activity Feed에 표시.
  - git push 주기에 따라 데이터 지연 발생 가능 (실시간은 아님, 준실시간).
  - GitHub API rate limit(5000/hr) 내에서 충분히 운영 가능.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 전도(transduction) — 로컬 환경의 정보가 GitHub을 매개로 클라우드 환경으로 전도되어, 환경 경계를 넘어 동일한 정보가 다른 맥락에서 재개체화된다.
