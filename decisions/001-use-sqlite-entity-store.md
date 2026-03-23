# ADR-001: SQLite를 엔티티 저장소로 선택

- 날짜: 2026-03-15
- 상태: 채택됨
- 결정: 모든 엔티티(전개체, 작업, 산출물)의 상태와 메타데이터를 SQLite 단일 DB(`.t9.db`)에 저장한다. FTS5 가상 테이블로 전문 검색을 지원한다.
- 이유:
  - Notion API 의존에서 벗어나기 위해 로컬 우선 저장소가 필요했다. Notion API는 삽질 무한루프(L2U 버그 지옥)의 원인이었다.
  - cc/cx/gm 모두 SQLite를 네이티브로 접근 가능하다 (Python stdlib `sqlite3`).
  - WAL 모드(`PRAGMA journal_mode=WAL`)로 다중 세션 동시 읽기를 지원한다.
  - FTS5로 grep 수준의 검색을 DB 레벨에서 제공하여, 별도 인덱스 시스템 Build를 방지한다.
  - 파일 하나(`.t9.db`)로 Syncthing 동기화가 단순하다.
- 대안:
  - **Notion DB 유지**: API 불안정, 인코딩 깨짐, 2000자 제한, 외부 의존성 — 폐기.
  - **JSON 파일**: 동시 쓰기 충돌, 검색 성능 열악 — 불채택.
  - **PostgreSQL/MySQL**: 서버 관리 오버헤드, 대학생 환경에서 과잉 — 불채택.
  - **파일시스템 + grep만**: 메타데이터 관리 불가, 상태 전이 추적 불가 — 불채택.
- 결과:
  - `t9_seed.py`가 모든 DB 접근의 단일 진입점 역할을 한다.
  - `entities` 테이블(id, filepath, filename, phase, metadata JSON, body_preview, file_hash 등)이 핵심 스키마.
  - `transitions` 테이블로 상태 전이 이력을 완전히 추적한다.
  - `relates` 테이블로 엔티티 간 전도적 관계(transduction)를 기록한다.
  - `_migrate_db()`로 스키마 마이그레이션을 안전하게 처리한다 (ALTER TABLE만, DROP TABLE 절대 금지).
  - 레거시 데이터는 별도 `.t9_legacy.db`로 분리하여 오염을 방지한다.

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 연합된 환경(associated milieu) — SQLite가 모든 엔티티의 공유 환경(milieu)으로서 개체화 과정을 매개한다.
