---
created: 2026-03-16
phase: stabilized
author: cc (Claude Code)
purpose: T9 OS UX 설계 원칙 + 구체적 개선안
---

# T9 OS UX Principles
## "도구를 의식하는 순간, 그 도구는 실패한 것이다"

---

## Part 1. T9 OS UX 5원칙

### Principle 1: Zero Decision (선택지 제거)

> "사용자에게 선택을 요구하는 로직이 있으면 그건 버그" — T9 BIBLE

**근거:**
Steve Krug의 "Don't Make Me Think" 핵심 — 사용자가 생각해야 하는 모든 순간은 이탈 지점.
PKM 연구에서도 "캡처 시 분류를 요구하면 캡처율이 급락" 확인.
Amber Case의 Calm Technology 7번째 원칙: "적절한 기술의 양은 문제를 해결하는 데 필요한 최소한."

**T9 적용 규칙:**
- capture에 카테고리/태그/프로젝트 지정 불필요. 시스템이 자동 분류.
- 파일 이동, 이름 변경, 폴더 정리 — 모두 시스템 자동.
- 상태 전이(transition)에서 다음 상태 후보가 1개면 자동 진행.
- compose의 Plan A/B/C 중 선택이 어려우면 "가장 빠른 것"을 기본값으로.

**안티패턴 (현재 T9에서 발견):**
- `python3 T9OS/t9_seed.py approve <id> A` — ID를 기억해야 하고, A/B/C를 골라야 한다.
- `python3 T9OS/t9_seed.py transition <id> stabilized "사유"` — 상태 이름을 외워야 한다.

---

### Principle 2: One Breath (한숨에 끝나는 인터랙션)

> "Voice UI에서 3개 이상의 선택지를 나열하면 사용자는 기억하지 못한다" — Amazon VUI Guidelines

**근거:**
Voice-first 인터페이스 연구에 따르면 인간의 단기 기억은 "한숨" 분량만 처리 가능.
CLI에서도 동일: 명령어 하나에 목적 하나. 파이프라인이 아니라 동사 하나.

**T9 적용 규칙:**
- 모든 명령은 **5단어 이내**로 완결. `t9 capture "..."` 이 한계.
- 결과 출력도 **한 화면** 이내. 스크롤 필요하면 실패.
- 텔레그램 봇 응답은 **3문장 이내** 요약 + 필요시 "자세히" 옵션.
- 음성 입력 시 확인 질문 없이 바로 처리. 잘못되면 나중에 수정.

**안티패턴:**
- `python3 T9OS/t9_seed.py transition 42 stabilized "SSK 논문 초안 전달 완료"` — 14단어.
- status 출력이 터미널 전체를 채움 — 핵심 3줄이면 충분.

---

### Principle 3: Peripheral Awareness (주변부 인식)

> "기술은 사용자의 주변부에 있어야 하고, 필요할 때만 중심으로 이동해야 한다" — Amber Case, Calm Technology

**근거:**
Calm Technology의 핵심. 기술은 배경에서 조용히 작동하다가, 정말 중요할 때만 알림.
Nest Thermostat이 대표 사례: 설정 후 잊어버려도 된다.

**T9 적용 규칙:**
- 텔레그램 알림은 **오직 마감 24시간 전**과 **에이전트 실패** 시에만 발송.
- daily 브리프는 아침 한 번만. 사용자가 요청하지 않은 알림은 버그.
- 백그라운드 작업(reindex, watch, consolidate)은 완전 무음. 실패 시에만 알림.
- 대시보드는 "열었을 때" 최신 상태. 실시간 업데이트는 불필요한 주의 분산.

**안티패턴:**
- 봇이 시작/종료 시 메시지 전송 (`T9 Bot 가동` / `T9 Bot 종료`) — 불필요한 알림.
- 작업 완료마다 텔레그램 알림 — 정보 과잉.

---

### Principle 4: Error as Conversation (에러는 대화)

> "모든 에러 메시지는 (1) 무엇이 잘못됐는지, (2) 왜 잘못됐는지, (3) 어떻게 고치는지를 포함해야 한다" — clig.dev

**근거:**
CLI Guidelines (clig.dev)와 Lucas F. Costa의 CLI UX 패턴 연구 공통 결론:
에러를 기술 용어로 출력하면 사용자는 포기한다. 에러는 "다음에 뭘 해야 하는지"를 알려주는 대화.

**T9 적용 규칙:**
- 모든 에러 메시지는 한국어 + 다음 행동 제안 포함.
- 스택 트레이스는 `--verbose` 플래그가 있을 때만. 기본 출력은 1줄 요약.
- 잘못된 명령어 입력 시 가장 비슷한 명령어 제안 (fuzzy match).
- 필수 인자 누락 시 "이렇게 써보세요: ..." 예제 즉시 출력.

**현재 문제 (실제 코드에서 발견):**

```python
# t9_seed.py main() — 현재
else: print(f"  알 수 없는 명령: {c}"); print(USAGE)
```

이것은 USAGE 전체를 덤프해서 사용자를 압도한다.

**개선 후:**

```
알 수 없는 명령: "captuer"
혹시 이것? → t9 capture "내용"

자주 쓰는 명령:
  t9 daily      오늘 브리프
  t9 capture    아이디어 저장
  t9 status     전체 현황
```

---

### Principle 5: Progressive Disclosure (점진적 공개)

> "필요한 정보만 먼저, 나머지는 요청 시" — Nielsen Norman Group

**근거:**
Progressive Disclosure는 인지 부하(cognitive load)를 관리하는 핵심 UX 패턴.
초보 사용자에게 전문가용 옵션을 노출하면 두 그룹 모두 불행해진다.

**T9 적용 규칙:**
- QUICKSTART.md는 명령어 3개만: `t9 daily`, `t9 capture`, `t9 status`.
- 고급 기능(relate, consolidate, reflect)은 별도 문서(ADVANCED.md).
- CLI help 출력도 2단계: 기본 help는 5줄, `--help-all`은 전체.
- 텔레그램 봇 /help는 3개 명령만 안내. "더 알고 싶으면 /help-all"

---

## Part 2. 현재 시스템 구체적 개선안

### 2.1 CLI 명령어 단축

| 현재 (문제) | 개선안 | 근거 |
|---|---|---|
| `python3 T9OS/t9_seed.py capture "..."` | `t9 capture "..."` | shell alias 또는 PATH에 `t9` 스크립트 추가 |
| `t9 transition 42 stabilized "사유"` | `t9 done 42` 또는 `t9 done 42 "사유"` | "done"이 자연어. stabilized는 내부 용어 |
| `t9 approve <id> A` | `t9 go <id>` (A가 기본) | Plan A = "가장 빠른 것" 기본 선택 |
| `t9 compose "..."` + `t9 approve <id> A` | `t9 do "..."` (compose+approve 원스텝) | 2단계를 1단계로. 필요하면 `--plan` 옵션 |

**구현 방법 (Buy 우선):**

```bash
# ~/.bashrc에 추가 — 1줄이면 끝
alias t9='python3 ~/code/HANBEEN/T9OS/t9_seed.py'
```

그리고 t9_seed.py에 단축 명령어 추가:
- `done` = `transition <id> stabilized`
- `go` = `approve <id> A`
- `do` = `compose` + 자동 `approve A`

### 2.2 에러 메시지 개선

**현재:** 파이썬 traceback이 그대로 출력되는 경우 다수.

**개선:** main() 함수를 try/except로 감싸고, 사용자 친화적 메시지 출력.

```
[에러] DB 파일을 찾을 수 없습니다.
원인: T9OS/.t9.db 파일이 없거나 손상됨
해결: t9 reindex  (DB 재생성)
```

### 2.3 출력 포맷 개선

**현재 status 출력:** 상태별 숫자만 나열.

**개선안:**

```
=== T9 현황 (2026-03-16) ===

 지금 하는 일 (4):
   #42 SSK 논문 최종 초안
   #45 ODNAR 예창패 사업계획서
   #47 AT1 본선 준비
   #48 T9 OS UX 개선

 오늘 마감:
   #45 ODNAR 예창패 — D-8

 대기 중: 278개  |  완료: 8개
```

핵심: 숫자 나열 대신 "지금 하는 일"을 자연어로.

### 2.4 파일 자동 이동

**현재:** 녹음 파일을 수동으로 PERSONAL/recordings/에 복사해야 한다.

**개선안 (Buy):**
1. **텔레그램 봇이 이미 음성 파일 자동 다운로드함** (t9_bot.py의 handle_voice). 이미 구현됨.
2. 부족한 부분: PC의 특정 폴더(Downloads)에 떨어지는 파일의 자동 이동.
3. **Buy:** Syncthing가 이미 설치돼 있으므로, 아이폰 Syncthing 앱으로 녹음 폴더 직접 동기화.
4. 또는 watchdog (Python 패키지)로 Downloads 감시 → 확장자별 자동 분류.

### 2.5 "뭘 해야 하는지 모른다" 문제

**현재:** QUICKSTART.md가 12개 명령어를 나열. 처음 보면 압도당한다.

**개선:** 첫 실행 시 인터랙티브 가이드:

```
T9 처음이시네요! 이것만 기억하세요:

  t9 daily      → 오늘 뭐해야 하는지
  t9 capture    → 생각 저장
  t9 status     → 전체 현황

나머지는 나중에. 지금 t9 daily 한번 쳐보세요.
```

---

## Part 3. 텔레그램 봇 UX 개선안

### 3.1 명령어 외우기 제거

**현재 문제:** /status, /daily, /search, /capture, /compose, /ask — 6개 슬래시 명령어.

**개선 원칙:** 자연어 우선, 슬래시 명령어는 파워유저 단축키.

**구현:**

| 사용자 입력 | 봇 행동 | 라우팅 로직 |
|---|---|---|
| "오늘 뭐해" | daily 실행 | 키워드 매칭: 오늘, 할일, 브리프 |
| "SSK 어디까지 됐어?" | search SSK + CC 답변 | CC가 자동 판단 |
| "예창패 마감 언제야" | 마감일 검색 | 키워드: 마감, 언제, 기한 |
| "ODNAR 로고 디자인 해야 함" | capture 자동 실행 | "해야", "할 것", "아이디어" 감지 |
| 음성 메시지 | 전사 + 내용 기반 자동 라우팅 | 이미 구현됨 |
| /status | status (파워유저 단축) | 기존 유지 |

**핵심:** handle() 함수에서 슬래시가 아닌 메시지를 CC에 넘기기 전, 간단한 intent 분류 레이어 추가. Build하지 말 것 — CC가 이미 intent 판단이 가능하므로, CC에 넘기면서 "이 메시지가 T9 명령(status/daily/capture/search)인지 먼저 판단하고, 맞으면 해당 명령 실행 결과를 반환하라"는 시스템 프롬프트 추가.

### 3.2 응답 포맷

**현재:** run_t9() 출력을 그대로 전송. CLI 포맷이 텔레그램에서 보기 어려움.

**개선:**
- 텔레그램 Markdown 파싱 모드 활성화 (`parse_mode=Markdown`).
- 긴 출력은 3줄 요약 + "전체 보기" 인라인 키보드 버튼.
- 상태 이모지 표준화: 진행중, 완료, 마감임박, 에러 (4개만).

### 3.3 Inline Keyboard 활용

**현재:** 텍스트 명령만 지원.

**개선:** compose 결과에 Plan A/B/C 인라인 버튼 → 탭 한 번으로 approve.

```
Plan A: 기존 슬라이드 수정 (2시간)
Plan B: 새로 만들기 (5시간)
Plan C: 템플릿 활용 (1시간)

[A 선택]  [B 선택]  [C 선택]
```

### 3.4 프로액티브 알림

**현재:** 사용자가 물어야만 응답.

**개선 (최소한):**
- 매일 아침 8시: daily 브리프 자동 전송 (cron).
- 마감 24시간 전: 알림 1회.
- 그 외 알림 없음 (Calm Technology 원칙).

---

## Part 4. QUICKSTART.md 개선 제안

### 현재 문제

1. 12개 명령어 나열 — 압도적.
2. `python3 T9OS/t9_seed.py` 전체 경로 — 매번 타이핑 고통.
3. 상태 흐름 다이어그램 — 초보자에게 불필요.
4. FinBot, Dashboard, cc 사용법까지 한 문서에 — 관심사 혼합.

### 개선 구조

```
QUICKSTART.md (초보, 30초 읽기)
  ├── 0. 최초 설정 (alias 추가, 1줄)
  ├── 1. 매일 아침: t9 daily
  ├── 2. 생각 저장: t9 capture "..."
  ├── 3. 현황 확인: t9 status
  └── "이것만 알면 됩니다. 더 알고 싶으면 → HANDBOOK.md"

HANDBOOK.md (중급, 필요할 때 참조)
  ├── 작업 만들기: t9 do "..."
  ├── 완료 처리: t9 done <id>
  ├── 검색: t9 search "..."
  ├── 텔레그램 봇 사용
  └── 수업 녹음 전사

ADVANCED.md (고급, cc/cx 전용)
  ├── relate, consolidate, reflect
  ├── 상태 전이 그래프 (시몽동)
  ├── DB 직접 조작
  └── 파이프라인 구축
```

### QUICKSTART.md 핵심 원칙

- 3분 이내 읽기 완료.
- 명령어는 3개만.
- "왜"가 아니라 "어떻게"만.
- 최초 설정은 복사-붙여넣기 1줄.

---

## Part 5. 참고한 이론과 출처

### 핵심 이론

| 이론 | 핵심 메시지 | T9 적용 |
|---|---|---|
| Don't Make Me Think (Steve Krug) | 생각해야 하면 실패 | Zero Decision 원칙 |
| Calm Technology (Amber Case) | 기술은 배경에서 작동 | Peripheral Awareness |
| Progressive Disclosure (Nielsen) | 정보는 단계적으로 | QUICKSTART 3단계 분리 |
| CLI Guidelines (clig.dev) | 에러는 대화, 출력은 최소 | Error as Conversation |
| Zero UI / Invisible UX | 인터랙션 자체를 제거 | 자동 라우팅, 자동 분류 |
| VUI Design (Amazon) | 한숨 분량만 | One Breath 원칙 |
| PKM Friction 연구 | 캡처 마찰 = 캡처 포기 | 무분류 capture |

### 핵심 수치 (웹 리서치)

- Zero UI 도입 시 일상 작업 완료 시간 **68% 단축**, 만족도 **53% 향상** (Zero UI 연구)
- 사용자의 **71%**가 행동 기반 맥락 적응을 기대 (2026 UX 트렌드)
- 에러 메시지에 해결 방법 포함 시 이탈률 **40% 감소** (CLI UX 패턴 연구)

---

## Part 6. 즉시 실행 가능한 액션 (우선순위)

### P0 (오늘, 5분)

1. `~/.bashrc`에 `alias t9='python3 ~/code/HANBEEN/T9OS/t9_seed.py'` 추가.
2. `source ~/.bashrc` 실행.

### P1 (이번 주, 각 30분)

3. t9_seed.py에 단축 명령어 추가: `done`, `go`, `do`.
4. main()의 에러 출력을 사용자 친화적으로 변경.
5. t9_bot.py에 `parse_mode=Markdown` 추가.

### P2 (다음 주)

6. status 출력 포맷 개선 (자연어 + 마감일 강조).
7. QUICKSTART.md 3단계 분리 (QUICKSTART / HANDBOOK / ADVANCED).
8. 텔레그램 봇 아침 8시 daily 자동 전송 (cron 1줄).

### P3 (여유 있을 때)

9. 텔레그램 Inline Keyboard (compose Plan 선택).
10. 텔레그램 자연어 intent 분류 레이어.
11. Downloads 폴더 watchdog 자동 분류.

---

> "최고의 인터페이스는 인터페이스가 없는 것이다.
> 최고의 도구는 도구를 의식하지 않게 하는 것이다.
> T9 OS의 궁극적 목표는 한빈이 T9를 잊어버리는 것이다."
