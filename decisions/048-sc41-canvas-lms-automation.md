# ADR-048: coursework 학교생활 자동화 — Canvas LMS + cron

- 날짜: 2026-03-03 (Make.com 시도), 2026-03-05 (cron 전환)
- 상태: 채택됨
- 결정: coursework(4학년1학기) 학교 작업을 Canvas LMS API + sc41_cron.py로 자동화한다. LMS 파일 다운로드, 성적 조회를 cron으로 자동 실행한다. Make.com Canvas→Notion 연동은 시도 후 폐기하고 직접 API 호출로 전환.
- 이유: "최소 에너지 운영" 원칙. Make.com은 Canvas API 연동이 복잡하고 free tier 제한. 직접 Python 스크립트가 더 안정적.
- 대안: Make.com 자동화 유지 (free tier 제한, 복잡), 수동 확인 (시간 낭비), Zapier (유료)
- 결과: sc41_cron.py 파이프라인 등록, 매일 08:00 자동 실행, P0 하드코딩 토큰 제거(환경변수 전환)
- 출처: 20260303_CX_026_(legacy-bot)_201207_Make.com설계.txt, 20260305_CC_001_sc41_files_025159_결과.txt, 20260316_CC_003_041500_T9OS_v02_시몽동개정_model-project_project-alpha.txt

## Simondon Mapping
자동화를 통한 구체화: 분리된 기능(다운로드, 성적확인, 알림)이 단일 cron 파이프라인으로 수렴하여 "최소 에너지" 원칙을 구현.
