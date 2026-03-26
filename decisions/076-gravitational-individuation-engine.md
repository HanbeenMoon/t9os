---
phase: individuating
transitioned_at: 2026-03-26
---

# ADR-076: Gravitational Individuation Engine

- 날짜: 2026-03-26
- 상태: Active
- 결정: 벡터 임베딩 + NLI 기반 전개체 자동 개체화 엔진(gravity engine) 도입
- 이유: 전개체(préindividuel)가 inbox에 축적만 되고 자동 개체화(individuation)되지 않는 구조적 병목. 설계자 수동 개입 없이 엔티티 간 인력(gravitation)을 계산하여 관계를 자동 발견하고, 준안정 상태에서 위상 전이를 촉발하는 엔진이 필요.

## 맥락

T9OS의 전개체 시스템은 capture → inbox → phase transition 흐름을 따르지만, relate(관계 형성)가 수동이었다. 엔티티 수가 증가하면서 설계자가 모든 관계를 직접 지정하는 것은 불가능. 시몽동의 개체화 이론에서 전개체적 긴장(tension préindividuelle)이 임계점을 넘으면 자발적으로 구조가 출현하듯, 벡터 공간에서 엔티티 간 근접성이 임계값을 넘으면 자동으로 관계를 형성하는 중력 모델을 채택.

## 시몽동 원문 근거

> "L'individuation est une résolution partielle qui se produit dans un système riche en potentiels, quand ce système atteint un état de sursaturation."
> (개체화는 퍼텐셜이 풍부한 체계가 과포화 상태에 도달할 때 발생하는 부분적 해결이다.)
> — Gilbert Simondon, *L'individuation à la lumière des notions de forme et d'information* (1958/2005), p.25

벡터 임베딩 = 퍼텐셜의 수치적 표현. 코사인 유사도 임계값 초과 = 과포화(sursaturation). 자동 relate = 부분적 해결(résolution partielle).

> "La transduction est une opération physique, biologique, mentale, sociale, par laquelle une activité se propage de proche en proche."
> — Simondon, ibid., p.32

NLI 기반 관계 검증 = transduction. 단순 거리가 아니라 의미적 함의(entailment)를 통해 관계가 전파.

## 한빈 반대이론 반영

벡터 유사도만으로 관계를 결정하면 false positive 폭발. "비슷하다 ≠ 관련 있다". 코사인 유사도 0.8인 두 문서가 실제로는 무관할 수 있다 (예: 동일 문체의 다른 주제).

대응:
1. **NLI 게이트**: 벡터 근접성은 후보 생성만. 최종 관계 확정은 NLI(Natural Language Inference) 모델이 entailment/contradiction 판정
2. **파동 모델(wave propagation)**: 관계 강도를 이진(관련/무관)이 아니라 연속적 파동으로 모델링. 감쇠(decay)와 간섭(interference) 포함
3. **설계자 override**: 자동 관계에 대한 설계자 거부권 보장. gravity가 제안, 설계자가 확정/거부

## 구현 Phase

### Phase 1 (cb96): 공간 인프라

`lib/vec.py` — 벡터 연산 기반 모듈

- 로컬 임베딩 생성 (sentence-transformers, GPU 불필요)
- entities 테이블에 embedding BLOB 컬럼 추가
- entity_vectors 테이블 (id, entity_id, model, vector, created_at)
- 코사인/유클리드 거리 계산 유틸리티
- config.py에 VEC_MODEL, VEC_DIM, GRAVITY_THRESHOLD 설정 추가

### Phase 2 (de73): 충돌 + NLI + 파동

`lib/gravity.py` — 개체화 엔진 본체

- 전개체 간 중력 계산 (벡터 근접성 × phase 가중치)
- NLI 기반 관계 검증 (entailment score > threshold → relate 자동 생성)
- 파동 전파: 새 엔티티 등록 시 기존 엔티티와의 중력장 재계산
- relates 테이블 자동 갱신 + transduction.py 연동
- Phase transition 자동 제안: 충분한 관계가 형성된 전개체 → individuating 전이 후보

## 관련 파일

| 파일 | 역할 |
|------|------|
| `lib/gravity.py` | 개체화 엔진 — 중력 계산, NLI 검증, 파동 전파 |
| `lib/vec.py` | 벡터 연산 — 임베딩 생성, 거리 계산, 인덱싱 |
| `lib/config.py` | VEC_MODEL, VEC_DIM, GRAVITY_THRESHOLD 설정 |
| `lib/transduction.py` | 위상 전이 연동 — gravity 결과를 전도(transduction)로 전파 |

## Simondon Mapping

- **전개체적 긴장 → 벡터 근접성**: 퍼텐셜이 수치화되어 측정 가능해짐
- **과포화 → 임계값 초과**: GRAVITY_THRESHOLD가 과포화 시점을 정의
- **개체화 → 자동 relate**: 관계 형성이 곧 개체화의 부분적 해결
- **전도(transduction) → NLI 전파**: 의미적 함의가 근접 엔티티로 전파
- **잔여(résidu) → 미매칭 엔티티**: 관계를 형성하지 못한 전개체는 잔여로 보존, 다음 파동에서 재시도
