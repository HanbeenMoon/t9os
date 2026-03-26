# ADR-036: model-project 모델 변경 — DeepSeek-R1-Distill → Qwen2.5-1.5B-Instruct

- 날짜: 2026-03-16
- 상태: 폐기됨(Deprecated)
- 사유: T-SUM/model-project 프로젝트 보류 상태. 파인튜닝 결정이 더 이상 유효하지 않음
- 결정: TSUM model-project의 파인튜닝 베이스 모델을 DeepSeek-R1-Distill-Qwen-1.5B에서 Qwen2.5-1.5B-Instruct로 변경한다. QLoRA 설정(lr 5e-5, bfloat16, epoch 5), 데이터 증강(500건 → 2,261건), 올바른 추론 템플릿을 동시에 적용한다.
- 이유: DeepSeek-R1-Distill은 reasoning 특화 모델로 QA에 부적합, 한글 깨짐(prepare_model_for_kbit_training 누락), 토큰 반복(Alpaca vs 추론 템플릿 불일치) 3가지 근본 원인 발견.
- 대안: DeepSeek 버그 수정 후 유지 (모델 자체가 QA 부적합), 더 큰 모델 (RTX 3060 12GB 제약), API 호출 (오프라인 동작 요구)
- 결과: eval_loss 24% 개선(0.52→0.40), 한국어 출력 정상화, TF-IDF RAG + 대화형 CLI + 자동 평가 구현
- 출처: 20260316_CC_003_041500_T9OS_v02_시몽동개정_model-project_project-alpha.txt, 20260316_CC_004_050000_model-project_모델정리.txt, 20260316_CC_001_(TSUM)_051000_model-project실전완성.txt

## Simondon Mapping
이접의 해소: reasoning vs QA, float16 vs bfloat16, Alpaca vs 추론 템플릿이라는 복수의 양립 불가능한 긴장이 모델 교체라는 새 구조에서 동시에 해소됨.
