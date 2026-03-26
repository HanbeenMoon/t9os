---
phase: stabilized
transitioned_at: 2026-03-26 11:35
---

# ADR-075: 구체화 시스템 (Concrétisation)

- 날짜: 2026-03-26
- 상태: Active
- 결정: 시몽동 구체화 원리 기반 코드 수렴 시스템 도입 (rm 금지, sediment 보존)
- 이유: AI 세션 반복 개발 시 부산물 누적 + Intent debt 방지

## 맥락

AI 세션이 코드를 반복 발전시킬 때 이전 버전의 부산물(중복 함수, 이중 저장, 병렬 진화한 모듈)이 정리되지 않는 구조적 문제 발생.
Lehman Law II(복잡도 자동 증가) + Intent debt(왜 이 코드가 있는지 모름) + GitClear 데이터(refactoring 25%→10%)로 실증.

## 결정

시몽동의 구체화(concrétisation) 원리를 적용한 코드 수렴 시스템 도입.

### 3원칙

1. **rm 금지, sediment으로.** 코드 삭제 대신 `T9OS/data/sediment/`에 Intent 기록과 함께 보존. 검색 가능, 재활성화 가능.
2. **구체화 = 수렴.** 중복 기능을 "삭제+유지"가 아니라 하나의 수렴점으로 통합. 시너지적 수렴.
3. **Intent 외부화.** 왜 이 코드가 있는지/왜 침전되었는지 ADR과 sediment 프론트매터로 기록.

### 첫 적용 결과 (2026-03-26)

ipc.py + session_lock.py 병렬 진화 7개 중복 → 5개 수렴 + 2개 침전. rm 0줄.

| 수렴점 | 역할 |
|--------|------|
| `lib/ipc.py` | 세션 관리 + heartbeat + WORKING.md 동기화 단일 소스 |
| `config/projects.json` | 프로젝트 패턴 단일 소스 |
| `lib/ipc._db()` | DB 접근 단일 함수 |

## 근거

- 시몽동: 잔여(résidu préindividuel)는 쓰레기가 아니라 "되살의 비축(réserve de devenir)"
- 시몽동: 진공관 에보나이트 받침대 — 기능적 부분이 커지면서 이전 흔적이 자연스럽게 흡수
- Storey 2026: Intent debt 없으면 AI도 안전한 삭제 불가
- Kent Beck "Tidy First": 구조 변경과 기능 변경 분리

## 결과

- 기존 기능 전부 정상 (smoke 45 PASS)
- 침전 파일 2개 생성 (sediment/)
- session_lock.py: 프로젝트 claim 전문가로 역할 축소
