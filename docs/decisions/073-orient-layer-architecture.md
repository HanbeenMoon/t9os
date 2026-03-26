# ADR-073: Orient Layer Architecture (OLA) 도입

- 날짜: 2026-03-23
- 상태: Active
- 결정: PreToolUse 훅 체인에 Orient Layer를 추가한다. 기존 하드 게이트(물리적 차단) 뒤에 소프트 게이트를 구조화한 Orient 엔진을 배치하여, 추상적 원칙(SRBB, 철학 정합성, 전수 검사 등)을 분기 조건과 중단 조건으로 변환한다.
- 이유:
  - 현재 소프트 게이트는 CLAUDE.md에 자연어로만 존재하며, 에이전트가 읽을 수도 있고 안 읽을 수도 있다.
  - 하드 게이트(`pre-tool-hard-gate.sh`)는 "파괴적 명령 차단"에만 작동하며, "품질/원칙 준수 확인"에는 구조적 매개 계층이 없다.
  - 감시단은 사후 검증(post-hoc)이므로, 이미 500줄 코드를 작성한 뒤에야 SRBB 위반을 발견한다.
  - 인사이트가 memory에 쌓이지만 에이전트 행동 변화로 이어지지 않는 패턴이 반복된다.
- 대안:
  - **현상 유지 (소프트 게이트를 자연어로 유지)**: 에이전트가 매번 읽는다고 보장 불가. 탈락.
  - **하드 게이트에 소프트 로직 통합**: 한 파일이 비대해지고, 하드/소프트 경계가 흐려진다. 탈락.
  - **별도 Orient Layer 추가**: 관심사 분리, 점진적 도입 가능, 하드 게이트 불변. 채택.
- 결과:
  - 리서치 보고서: `T9OS/artifacts/OLA_ORIENT_LAYER_ARCHITECTURE.md`
  - Phase 0 (관찰): 현재~AT1 종료. 소프트 게이트 위반 사례 수집.
  - Phase 1 (최소 구현): `pre-tool-orient.py` 작성 + `.claude/settings.json` 훅 등록.
  - Phase 2 (안돈 추가): SRBB/DEPLOY pause 안돈 도입.
  - Phase 3 (라우팅 테이블): `orient_routes.yaml` + 감시단 연동.
  - Phase 4 (안정화): false positive 조정, 변조(modulation) 적용.
  - 부수 효과: `safe_change.sh` 스냅샷+smoke test 자동화로 "고치기 두려움" 해소.

## 핵심 구조

```
PreToolUse 훅 체인:
  [pre-tool-hard-gate.sh]  ← 물리적 차단 (기존, 불변)
         ↓
  [pre-tool-orient.py]     ← Orient Layer (신규)
    ├─ 구조 판별 (이 행동이 BUILD인가? DEPLOY인가? CONSTITUTION_CHANGE인가?)
    ├─ 안돈 트리거 (멈춰야 하는가? severity: block/pause)
    └─ 라우팅 테이블 (무엇을 확인해야 하는가?)
         ↓
  도구 실행
```

## 기존 구조와의 관계

| 기존 | OLA 이후 |
|------|---------|
| 하드 게이트 (pre-tool-hard-gate.sh) | 불변. OLA는 그 뒤에 체인됨 |
| 소프트 게이트 (CLAUDE.md 자연어) | OLA 라우팅 테이블로 점진 이관 |
| 감시단 (사후 검증) | OLA 로그를 참조하여 사전/사후 연계 |
| HOTL Autonomy Matrix | OLA가 대체하지 않음. T1/T2/T3과 직교적으로 작동 |

## Simondon Mapping

이 결정이 시몽동의 어떤 원리를 구현하는가:

- **연합된 환경(milieu associe)의 코드화**: L1에 명시된 "cc는 작업 시작 전 환경 상태를 감지하고 되먹임에 반응"을 자연어 지침에서 실행 가능한 훅으로 전환. 환경 감지가 구조적으로 강제된다.
- **이접(disparation) 감지의 자동화**: 안돈 트리거는 "양립 불가능한 조건"(예: BUILD 행동 + SRBB 미완료)을 자동 감지. L2의 이접 기반 상태 전이를 도구 호출 수준에서 구현.
- **준안정 상태 보존**: 스냅샷+smoke test로 변경 가능성을 열어두되 안전망 유지. 과안정(경직) 방지.
- **전도(transduction)**: 한 세션에서 발견된 인사이트가 OLA 라우팅 테이블에 등록되면, 모든 세션에서 자동으로 작동. 인사이트의 전도적 전파.
