# ADR-028: legacy-bot watcher 폐기 → T9 Agent 텔레그램 봇 전환

- 날짜: 2026-03-06 (legacy-bot 제거), 2026-03-07 (T9 Agent 안정화)
- 상태: 대체됨(Superseded)
- Superseded by: ADR-034 (T9 봇 Python 재작성)
- 결정: Notion 큐 폴링 기반 legacy-bot watcher를 폐기하고, 텔레그램 봇 기반 T9 Agent(t9_agent.ps1)로 전환한다. 텔레그램에서 명령 수신 → codex/claude 실행 → 결과를 텔레그램+Notion에 기록하는 구조.
- 이유: legacy-bot watcher는 Notion API 폴링 지연, 인코딩 문제, PowerShell 스코프 버그 등 안정성 문제가 누적됨. 텔레그램은 모바일에서 즉시 명령 가능하고, push 기반으로 지연 없음.
- 대안: legacy-bot watcher 버그 수정 후 유지 (근본 구조 문제 해결 불가), Slack 봇 (이미 텔레그램 사용 중), Discord 봇 (불필요한 복잡성)
- 결과: Task Scheduler에서 legacy-bot 태스크 제거, queue 폴더 아카이브, t9_agent.ps1이 유일한 외부 인터페이스. 엔진 런타임 스위칭("클코로 바꿔"/"코덱스로 바꿔") 지원.
- 출처: 20260306_CX_008_(2-legacy-bot)_212219_legacy-bot제거T9AgentNotion연동.txt, 20260306_CX_011_(2-legacy-bot)_215754_T9Agent엔진스위칭추가.txt, 20260306_CX_013_(2-legacy-bot)_222253_legacy-bot현황정리.txt

## Simondon Mapping
기술적 개체의 구체화(concretization): 분리된 기능(폴링, 실행, 기록)이 단일 에이전트로 통합되어 다기능적 시너지 달성.
