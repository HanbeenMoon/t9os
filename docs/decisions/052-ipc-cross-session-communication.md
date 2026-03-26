# ADR-052: IPC 세션 간 통신 — T9OS/lib/ipc.py

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 동시 실행 중인 cc 세션 간 통신을 T9OS/lib/ipc.py로 구현한다. 한 세션이 전개체를 field/inbox/에 저장하면 IPC 메시지로 다른 세션에 알린다. 각 세션의 대화 내용은 독립적이나, 파일시스템을 통한 비동기 통신이 가능하다.
- 이유: 멀티 세션 동시 운영(research-project + project-alpha + T9OS 등) 시 한 세션의 발견이 다른 세션에 전파되어야 함. 세션 간 직접 메모리 공유는 불가하므로 파일 기반 IPC가 유일한 방법.
- 대안: 세션 간 통신 없음 (사일로), Redis/RabbitMQ (과도한 인프라), 소켓 통신 (복잡)
- 결과: session-end.sh에서 IPC 메시지 전송, 다른 세션은 reindex 시 인식
- 출처: 20260317_bdedf066.md (세션 대화), T9OS/lib/ipc.py

## Simondon Mapping
전도적 전파(transduction)의 세션 간 구현: 한 세션의 구조가 IPC를 통해 인접 세션으로 전파되어 시스템 전체의 개체화가 동기화됨.
