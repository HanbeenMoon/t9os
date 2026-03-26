# T9 OS 기술 부채 목록

> 코드베이스 직접 확인 기반. 2026-03-26 대청소 후 갱신.

---

## 해결됨 (2026-03-23 대수술)

| ID | 항목 | 해결 방법 |
|----|------|-----------|
| TD-001 | t9_bot systemd 미연결 | systemd user service 등록+활성화 완료 |
| TD-002 | deadline_notify cron 미연결 | crontab `0 8 * * *` 등록 완료 |
| TD-003 | 마감일 파일 경로 불안정 (4개 fallback) | 정식경로 1개 + 레거시 1개로 축소 |
| TD-010 | bare except 남용 | 8개소 `except Exception as e:` + 로깅 변환 |
| TD-012 | FTS5 인덱스 재구축 로직 없음 | `rebuild-fts` 명령 추가 |
| TD-015 | calendar_sync 수동 실행 | crontab 3회/일 (07:30, 12:00, 19:00) |
| TD-NEW1 | DB 오염 방지 (filepath 타입 검증) | `_upsert`에 filepath str 검증 추가. `safe_change.sh` 인라인 Python도 config.py 경유로 수정 (2026-03-26) |
| TD-NEW1b | safe_change.sh DB 직접 하드코딩 | `safe_change.sh:43` 인라인 Python → `from lib.config import DB_PATH` 경유로 수정 (2026-03-26) |
| TD-009 | 오버나이트 시스템 미구현 | `pipes/overnight.py` + cron 04:00 등록. `cmd_orphans(fix=None)` 시그니처 불일치 버그 수정 (2026-03-26) |
| TD-009b | overnight.py cmd_orphans TypeError | `commands_ext.cmd_orphans(get_db)` 시그니처에 `fix=None` 파라미터 추가 — overnight.py `fix=False` 호출 호환 (2026-03-26) |
| TD-011 | WSL-NTFS 이중파일 감지 | `cmd_transition` copy+delete 후 잔존 감지+경고 |

---

## 심각도: HIGH (가동에 영향)

_(현재 HIGH 항목 없음)_

---

## 심각도: MEDIUM (기능 제한)

### TD-004: Pipeline Composer 미구현
- **위치**: BIBLE.md 섹션 15 핵심 갭 #1
- **현상**: "파이프라인을 만드는 파이프라인"이 미구현. 새 파이프라인은 수동 코드 작성.
- **제안**: compose 명령 확장 또는 별도 Composer 모듈 설계.

### TD-005: Resource 추적 시스템 미구현
- **위치**: BIBLE.md 섹션 3.4 (5축 중 자원축)
- **현상**: 시간, 토큰, 돈 추적이 안 된다.
- **제안**: 세션별 토큰 사용 로깅 + 시간 추적 최소 구현.

### TD-006: 심리학 7모듈 대부분 미구현
- **위치**: BIBLE.md 섹션 9
- **현상**: reflect만 부분 구현. 나머지 6개 미구현.
- **제안**: Phase 1 구현 대상 선정이 필요.

### TD-007: 자동 split/merge 판단 미구현
- **위치**: BIBLE.md Layer B 설명
- **현상**: cc가 "이건 쪼개야 한다" 판단을 하지 못한다.
- **제안**: 패턴 기반 자동 제안 (확정은 설계자 승인).

### TD-008: 오케스트레이터 (cc/cx/gm 자동 선택) 미구현
- **위치**: BIBLE.md 섹션 10
- **현상**: 어떤 에이전트가 적합한지 수동 판단.
- **제안**: 작업 유형별 자동 라우팅 규칙 구현.

---

## 심각도: LOW (개선 사항)

### TD-013: Concretization 수준 측정 미구현
- **위치**: `constitution/L3_amendment.md`
- **현상**: 구체화 수준 4단계 자동 측정이 없다.
- **제안**: 도구 간 통합 지표 정량화.

### TD-014: Transduction 경로 추적 부실
- **위치**: `t9_seed.py` relates 테이블
- **현상**: 전도적 학습 경로를 체계적으로 추적하지 못한다.
- **제안**: relate 시 전도 유형 분류 + 시각화.

---

## 아키텍처 부채

### TD-A1: BIBLE.md와 실제 구현 간 GAP 관리
- ADR 시스템이 부분 대체. 주기적 갭 점검 필요.

### TD-A2: 단일 DB 파일의 Syncthing 동기화 위험
- `.t9.db`가 WAL 모드지만, 두 PC 동시 수정 시 충돌 가능.
- **제안**: DB 접근을 한 PC로 제한 or conflict 감지 도구.

### TD-A3: 파이프라인 테스트 부재 — 부분 해소
- smoke test 47항목 가동 중 (ALL CLEAR). integrity check 6항목.
- 개별 파이프라인 단위 테스트는 아직 없음. overnight.py가 일부 대체.

