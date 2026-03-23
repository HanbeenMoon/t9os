---
phase: stabilized
transitioned_at: 2026-03-19 updated
---

# T9 OS Bible v0.3
# "파이프라인을 만드는 파이프라인" — 개체화하는 메타-운영체제

---

## 0. 이 문서의 목적

T9 OS 구축의 설계 바이블. cc(Claude Code)가 구현 시 항상 참조.
이 문서 자체도 개정 가능 — 3층 헌법의 원리 적용.

---

## 1. 왜 T9 OS를 만드는가 (문제 히스토리)

### 1.1 AS-IS의 구조적 한계 (한빈 직접 발언 기반)

1. **토큰 낭비**: "37만원짜리 맥스 20을 써도 대학생이 토큰이 부족한게 말이되냐?"
   - 웹 UI 매번 컨텍스트 리셋 → 브리핑 재전달에 토큰 소모
   - Max x20(월 2M 토큰)도 부족

2. **메타 작업 과다**: "아카이빙/로그/명세서/브리핑이 실제 작업보다 많음"
   - 웹 Claude가 직접 반성: "한빈이 '이거 해줘'라고 하면 저는 브리핑 문서 뽑고, 아카이브 정리하고, 명세서 만들고. 그게 다 메타 작업이었어요."
   - 일을 하기 위한 일 > 실제 일

3. **산출물 부재**: "시스템은 화려하지만 외부에 내놓은 결과물이 뭐예요?"
   - 7개 프로젝트 동시 10%씩 = 축적이 아니라 에너지 분산
   - 시스템 만드는 게 목적이 되어버린 상태

4. **L2U 버그 지옥**: "L2U부터 개지랄 다 해봤는데 포기"
   - 텔레그램 봇 응답 `[` 문제, 인코딩 깨짐
   - Notion API 의존 → 삽질 무한루프

5. **컨트롤타워 의존 리스크**: "전략 판단 대부분을 Claude한테 위임. 검증 구조 없음."

### 1.2 웹 Claude의 경고

> "Claude Code로 전부 이관도 또 메타 작업이에요. 이관 설계하고, 프롬프트 체계 다시 짜고, CLAUDE.md 업데이트하고, 테스트하고. 그거 하다 보면 또 일주일이에요."

**→ T9 OS 구축 자체가 메타 작업 함정에 빠지면 안 됨. 최소한의 구조로 빠르게 작동시키고 점진적으로 성장시켜야 함.**

### 1.3 한빈의 최종 판단

> "웹은 구조적 한계가 너무 커. 클코로 넘어가면 가능성이 무궁무진해. 수백개의 스킬스.md와 오케스트레이션."

---

## 2. T9 OS의 본질

### 2.1 한줄 정의

**"의도를 입력받아, 그 의도의 잠재적 작업 존재들을 상황적으로 개체화하고, 그 존재들을 다시 합치고 쪼개며 장기 기억으로 환원하는 메타-운영체제."**

### 2.2 핵심 철학 (시몽동 기반)

- 기록은 무덤이 아니라 **장(Field)** — 완성된 정보가 아니라 잠재성의 저장소
- 고정된 파이프라인이 아니라 **"개체화되고, 전개체로 환원되고, 재개체화되는 순환계"**
- 입력은 "할 일"이 아니라 **욕구, 긴장, 가능성**

### 2.3 핵심 원칙

1. **Build vs Buy**: Build는 세상에 없는 것에만. 나머지는 전부 Buy (검색 포함)
2. **Zero-Friction**: "사용자에게 선택을 요구하는 로직이 있으면 그건 버그"
3. **소비 vs 생산 필터**: 에너지가 자산으로 축적되는가?
4. **비트겐슈타인**: "도구의 한계 = 세계의 한계. 막히면 새 도구 탐색"
5. **메타 작업 최소화**: 일을 하기 위한 일 < 실제 일 (항상)
6. **산출물 우선**: 시스템 정교함보다 실제 결과물

---

## 3. 아키텍처

### 3.1 4계층 구조 (전개체 → 개체화 → 실행 → 환원)

```
Layer A. Pre-Individual Field (전개체 저장소) — 구현됨
  - 아직 작업으로 확정되지 않은 것
  - 대화 로그, 생각 메모, 감정, 스크랩, 이미지, 음성, 링크
  - 구현: T9OS/field/inbox/ (274건+), t9_seed.py capture/idea
  - 자동 분류: pipes/t9_auto.py (gm flash 기반) — 구현됨

Layer B. Individuation Engine (개체화 엔진) — 부분 구현
  - 전개체 상태를 읽고 task 후보 추출
  - 역할 생성, 합치기/쪼개기 판단
  - Intent Parser: desire_type, object, urgency, ambiguity, execution_cost
  - 구현: t9_seed.py compose/approve, pipes/intent_parser.py
  - 미구현: 자동 split/merge 판단, Pipeline Composer

Layer C. Temporary Agents / Pipelines (임시 에이전트) — 구현됨
  - 그 순간에만 필요한 역할을 임시 생성
  - cc(컨트롤타워), cx(노동), gm(반복/무료)
  - 구현: pipes/ 14개 파이프라인, .claude/skills/ 14개 스킬

Layer D. Residue / Return (잔여/환원) — 구현됨
  - 완료된 작업의 로그, 실패 이유, 파생 아이디어
  - 다시 전개체 저장소로 반환
  - 구현: t9_seed.py transition/consolidate/reflect, T9OS/memory/
```

### 3.2 12개 상태 모델 — 구현됨

```
preindividual     → 아직 흐림                          — 구현됨 (t9_seed.py)
impulse           → 즉각적 충동/직관                    — 구현됨
tension_detected  → 뭔가 긴장이 감지됨                  — 구현됨
candidate_generated → 가능한 개체 후보 생성              — 구현됨
individuating     → 현재 구체화 중                      — 구현됨
stabilized        → 임시 안정화됨                       — 구현됨
split             → 둘 이상으로 분기됨                   — 구현됨 (수동 전이)
merged            → 다른 것과 합쳐짐                    — 구현됨 (수동 전이)
suspended         → 잠복                               — 구현됨
archived          → 장기기억으로 이동                    — 구현됨
dissolved         → 배경으로 가라앉음 (archived에서는 전이 불가) — 구현됨
reactivated       → 재활성화됨                          — 구현됨
```

### 3.3 3층 헌법 (메타 무한회귀 해결) — 구현됨

```
1층: 실행 규칙 — 지금 당장 돌아가게 하는 규칙    → constitution/L1_execution.md
2층: 해석 규칙 — 언제 상태를 바꿀지             → constitution/L2_interpretation.md
3층: 개정 규칙 — 1,2층을 언제 수정할지           → constitution/L3_amendment.md
감시단 규칙: 코드/문서 작업 후 자동 감시          → constitution/GUARDIANS.md (추가)
```

> "완결된 OS가 아니라, 자기 자신의 규칙을 언제든 수정할 수 있는 가설적 OS"

### 3.4 5축 해석 체계 (직무 대신)

```
1. 의도(Intent): "나 @@ 만들고 싶어"     — 부분 구현 (pipes/intent_parser.py)
2. 상태(State): 탐색/실행/보류           — 구현됨 (12개 상태 모델로 확장)
3. 자원(Resource): 시간, 토큰, 돈 등     — 미구현 (자원 추적 시스템 없음)
4. 제약(Constraint): 마감, 예산, 체력     — 부분 구현 (마감일만 state.md + daily)
5. 산출물(Artifact): 코드, 문서, 설계안   — 구현됨 (T9OS/artifacts/)
```

### 3.5 18개 학문 통합 설계 원리

```
물리(상전이/임계성), 생명(allostasis/autopoiesis),
진화(Quality-Diversity), 심리(SDT/구현의도),
신경(predictive coding), 사이버네틱스(피드백루프),
시스템공학(V-model), HCI(affordance), 경제학(기회비용),
STS(기술의 사회적 구성), 철학(시몽동/개체화),
복잡계(자기조직화), 생태학(niche construction),
언어학(화행이론), 인류학(리미널리티),
정보이론(엔트로피), 제어공학(PID), 교육학(ZPD)
```

---

## 4. 오케스트레이션

### 4.1 역할 분담 — 구현됨

```
cc (Claude Code) = 컨트롤타워 — 구현됨
  - 전략 판단, 오케스트레이션
  - 토큰 아껴야 함 (항상 실행 중)
  - 다른 에이전트 호출/관리
  - claude-octopus v9.2.0 연동 (cx 코드 리뷰)

cx (Codex) = 노동자 — 구현됨
  - GPT Plus 3만원, 토큰 풍부
  - 코드 생성, 문서 작성, 긴 스크립트
  - cc가 시키는 대로 실행

gm (Gemini CLI) = 보조 — 구현됨
  - 무료, OCR, 대량 반복
  - 3 Flash 또는 3.1 Pro만 사용 (2.x 절대 금지)
  - 병렬 처리에 최적
  - gm_batch.py로 감시단 21명 하위직원 batch 실행

t9_agent (텔레그램) = 모바일 접근 — 부분 구현
  - pipes/t9_bot.py 코드 작성됨
  - systemd 미연결, 가동 안 됨
  - 목적: 야외에서 cc 접근
```

### 4.2 병렬 실행 원칙 — 구현됨

- 독립적 작업은 항상 병렬 (승인 후)
- 시스템 리소스 모니터링하며 workers 수 최적화
- 서울PC: 12코어, 15GB RAM, RTX 3060
- API rate limit 고려 (Gemini free: ~10 req/min)
- 세션 충돌 방지: `pipes/session_lock.py` + `t9_seed.py claim/release` — 구현됨 (추가)
- 세션 간 통신: `lib/ipc.py` — 구현됨 (추가)

### 4.3 감시단 (Guardian System) — 구현됨 (추가)

BIBLE v0.1에 없던 신규 시스템. 코드/문서 작업 후 자동 감시.
상세: `T9OS/constitution/GUARDIANS.md`

| 감시단 | 역할 | 하위직원 수 (gm batch) | 상태 |
|--------|------|----------------------|------|
| G1 기술 | 보안, 코드 품질, Build vs Buy | 4명 | 구현됨 |
| G2 철학 | 비전 왜곡 방지 (G2-A 비전 + G2-B 존재론, 2단계) | 4명 | 구현됨 |
| G3 규칙 | L1/L2 위반, 데이터 규칙, 로그 형식 | 2명 | 구현됨 |
| G4 글쓰기 | 대외 산출물 글 품질, 비트겐슈타인 원칙 | 2명 | 구현됨 (추가) |
| G5 경영 | BM, 재무, 시장 검증, G2 견제 | 3명 | 구현됨 (추가) |
| G6 마케팅 | 5초 테스트, 욕구 자극, G2 견제 | 2명 | 구현됨 (추가) |
| G7 디자인 | 철학 시각화, 모션 품격, Stripe/Linear급 | 2명 | 구현됨 (추가) |

- 실행 도구: `python3 T9OS/pipes/gm_batch.py guardian` (cc 토큰 절약, gm 무료)
- 감시단 간 토론(Guardian Debate): G2 vs G5/G6 충돌 시 토론 → 합의 → 한빈 최종판단
- 경량(G1만) / 기본(G1+G2+G3) / 전체(G1~G7, 21명)

---

## 5. 데이터 체계

### 5.1 현재 데이터 자산

```
_legacy/_notion_dump/    ← 노션 전체 (554건, 575KB)
  chats/                ← AI 채팅 (148,853건, 111MB, 월별 83파일)
  digested_final/       ← 3.1Pro+3Flash 교차비교 digest (99개, 642KB)

_legacy/_personal_dump/ ← 카톡+옵시디언 (완료)
  obsidian/MOONDUNE/    ← 원본 1918 md
  kakao/                ← 원본 카톡 16 txt
  merged/               ← 병합본 70개
  digested_final/       ← 다차원 다이제스트 (70/70 완료)
    ├── *_digest.txt         ← 팩트 다이제스트 (인물/일정/재무/프로젝트)
    ├── KakaoTalk_사고지도_THOUGHT_MAP.md  ← 7테마 사고 진화 지도
    └── KakaoTalk_인사이트_RAW_INSIGHTS.md ← 236개 원시 인사이트
```

### 5.2 다차원 다이제스트 체계

원본 데이터에 대해 두 가지 차원의 다이제스트를 유지:

```
차원 1: 팩트 다이제스트 (*_digest.txt)
  - 누가, 언제, 어디서, 얼마 — 이벤트/사실 중심
  - 인물, 일정, 재무, 프로젝트, 추천 정보

차원 2: 인사이트 다이제스트 (*_insights.md, THOUGHT_MAP.md)
  - 왜, 어떻게 생각했는가 — 사고/철학 중심
  - 7테마: 결핍/정체성/관계/메타인지/기술비전/사업철학/실행력
  - 시간에 따른 사고 진화 추적

→ 두 차원 교차 검색 시 원본 데이터의 90%+ 활용 가능
→ 파이프라인: T9OS/pipelines/digest_insights.sh
```

### 5.3 데이터 접근 원칙

```
1. 사고 지도(THOUGHT_MAP) = 한빈의 세계관/철학 파악용
2. 팩트 다이제스트 = 사실관계/이벤트 파악용
3. 인사이트 RAW = 특정 테마 심층 탐색용
4. grep = 원본 위치 찾기
5. 원본 읽기 = 정밀 확인 (해당 부분만)
→ 인덱스 시스템 별도 Build 금지 (grep이 Buy)
```

### 5.4 데이터 무결성 원칙

- 원본은 절대 수정 안 함
- 가공본은 원본의 복제에서 출발
- 파싱 시 전체 키/필드 전수 검사 필수 ("없다" 판단은 확인 후에만)

---

## 6. 구현 전략

### 6.1 핵심 경고: 메타 작업 함정

> 이 T9 OS 구축 자체가 메타 작업이 될 수 있음.
> "시스템을 바꾸면 더 효율적일 거야" → 이관 작업 → 예상보다 오래 → 마감 다가옴 → 결과물 없음
>
> 따라서: 최소한의 구조로 빠르게 작동시키고 점진적 성장.

### 6.2 구현 원칙

1. **최소 기능 먼저**: 완벽한 구조 대신 작동하는 최소 구조
2. **Buy 최대화**: GitHub에서 가져올 수 있는 건 전부 가져옴
3. **점진적 성장**: v0.1로 시작, 사용하면서 개정
4. **산출물 지향**: 시스템 자체가 아니라 시스템이 내는 결과물이 기준

### 6.3 폴더 구조 (실제 구현 — v0.3 갱신)

```
T9OS/                           ← 설계/철학/데이터
├── BIBLE.md                    ← 이 문서
├── QUICKSTART.md               ← 빠른 시작 가이드 (추가)
├── t9_seed.py                  ← 시드 엔진 (761줄, 엔티티 관리) (추가)
├── t9_viz.py                   ← 시각화 유틸 (추가)
├── constitution/               ← 3층 헌법 — 구현됨
│   ├── L1_execution.md
│   ├── L2_interpretation.md
│   ├── L3_amendment.md
│   └── GUARDIANS.md            ← 감시단 G1~G7 규칙 (추가)
├── telos/                      ← 목표 시스템 — 구현됨 (8파일로 확장)
│   ├── MISSION.md              ← 미션
│   ├── GOALS.md                ← 현재 목표
│   ├── PROJECTS.md             ← 프로젝트 현황
│   ├── MODELS.md               ← 사고 모델
│   ├── LEARNED.md              ← 범용 학습
│   ├── LEARNED_SSK.md          ← SSK 학습 (추가)
│   ├── SIMONDON.md             ← 시몽동 원리 (추가)
│   └── UX_PRINCIPLES.md        ← UX 원칙 (추가)
├── field/inbox/                ← 전개체 저장소 (274건+) — 구현됨
├── spaces/                     ← 작업 공간 — 구현됨 (확장)
│   ├── active/
│   ├── suspended/
│   ├── archived/
│   └── sediment/               ← 침전층 (추가)
├── artifacts/                  ← 산출물 — 구현됨
├── memory/                     ← 장기 기억 (memory_ssk.md) — 구현됨
├── pipes/                      ← 실행 파이프라인 14개 (추가 — 6.4절 참조)
├── lib/                        ← 공유 라이브러리 4개 (추가 — 6.5절 참조)
├── deploy/                     ← 배포 스크립트 8개 (추가 — 6.6절 참조)
├── pipelines/                  ← 레거시 파이프라인
│   ├── digest_insights.sh      ← 인사이트 추출 + 사고 지도 생성
│   └── prompts/                ← 파이프라인용 프롬프트 템플릿
├── logs/                       → 심볼릭 링크 → _ai/logs/
└── data/                       → 심볼릭 링크들
    ├── notion_dump/            → _legacy/_notion_dump/
    ├── personal_dump/          → _legacy/_personal_dump/
    ├── conversations/          ← T9 OS 구축 세션 대화 기록 (추가)
    ├── composes/               ← compose 결과 저장 (추가)
    ├── cc_sessions_raw/        ← cc 세션 원본 (추가)
    └── archive_legacy/         ← 레거시 아카이브 (추가)

.claude/                        ← cc 인프라 — 구현됨
├── WORKING.md                  ← 크래시 버퍼 (codex-os에서 Buy) — 구현됨
├── state.md                    ← 열린 루프 추적 — 구현됨
├── routing-policy.md           ← 모델 라우팅 — 구현됨
├── agents/                     ← 서브에이전트 3종 — 구현됨
│   ├── code-reviewer.md
│   ├── data-manager.md
│   └── researcher.md
├── skills/                     ← 스킬 14종 — 구현됨 (6.7절 참조)
└── rules/                      ← 경로별 규칙 — 구현됨
    ├── logging.md
    └── stata.md
```

**폐기된 파일** (v0.1에 있었으나 현재 없음):
- `T9OS/research_raw.md` — 원본 설계 추출 (아카이브 이동 또는 삭제됨)
- `T9OS/github_research.md` — Buy 조사 (아카이브 이동 또는 삭제됨)

### 6.4 파이프라인 레지스트리 (`T9OS/pipes/`) — 추가

| 파일 | 역할 | 호출 방법 | 상태 |
|------|------|-----------|------|
| `gm_batch.py` | 감시단 batch + 대량 리뷰 (50KB, 핵심) | `python3 T9OS/pipes/gm_batch.py guardian -t <파일>` | 구현됨 |
| `t9_auto.py` | 전개체 자동 분류 (gm flash) | `python3 T9OS/pipes/t9_auto.py` | 구현됨 |
| `t9_ceo_brief.py` | CEO 텔레그램 브리프 | session-start.sh 자동 | 구현됨 |
| `t9_bot.py` | 텔레그램 봇 | systemd (미연결) | 부분 구현 |
| `session_lock.py` | 세션 충돌 방지 | t9_seed.py claim/release | 구현됨 |
| `intent_parser.py` | 의도 파서 (5축 해석) | t9_seed.py 통합 | 구현됨 |
| `whisper_pipeline.py` | 음성 전사 (faster-whisper) | `/whisper` 스킬 | 구현됨 |
| `calendar_sync.py` | Google Calendar 동기화 | 수동 | 구현됨 |
| `deadline_notify.py` | 마감일 알림 | cron (미연결) | 부분 구현 |
| `sc41_cron.py` | SC41 과제 자동화 | cron | 구현됨 |
| `sc41_cron_runner.sh` | SC41 cron 실행 래퍼 | sc41_cron.py에서 호출 | 구현됨 |
| `reproducibility_check.py` | 재현성 자동 체크 | `python3 T9OS/pipes/reproducibility_check.py` | 구현됨 |
| `tg_common.py` | 텔레그램 공통 함수 | import 전용 | 구현됨 |
| `__init__.py` | 패키지 초기화 | 자동 | 구현됨 |

### 6.5 공유 라이브러리 (`T9OS/lib/`) — 추가

| 파일 | 역할 | 상태 |
|------|------|------|
| `ipc.py` | 세션 간 통신 (13KB) | 구현됨 |
| `commands.py` | t9_seed 확장 명령어 (15KB) | 구현됨 |
| `export.py` | 데이터 내보내기 유틸 (5KB) | 구현됨 |
| `parsers.py` | 파서 유틸 (3KB) | 구현됨 |

### 6.6 배포 스크립트 (`T9OS/deploy/`) — 추가

| 파일 | 역할 | 상태 |
|------|------|------|
| `SETUP_GUIDE.md` | 셋업 가이드 문서 | 구현됨 |
| `config_bashrc_t9.sh` | bashrc T9 설정 | 구현됨 |
| `copy_to_usb.sh` | USB 복사 | 구현됨 |
| `prepare_usb_package.sh` | USB 패키지 준비 | 구현됨 |
| `setup_target_machine.sh` | 대상 머신 셋업 | 구현됨 |
| `setup_via_syncthing.sh` | Syncthing 셋업 | 구현됨 |
| `step1_install_wsl.ps1` | WSL 설치 (PowerShell) | 구현됨 |
| `step2_setup_wsl.sh` | WSL 설정 | 구현됨 |

### 6.7 스킬 시스템 (`.claude/skills/`) — 추가

| 스킬 | 역할 | 분류 |
|------|------|------|
| `t9-daily` | 일일 브리프 + 마감일 | T9 운영 |
| `t9-weekly` | 주간 회고 + 반성 | T9 운영 |
| `t9-braindump` | 브레인덤프 → 전개체 분류 | T9 운영 |
| `t9-consolidate` | 아카이브 → memory 통합 | T9 운영 |
| `t9-research` | 리서치 파이프라인 | T9 운영 |
| `t9-visualize` | 데이터 시각화 | T9 운영 |
| `whisper` | 음성 전사 (faster-whisper) | 도구 |
| `ocr` | OCR (이미지 → 텍스트) | 도구 |
| `pdf-extract` | PDF 추출 | 도구 |
| `verify` | verify_paper.py 실행 | 도구 |
| `answer` | 질문 답변 | 학습 |
| `solve` | 문제 풀이 | 학습 |
| `battle-start` | 배틀 시작 | 학습 |
| `battle-log` | 배틀 로그 | 학습 |

---

## 7. 프로젝트 포트폴리오 현황 (2026-03-19 갱신)

| 프로젝트 | Tier | 상태 | 설명 |
|---------|------|------|------|
| T9 | 1 | OS 가동 중 | 이 아키텍처 자체. 헌법+시드엔진+파이프라인 구현 완료 |
| ODNAR | 1 | MVP 있음 | unknown unknowns 자동 구조 발견 플랫폼 |
| SSK | 1 | 논문 v23 | 특허자산 → 산업별 임금 차별적 효과 (Stata) |
| SC41 | 2 | 자동화 안정 | 4학년1학기 최소 에너지 운영 |
| PM3 | 2 | 설계 완료 | PMILL — 학술연구 자동화 파이프라인 |
| L2U | 2 | 동결 | 재설계 필요. T9 OS에서 재정의 |
| T9D | 2 | Vercel 배포 | T9 Dashboard |
| AT1 | 시즌 | 본선 대비 | AI TOP 100 CAMPUS 대회 |
| T-SUM | 3 | 홀드 | Tech Skill Up Mentoring |
| AI학회 | 3 | 대기 | AI 학회 활동 |
| 한민혁 | 2 | 진행 중 | 스테이블코인 레퍼런스트리 |

---

## 8. 핵심 사람

| 이름 | 관계 | 맥락 |
|------|------|------|
| 김동우 | SSK 공동연구자 | MDIS 데이터, 현실적 피드백 |
| 김일두 | SSK 멘토(석사) | 논문 검토, 방법론 자문 |
| 이석준 | ODNAR CTO 후보 | 기술 검토, 팩트폭력 피드백 |
| 박성호 | T-SUM 멘토 | AI 파인튜닝 지도 |
| 워니(혜원) | 연인 | 심리적 지지, 현실적 조언 |

---

## 9. 심리학 7모듈 (T9 OS 고유 설계) — 미구현

기존 생산성 도구는 "할 일 목록"만 있고 "할 수 있는 상태"는 무시.
T9는 task 생성 전에 심리적 상태를 고려.

```
1. 동기 모듈 (SDT) — 자율성/유능감/관계성 3욕구 충족도 체크     — 미구현
2. 감정번역 모듈 — 감정 = 상태신호, 제거 대상 아님              — 미구현
   "고 또한 삶이다. 모든 감정을 온전히 느껴야만 한다" (한빈 원칙)
3. 행동전환 모듈 (구현의도) — if-then 플래닝, 환경 트리거        — 미구현
4. 심리적 유연성 모듈 — 고정 정체성 대신 상황별 역할 모드        — 미구현
5. Flow 교정 모듈 — 난이도/의미/명료성 3가지 균형               — 미구현
6. Allostatic 예측 모듈 — 미래 피로/과열/회복 예측              — 미구현
7. 반성 모듈 — 패턴-조건 관계 학습 (진단체계 환원 금지)         — 부분 구현 (t9_seed.py reflect)
```

---

## 10. L2U 확장설계 P1~P7

L2U는 T9 OS에서 재정의 필요. 원래 목적(웹UI↔CLI 소통)은 폐기.
새 목적: 모바일/야외에서 cc 접근.

```
P1: 긴 명세서 → Notion 본문 (2000자 제한 우회)                — 폐기 (Notion 의존 제거)
P2: 완료 알림 자동화                                          — 부분 구현 (pipes/deadline_notify.py)
P3: 식별자 통합 (page_id = 자동 식별자)                        — 폐기 (SQLite entity_id로 대체)
P4: 프로젝트간 큐 소통 ([T9→ODNAR] 태그)                      — 부분 구현 (lib/ipc.py, 세션 간 통신)
P5: 작업환경 점검 상시등록                                     — 미구현
P6: 작업 체이닝 (A 완료 → 자동 B 시작)                        — 미구현 (Pipeline Composer 필요)
P7: 엔진 자동전환 (cc/cx/gm 중 적합한 것 자동 선택)            — 부분 구현 (routing-policy.md 수동 가이드)
```

→ P6, P7은 T9 OS Pipeline Composer와 통합 가능

---

## 11. AX 재해석 프레임워크

SC41 수업 개념은 DX(디지털 트랜스포메이션) 시대 기준.
직접 적용 금지 → AX(AI 트랜스포메이션)로 번역 후 적용.

- 병렬적 폭포수 = cc+cx 동시 실행
- 진화적 모형 = 각 프로젝트별 점진적 발전
- 1주 스프린트 = 매주 조별과제 사이클

---

## 12. ODNAR와 T9 OS의 관계

- T9 OS = 한빈의 생산성 운영체제 (도구)
- ODNAR = 개인 온톨로지 발견 엔진 (제품)
- T9 OS의 전개체 저장소 ↔ ODNAR의 메모 입력 시스템은 동일 구조
- T9 OS에서 축적된 데이터가 ODNAR의 재료
- known unknowns(Claude Projects) vs unknown unknowns(ODNAR) 프레이밍

---

## 13. 파운더 서사 (사업계획서용)

- "빚덩이 대학생이 37만원 결제" — 레버리지 최대 시점에 투자
- "일체유심조" — 합리화일지언정 내가 오롯이 믿으면 내 세상
- "과거 몰입(여자) = 소비, 현재 AI = 생산 — 처음으로 복리가 도는 대상"
- 워니: "정량적인 건 최대한 쏟아부어야 설령 실패해도 만족"

---

## 14. Buy 로드맵 (GitHub 리서치 기반) — 이행 현황 갱신

### 즉시 (설정만)
- [x] `.claude/WORKING.md` — 크래시 버퍼 (codex-os) — 구현됨
- [x] `.claude/state.md` — 열린 루프 추적 (codex-os) — 구현됨
- [x] `.claude/routing-policy.md` — 모델 라우팅 (codex-os) — 구현됨
- [x] `.claude/rules/` — 경로별 규칙 (Claude Code 공식) — 구현됨

### 이번 주 (설치+설정)
- [x] 서브에이전트 + 영구 메모리 (`.claude/agents/`) — 구현됨 (3종)
- [x] 커스텀 스킬 (`.claude/skills/`) — 구현됨 (14종)
- [ ] CAO 설치 (`uv tool install cli-agent-orchestrator`) — 미구현
- [ ] Agent Teams 활성화 (settings.json) — 미구현
- [x] COG 스킬 포팅 (braindump, auto-research, weekly-checkin) — 구현됨 (부분 포팅)

### 이번 달 (Build on Buy)
- [ ] 오버나이트 시스템 (cron + session-brief.md) — 미구현
- [x] TELOS 목표 시스템 (PAI + 시몽동) — 구현됨 (telos/ 8파일)
- [x] VoxWatcher (파일 변경 감지) — 구현됨 (`t9_seed.py watch`)

### Buy 소스
- PAI: TELOS 목표 시스템, 3-tier 메모리, Hook
- COG: 17개 스킬, 자기진화 사이클, 멀티에이전트 호환
- codex-os: WORKING.md 크래시 버퍼, VoxWatcher, 오버나이트
- CAO: tmux 멀티에이전트, 3가지 오케스트레이션 패턴
- Claude Code 공식: Agent Teams, Subagents, Skills, Memory

---

## 15. 핵심 갭 (미구현 우선순위)

| 순위 | 항목 | 설명 | 상태 |
|------|------|------|------|
| 1 | Pipeline Composer | "파이프라인을 만드는 파이프라인" (BIBLE 핵심 컨셉) | 미구현 |
| 2 | 심리학 7모듈 | 9절 전체. reflect만 부분 구현 | 미구현 |
| 3 | Resource 추적 | 5축 중 자원축 (시간/토큰/돈 추적) | 미구현 |
| 4 | Workflow Memory | 파이프라인 실행 이력 기억 | 미구현 |
| 5 | 오케스트레이터 P7 | cc/cx/gm 자동 선택 | 미구현 |
| 6 | 오버나이트 시스템 | cron + session-brief.md | 미구현 |
| 7 | t9_bot systemd | 텔레그램 봇 상시 가동 | 미구현 |
| 8 | deadline_notify cron | 마감일 알림 자동화 | 미구현 |

---

## 16. TODO (이 바이블 기준)

- [x] GitHub 리서치 → 섹션 14 Buy 로드맵 + github_research.md
- [x] Notion 본문보강 원본 읽기 (심리학 7모듈, L2U P1-P7 등)
- [x] 한빈 Roast 세션 원본 읽기 (메타 작업 함정 경고)
- [x] 폴더 구조 확정 및 생성 — 구현됨 (6.3절)
- [x] 3층 헌법 v0.1 작성 — 구현됨 (constitution/)
- [x] 기존 CLAUDE.md → T9 OS 확장 — 구현됨
- [x] 데이터 재배치 (덤프 → T9OS 구조) — 구현됨 (심볼릭 링크)
- [x] 스킬/훅 시스템 설계 — 구현됨 (14종 스킬 + session hooks)
- [ ] 원본 deep read 에이전트 결과 반영
- [ ] t9_agent 재설계 명세 (t9_bot.py 코드는 있으나 가동 안 됨)
- [ ] 심리학 7모듈 중 Phase 1 구현 대상 선정
- [ ] L2U P5/P6/P7 → T9 OS 통합 재설계
- [ ] Pipeline Composer 설계 + 구현
- [ ] Resource 추적 시스템 설계

---

## 17. 개정 이력

| 날짜 | 버전 | 변경 | 이유 |
|------|------|------|------|
| 2026-03-15 | v0.1 | 초기 생성 | Notion+웹 대화 8개+원본 3개+digest 99개 기반 설계 |
| 2026-03-19 | v0.3 | 실제 구현 상태 전면 반영 | BIBLE_IMPLEMENTATION_GAP.md 기반 갱신. pipes/ 14개, lib/ 4개, deploy/ 8개, skills 14종, Guardian G4~G7, Buy 로드맵 이행 현황, 핵심 갭 정리. 폐기 항목(research_raw.md, github_research.md, L2U P1/P3) 표시 |

---

*이 문서는 개정 가능한 가설적 바이블입니다. v0.3 — 2026-03-19*
*실제 파일시스템 + GAP 분석 기반 갱신. 변조의 대상이지 영구 형태가 아니다.*
