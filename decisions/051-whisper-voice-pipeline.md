# ADR-051: 음성 전사 파이프라인 — faster-whisper 채택

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 텔레그램 음성 메시지를 faster-whisper로 자동 전사하여 T9 Seed에 전개체로 등록하는 파이프라인을 구축한다. /whisper 스킬로 호출 가능.
- 이유: 설계자이 모바일에서 음성으로 입력하는 경우가 많음. 텍스트 변환 없이는 T9 Seed에 등록 불가. OpenAI Whisper API는 비용 발생, faster-whisper는 로컬 GPU(RTX 3060)에서 무료 실행 가능.
- 대안: OpenAI Whisper API (유료), Google Speech-to-Text (유료), 수동 전사 (비효율)
- 결과: T9OS/pipes/whisper_pipeline.py 등록, t9_bot.py에서 음성 메시지 자동 연동
- 출처: 20260316_CC_005_130000_전수조사_정리_UX.txt, CLAUDE.md 파이프라인 레지스트리

## Simondon Mapping
전개체적 장의 감각 확장: 텍스트만 수용하던 입력 채널이 음성까지 확장되어 전개체의 포착 범위가 넓어짐.
