# ADR-042: workspace 폴더 구조 표준화 — PROJECTS/PERSONAL/_ai/_keys 4분할

- 날짜: 2026-02-20 (초기 설정), 2026-02-21 (전수조사+정리)
- 상태: 채택됨
- 결정: workspace 루트를 PROJECTS/(개발 프로젝트), PERSONAL/(학교/개인), _ai/(AI 로그+도구), _keys/(비밀키)로 4분할한다. 심볼릭 링크(~/code/workspace → /path/to/workspace)로 WSL 접근을 단축한다. FOR_AI, FOR_ME, dev 등 초기 폴더는 이 구조로 통합/폐기한다.
- 이유: 초기에는 dev/, FOR_AI/, FOR_ME/, personal/, resources/ 등 목적이 겹치는 폴더가 난립. Junction link도 혼재. 단일 원칙(용도별 4분할)으로 정리.
- 대안: 프로젝트별 독립 리포 (컨텍스트 분산), 단일 폴더 (구조 없음), Monorepo+workspace (과도한 설정)
- 결과: 전수조사 3회 실행(02-21, 02-28, 03-02), 디스크 절감 ~8.2GB, .gitignore 패턴 확립
- 출처: 20260220_CC_002_222046_seoul_setup_script.txt, 20260221_CC_026_165034_workspace_fullscan.txt, commit 99abfc12

## Simondon Mapping
전개체적 잠재성의 구조화: 무질서한 파일 집합(과포화 용액)에 4분할이라는 씨앗 결정을 도입하여 폴더 구조의 개체화를 촉발.
