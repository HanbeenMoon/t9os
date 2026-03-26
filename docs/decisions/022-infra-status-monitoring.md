# ADR-022: 인프라 상태 모니터링 API

- 날짜: 2026-03-05
- 상태: 채택됨
- 결정: Dashboard에 `/api/infra` 라우트를 추가하여 GitHub, Notion, local-PC, remote-PC의 연결 상태를 실시간으로 모니터링한다. 각 서비스에 헬스체크 요청을 보내고 응답 여부로 online/offline 판단.
- 이유:
  - T9 OS는 여러 외부 서비스(GitHub, Notion, Google Calendar)와 2대의 PC(서울, remote)에 의존한다.
  - 서비스 장애 시 원인 파악에 시간이 걸린다. 인프라 상태를 한눈에 보면 문제를 즉시 식별할 수 있다.
  - Tailscale로 연결된 PC 상태를 확인하면 원격 작업 가능 여부를 빠르게 판단할 수 있다.
- 대안:
  - **외부 모니터링 서비스 (UptimeRobot 등)**: 내부 PC 모니터링 불가, T9 OS 특화 불가 — 불채택.
  - **수동 확인**: ping/curl을 매번 실행하는 것은 비효율 — 폐기.
  - **모니터링 미구현**: 장애 대응 지연 — 폐기.
- 결과:
  - Dashboard 상단에 인프라 상태 표시 (GitHub, Notion, local-PC, remote-PC).
  - 각 서비스 응답 시간도 함께 표시하여 성능 저하를 감지.
  - PC 상태는 Tailscale IP로 확인.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 연합된 환경의 상태 감시 — 기술적 대상이 정상 작동하려면 연합된 환경(인프라)이 안정적이어야 한다. 환경의 상태를 모니터링하는 것은 메타안정성 유지의 전제 조건이다.
