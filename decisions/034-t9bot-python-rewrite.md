# ADR-034: T9 봇 PowerShell → Python 재작성

- 날짜: 2026-03-16
- 상태: 채택됨
- Supersedes: ADR-028 (legacy-bot→T9Agent PowerShell 봇)
- 결정: 텔레그램 봇을 PowerShell 1821줄(t9_agent.ps1)에서 Python 190줄(t9_bot.py)로 재작성한다. 음성 메시지 Whisper 자동 전사, 자연어 매칭("오늘 뭐해" → daily), /ask·/run·/compose·/capture 명령어를 지원한다.
- 이유: PowerShell은 WSL 환경에서 불안정하고, 인코딩 문제($script: 스코프 버그 등)가 반복됨. Python은 크로스플랫폼이고 telebot/whisper 라이브러리 생태계가 풍부.
- 대안: PowerShell 버그 수정 후 유지 (근본 구조 복잡), Node.js (Python이 T9OS 주 언어)
- 결과: nohup 백그라운드 상시 가동, WSL에서 네이티브 실행
- 출처: 20260316_CC_005_130000_전수조사_정리_UX.txt

## Simondon Mapping
구체화(concretization): 분산된 기능(텔레그램 수신, 명령 파싱, 엔진 호출, 음성 전사)이 190줄 단일 스크립트로 통합되어 기술적 성숙도 상승.
