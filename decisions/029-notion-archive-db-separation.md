# ADR-029: Notion 실행큐 DB와 결과 아카이브 DB 분리

- 날짜: 2026-03-06
- 상태: 대체됨(Superseded)
- Superseded by: ADR-056 (Notion→로컬 이관으로 Notion 운영 자체가 종료)
- 결정: Notion의 L2U 작업큐 DB(faed81d1)와 결과 아카이브를 분리한다. 새 아카이브 전용 DB(31be6a3c-9e5a-8163)를 생성하고, 에이전트 실행 결과는 아카이브 DB에만 기록한다.
- 이유: 실행 큐와 결과 아카이브가 같은 DB에 혼합되면 폴링 필터가 복잡해지고, 완료 항목이 큐를 오염시켜 성능과 가독성이 저하됨.
- 대안: 큐 DB에서 완료 항목 주기적 삭제 (이력 소실), 별도 워크스페이스 (접근 복잡)
- 결과: _keys/.env.txt에 T9_NOTION_ARCHIVE_DB_ID 추가, notion_archive_result.py 수정, 롤백 스크립트(ROLLBACK.ps1) 생성
- 출처: 20260306_CX_021_(2-L2U)_233940_NotionArchiveDB분리및롤백체계구축.txt

## Simondon Mapping
이접(disparation)의 해소: 실행(큐)과 기록(아카이브)이라는 양립 불가능한 요구가 DB 분리라는 새 차원에서 구조적으로 해소됨.
