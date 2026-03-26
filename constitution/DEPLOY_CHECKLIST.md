# T9 OS 배포 완결 체크리스트
# ADR-058: 구현만 하지 마라 — 배포+가동확인까지 완료

> "코드 작성 = 30%. 테스트+배포+가동확인 = 나머지 70%."

---

## 1. 코드 변경 시 (모든 변경)

- [ ] `safe_change.sh snapshot` 실행됨 (자동: post-tool-use 훅)
- [ ] smoke test 37/37 PASS
- [ ] verify_claims 10/10 VERIFIED (CONSTITUTION_CHANGE 시)

## 2. 새 파이프라인 추가 시

- [ ] SRBB 확인 (Orient 안돈이 자동 트리거)
- [ ] `lib/registry.py`에 등록
- [ ] `CLAUDE.md` 파이프라인 레지스트리 테이블 갱신
- [ ] cron 필요 시 `cron_runner.sh`에 추가 + crontab 등록
- [ ] smoke test에 파일 존재 체크 추가

## 3. 헌법/핵심문서 변경 시

- [ ] Orient 안돈 확인 (L1/L2는 block, 재시도 필요)
- [ ] 3곳 동시 갱신: L1/L2 + CLAUDE.md + memory
- [ ] 정량 주장 검증 (`verify_claims.py`)
- [ ] 한빈 원문 인용 형식 준수 (`> ` 블록인용)

## 4. 배포 (Vercel/systemd/cron)

- [ ] 로컬에서 가동 확인 (1회 실행 + exit code 0)
- [ ] 배포 실행
- [ ] 배포 후 실제 서비스 응답 확인
- [ ] healthcheck 정상 확인
- [ ] TG 알림 정상 확인 (해당 시)

## 5. 세션 종료 시

- [ ] `safe_change.sh verify` (자동: session-end 훅)
- [ ] 주요 작업 `t9_seed.py capture`로 등록
- [ ] ADR 필요 시 작성 (또는 `adr_auto.py` 자동 생성)

---

## 자동화 현황

| 항목 | 자동화 | 수동 |
|------|--------|------|
| 스냅샷 | post-tool-use (첫 수정 시) | `safe_change.sh snapshot` |
| smoke test | session-start (FAIL시 경고) | `python3 tests/smoke_test.py` |
| verify | session-end | `safe_change.sh verify` |
| claims | 수동 | `python3 tests/verify_claims.py` |
| Orient 안돈 | PreToolUse 훅 | - |
| 레지스트리 갱신 | 수동 | `lib/registry.py` 편집 |
| ADR | session-end (`adr_auto.py`) | 직접 작성 |
