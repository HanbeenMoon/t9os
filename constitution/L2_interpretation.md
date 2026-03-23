---
phase: stabilized
transitioned_at: 2026-03-16 04:59
---

# L2: 해석 규칙 — 상태 전이 판단 기준
# v0.2 — 시몽동 전면 개정 (2026-03-16)

## 이접 기반 상태 전이 (Disparation)

상태 전이는 단순 "조건 충족"이 아니라, **양립 불가능한 차원들 사이의 긴장**이 해소될 때 발생한다.
각 전이에서 이접의 세 요소를 식별:

| 전이 | dimension_a | dimension_b | resolution_dimension |
|------|------------|------------|---------------------|
| preindividual → tension_detected | 현 상태(안정) | 욕구/불편(변화) | 긴장의 명명 |
| tension → candidate | 추상적 긴장 | 구체적 행동 가능성 | 행동 후보 생성 |
| candidate → individuating | 잠재적 작업 | 자원/시간 제약 | 설계자 승인 또는 마감 압력 |
| individuating → stabilized | 실행 중 불확실성 | 산출물 기대 | 산출물 1개+ 생성 |
| stabilized → archived | 작업 관성(더 할 수 있음) | 완료 기준(충분함) | 회고 기록 완료 |

### preindividual → tension_detected
- 사용자가 불편/아이디어/욕구 표현
- 반복되는 패턴 감지 (같은 주제 3회 이상 언급)
- **이접 식별 필수**: "무엇과 무엇이 양립 불가능한가?" 명시

### tension_detected → candidate_generated
- 구체적 행동 가능성 식별
- "이거 해볼까?" 수준의 명확성 도달

### candidate_generated → individuating
- 사용자 승인 또는 명시적 지시
- 마감 압력으로 자동 승격

### individuating → stabilized
- 산출물 1개 이상 생성 / 다음 액션 명확

### split/merged 후 재개체화 경로
- **split**: 원본 → dissolved, 하위 엔티티들 → candidate_generated에서 재출발
- **merged**: 원본들 → dissolved, 통합 엔티티 → candidate_generated에서 재출발
- 재개체화 시 원본의 메타데이터와 학습을 계승

### suspended / dissolved / archived / reactivated
- suspended: 외부 블로커 또는 우선순위 하락
- dissolved: 사용자 명시적 폐기 또는 30일+ suspended
- archived: stabilized 후 산출물/회고 완료
- reactivated: 관련 키워드 재등장 또는 사용자 재활성화

## 5축 해석
모든 입력을 이 5축으로 해석:
1. **의도**(Intent): create / explore / solve / earn / express / become
2. **상태**(State): 탐색 / 실행 / 보류
3. **자원**(Resource): 시간, 토큰, 돈, 파일, 사람, 도구, 지식
4. **제약**(Constraint): 마감, 예산, 체력, 실력, 접근권한
5. **산출물**(Artifact): 코드, 문서, 설계안, 데이터

## 전개체의 정의 (통일)
BIBLE/L1/코드 공통 정의:
> **전개체(preindividual)** = 아직 개체화되지 않은 잠재성의 총체.
> 감정, 욕구, 메모, 스크랩, 대화 파편 등. 그 자체로는 작업이 아니지만
> 긴장(disparation)이 감지되면 개체화의 재료가 된다.
> 코드에서: `phase='preindividual'`, 폴더: `field/inbox/`, `field/impulses/`

## 전개체 정리 프로토콜 (Triage)

전개체가 50건 이상 쌓이면 triage를 실행한다. 매 세션에서 하는 게 아니라, 축적됐을 때 한번에.

### 시몽동 원칙
- 전개체는 **분류되기를 거부한다.** 섣부른 분류는 잠재성을 죽인다.
- triage의 목적은 분류가 아니라 **긴장 감지(disparation detection)**.
- "이건 뭐지?"가 아니라 "이건 어디서 긴장을 일으키는가?"를 묻는다.

### 3단계 프로토콜

**1단계: 스캔 (30초/건)**
각 전개체를 훑으며 3가지만 판단:
- **마감이 있는가?** → YES면 즉시 `tension_detected` + urgency 태깅
- **기존 엔티티와 관련 있는가?** → YES면 `relate` 연결만 하고 전개체 유지
- **둘 다 아닌가?** → 그대로 둠 (전개체는 전개체로 남아도 된다)

**2단계: 긴장 감지 (패턴 기반)**
스캔 완료 후, 전개체 전체를 놓고 패턴을 찾는다:
- 같은 키워드/주제가 3건 이상 → `tension_detected`로 전이 + 왜 반복되는지 메모
- 같은 프로젝트 관련 5건 이상 → `merged` 고려 (하나의 candidate로 통합)
- 30일 이상 된 전개체 → `dissolved` 고려 (단, 설계자 확인 후)

**3단계: 산출물 연결**
tension이 감지된 엔티티에 대해:
- 이미 산출물이 있는가? (artifacts/ 에서 검색) → 있으면 `relate`
- candidate로 올릴 만한가? → 설계자 승인 or 마감 압력이 있을 때만

### 하지 않는 것
- 프로젝트별로 폴더 분류 ❌ (시몽동 위반 — 전개체는 여러 프로젝트에 걸칠 수 있다)
- 모든 전개체를 반드시 개체화 ❌ (전개체로 남는 것이 정상)
- 자동 dissolved ❌ (30일 규칙은 설계자 확인 후에만)
- 과도한 메타데이터 추가 ❌ (태그 3개 이상 붙이면 메타 작업)

### 실행 주기
- **자동**: seed reindex 시 마감일 전개체는 자동으로 tension_detected
- **수동**: cc가 `t9_seed.py consolidate` 실행 시 (또는 설계자이 "정리해" 지시 시)
- **주간**: `/t9-weekly` 스킬에서 전개체 현황 리포트 포함

## 감시단 해석 기준

### 실행 도구
- **gm_batch.py guardian**: `python3 T9OS/pipes/gm_batch.py guardian -t <파일> --mode <light|default|full>`
- cc는 감시단장 역할만. gm batch 하위직원이 실제 검사 (무료, 병렬).
- 결과: `_ai/logs/gm/{timestamp}_guardian_brief.md` (CEO 브리프)

### 모드 판단 기준

| 변경 유형 | 모드 | 감시단 | CLI |
|----------|------|--------|-----|
| 1-10줄 버그 픽스 | light | G1 | `--mode light` |
| 기능 추가 (>100줄) | default | G1+G2+G3 | (기본) |
| 아키텍처/비전 문서 | full | G1~G7 | `--mode full` |
| 논문/자소서 | 별도 | G2+G4 | `-g G2 G4` |
| 사업계획서 | 별도 | G4+G5+G6 | `-g G4 G5 G6` |
| 디자인/UI | 별도 | G1+G7 | `-g G1 G7` |
| 로그/.claude 메타 | 생략 | - | - |

### 판정 해석
- "비전 왜곡": ANCHOR 금지어 1회 = WARNING, 필수어 전부 누락 = CATASTROPHIC.
- 경량 → 중량 에스컬레이션: G1에서 P0 발견 시 자동 전환.
- 새 프로젝트 생성 시: ANCHOR 문서 작성 여부 확인. 없으면 G2 생략.

### 재현성 규칙 (위반 불가)
- **새 파이프라인/도구 생성 시**: CLAUDE.md 파이프라인 테이블 + L1 + memory 동시 갱신
- **기록 안 하면 = 안 만든 것.** 다른 세션이 발견 못하면 존재하지 않는다.
- 감시단 규칙 상세: `T9OS/constitution/GUARDIANS.md` 참조.

*이 규칙은 L3에 의해 개정 가능. 해석 자체가 변조(modulation)의 대상이다.*