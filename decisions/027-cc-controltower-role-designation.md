# ADR-027: cc(Claude Code)를 컨트롤타워로 지정 — claude.ai 대체

- 날짜: 2026-02-21 (규칙 확립), 2026-03-15 (T9OS 전면 이관)
- 상태: 채택됨
- 결정: AI 오케스트레이션의 컨트롤타워를 웹 Claude AI(claude.ai)에서 Claude Code(cc)로 전환한다. cc가 판단/전략/라우팅을 전담하고, cx(Codex)는 코드/문서, gm(Gemini CLI)은 OCR/대량 반복을 담당하는 3역할 체계를 확립한다.
- 이유: 웹 UI는 세션 간 컨텍스트 유지 불가, 파일시스템 직접 접근 불가, 자동화 불가. CLI 기반 cc는 로컬 파일 접근, 스크립트 실행, git 연동이 가능하여 실제 오케스트레이션에 적합.
- 대안: claude.ai 웹 UI 유지 (세션 연속성 없음), Codex 단독 (전략적 판단력 부족), ChatGPT 중심 (로컬 접근 불가)
- 결과: CLAUDE.md에 역할 분담 테이블 명시, cx/gm에 작업 위임 패턴 정착, 토큰 절약 원칙 도입
- 출처: 20260221_CC_007_130351_claude_md_update.txt, 20260316_CC_003_041500_T9OS_v02_시몽동개정_model-project_project-alpha.txt

## Simondon Mapping
연합 환경(associated milieu)의 재구성: 기술적 개체(cc)가 환경(파일시스템+API+에이전트)과 되먹임 루프를 형성하여 전체 시스템의 구체화(concretization) 수준을 높임.
