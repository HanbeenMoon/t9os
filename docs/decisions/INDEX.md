# ADR Index

## Active

| # | 파일 | 결정 | 날짜 |
|---|------|------|------|
| 001 | [001-use-sqlite-entity-store.md](001-use-sqlite-entity-store.md) | SQLite를 엔티티 저장소로 선택 | 2026-03-15 |
| 002 | [002-simondon-phase-transition-model.md](002-simondon-phase-transition-model.md) | 시몽동 위상 전이 모델 채택 | 2026-03-16 |
| 003 | [003-three-tier-constitution.md](003-three-tier-constitution.md) | 3층 헌법 구조 (L1/L2/L3) | 2026-03-15 |
| 004 | [004-guardian-seven-tier.md](004-guardian-seven-tier.md) | 감시단 7종 구조 (G1~G7) | 2026-03-16 |
| 005 | [005-gemini-batch-guardian.md](005-gemini-batch-guardian.md) | Gemini batch로 감시단 실행 | 2026-03-16 |
| 006 | [006-session-claim-release.md](006-session-claim-release.md) | 세션 충돌 방지 claim/release | 2026-03-16 |
| 007 | [007-seed-engine-single-entry.md](007-seed-engine-single-entry.md) | T9 Seed 엔진 단일 진입점 | 2026-03-15 |
| 008 | [008-search-reuse-buy-build.md](008-search-reuse-buy-build.md) | SRBB 원칙 | 2026-03-15 |
| 009 | [009-preindividual-inbox-pattern.md](009-preindividual-inbox-pattern.md) | 전개체 inbox 패턴 | 2026-03-15 |
| 010 | [010-pipeline-registry-table.md](010-pipeline-registry-table.md) | 파이프라인 레지스트리 테이블 | 2026-03-16 |
| 011 | [011-hotl-autonomy-matrix.md](011-hotl-autonomy-matrix.md) | HITL→HOTL 전환, T1/T2/T3 자율성 티어 | 2026-03-19 |
| 012 | [012-data-integrity-verification.md](012-data-integrity-verification.md) | 데이터 무결성 자동 검증 (integrity_check.py) | 2026-03-19 |
| 013 | [013-telegram-bot-silent-mode.md](013-telegram-bot-silent-mode.md) | 텔레그램 봇 무응답 inbox 저장 | 2026-03-19 |
| 014 | [014-architecture-dashboard.md](014-architecture-dashboard.md) | T9D 아키텍처 시각화 페이지 | 2026-03-19 |
| 015 | [015-adr-simondon-mapping.md](015-adr-simondon-mapping.md) | ADR 시몽동 매핑 필드 의무화 | 2026-03-19 |
| 016 | [016-resurface-sediment.md](016-resurface-sediment.md) | 침전 엔티티 재활성화 (resurface) | 2026-03-19 |
| 017 | [017-t9d-refresh-integrity-merge.md](017-t9d-refresh-integrity-merge.md) | 새로고침 + 무결성 검증 통합 | 2026-03-19 |
| 018 | [018-hanbeen-architecture-init.md](018-hanbeen-architecture-init.md) | HANBEEN 아키텍처 초기화 — CLAUDE.md 에이전트 컨텍스트 시스템 | 2026-03-04 |
| 019 | [019-t9-dashboard-nextjs-vercel.md](019-t9-dashboard-nextjs-vercel.md) | T9 Dashboard — Next.js + Vercel 배포 아키텍처 | 2026-03-05 |
| 020 | [020-live-data-no-hardcoding.md](020-live-data-no-hardcoding.md) | 라이브 데이터 원칙 — 하드코딩 제거 + Notion DB화 | 2026-03-05 |
| 021 | [021-github-data-proxy.md](021-github-data-proxy.md) | GitHub 경유 데이터 프록시 — 로컬 로그를 Dashboard에 연동 | 2026-03-05 |
| 022 | [022-infra-status-monitoring.md](022-infra-status-monitoring.md) | 인프라 상태 모니터링 API | 2026-03-05 |
| 023 | [023-google-calendar-direct-api.md](023-google-calendar-direct-api.md) | Google Calendar 직접 API 연동 | 2026-03-06 |
| 024 | [024-wsl-ubuntu-single-cli.md](024-wsl-ubuntu-single-cli.md) | WSL 우분투 단일 CLI 환경 확정 | 2026-03-10 |
| 025 | [025-dashboard-briefing-role-split.md](025-dashboard-briefing-role-split.md) | Dashboard/Briefing 역할 분리 | 2026-03-17 |
| 026 | [026-gitignore-archive-sedimentation.md](026-gitignore-archive-sedimentation.md) | .gitignore 전면 정리 + ARCHIVE 침전 패턴 | 2026-03-17 |
| 027 | [027-cc-controltower-role-designation.md](027-cc-controltower-role-designation.md) | cc를 컨트롤타워로 지정 — claude.ai 대체, 3역할 체계 | 2026-02-21 |
| 030 | [030-pm3-paper-mill-pipeline.md](030-pm3-paper-mill-pipeline.md) | pipeline-project 학술 논문 자동화 파이프라인 아키텍처 | 2026-03-01 |
| 031 | [031-t9os-v02-simondon-overhaul.md](031-t9os-v02-simondon-overhaul.md) | T9 OS v0.2 시몽동 전면 개정 | 2026-03-16 |
| 032 | [032-odnar-ontology-engine-pivot.md](032-odnar-ontology-engine-pivot.md) | ODNAR 비전 복원 — 메모앱에서 개인 온톨로지 인프라로 피봇 | 2026-03-16 |
| 033 | [033-ux-five-principles-zero-decision.md](033-ux-five-principles-zero-decision.md) | T9 OS UX 5원칙 — Zero Decision 중심 설계 | 2026-03-16 |
| 034 | [034-t9bot-python-rewrite.md](034-t9bot-python-rewrite.md) | T9 봇 PowerShell → Python 재작성 (Supersedes: ADR-028) | 2026-03-16 |
| 035 | [035-seed-engine-binary-file-support.md](035-seed-engine-binary-file-support.md) | T9 Seed 엔진 바이너리 파일 파싱 확장 | 2026-03-16 |
| 037 | [037-session-end-hook-async-reindex.md](037-session-end-hook-async-reindex.md) | 세션 종료 훅 비동기화 — reindex 분리 | 2026-03-17 |
| 038 | [038-claude-octopus-code-review.md](038-claude-octopus-code-review.md) | claude-octopus 멀티 에이전트 코드 리뷰 | 2026-03-16 |
| 039 | [039-gpt-export-conversation-archive.md](039-gpt-export-conversation-archive.md) | GPT 대화 기록 전량 아카이빙 — 1,070건 | 2026-02-25 |
| 040 | [040-legacy-data-digest-pipeline.md](040-legacy-data-digest-pipeline.md) | 레거시 데이터 다이제스트 파이프라인 — 옵시디언+카톡+노션 | 2026-03-15 |
| 041 | [041-logging-standard-format.md](041-logging-standard-format.md) | 로깅 표준 파일명 형식 확립 | 2026-02-21 |
| 042 | [042-hanbeen-folder-restructure.md](042-hanbeen-folder-restructure.md) | HANBEEN 폴더 구조 표준화 — 4분할 | 2026-02-20 |
| 043 | [043-ssk-cc-full-handover.md](043-ssk-cc-full-handover.md) | research-project 논문 cc 전면 이관 — 55+ 리뷰어 자동화 | 2026-03-16 |
| 044 | [044-gemini-model-restriction.md](044-gemini-model-restriction.md) | Gemini 모델 제한 — 2.x 금지, 3/3.1만 | 2026-03-10 |
| 045 | [045-t9os-constitution-supremacy.md](045-t9os-constitution-supremacy.md) | T9 OS 헌법 최상위 우선 원칙 | 2026-03-16 |
| 046 | [046-session-individuation-protocol.md](046-session-individuation-protocol.md) | 세션 개체화 프로토콜 — 매 세션 종료 필수 | 2026-03-16 |
| 048 | [048-sc41-canvas-lms-automation.md](048-sc41-canvas-lms-automation.md) | coursework 학교생활 자동화 — Canvas LMS + cron | 2026-03-03 |
| 049 | [049-syncthing-tailscale-two-pc-sync.md](049-syncthing-tailscale-two-pc-sync.md) | Syncthing + Tailscale 서울-remote PC 동기화 | 2026-02-20 |
| 050 | [050-t9-seed-session-start-load-order.md](050-t9-seed-session-start-load-order.md) | 세션 시작 로드 순서 — L1→L2→WORKING→state | 2026-03-15 |
| 051 | [051-whisper-voice-pipeline.md](051-whisper-voice-pipeline.md) | 음성 전사 파이프라인 — faster-whisper | 2026-03-16 |
| 052 | [052-ipc-cross-session-communication.md](052-ipc-cross-session-communication.md) | IPC 세션 간 통신 | 2026-03-16 |
| 053 | [053-design-buy-not-build.md](053-design-buy-not-build.md) | 디자인은 Buy — cc가 직접 만들지 않는다 | 2026-03-17 |
| 054 | [054-preindividual-auto-processing.md](054-preindividual-auto-processing.md) | 전개체 자동 처리 — 저장만 하지 마라 | 2026-03-16 |
| 055 | [055-noconcurrent-file-access.md](055-noconcurrent-file-access.md) | 같은 파일 동시 접근 금지 | 2026-02-21 |
| 056 | [056-notion-to-local-migration.md](056-notion-to-local-migration.md) | Notion UI → 로컬 cc 중심 체제 전면 이관 (Supersedes: ADR-029) | 2026-03-15 |
| 057 | [057-token-economy-cc-responsibility.md](057-token-economy-cc-responsibility.md) | 토큰 경제 — cc 토큰=수명, 긴 작업 위임 | 2026-03-16 |
| 058 | [058-deploy-not-just-implement.md](058-deploy-not-just-implement.md) | 구현만 하지 마라 — 배포+가동확인까지 완료 | 2026-03-17 |
| 059 | [059-cc-as-odnar-cto.md](059-cc-as-odnar-cto.md) | cc를 ODNAR CTO로 지정 | 2026-03-16 |
| 060 | [060-pandoc-docx-generation.md](060-pandoc-docx-generation.md) | pandoc + reference-doc DOCX 생성 표준 | 2026-03-16 |
| 061 | [061-no-edit-without-approval.md](061-no-edit-without-approval.md) | 명시적 승인 없이 파일 수정/생성 금지 | 2026-03-17 |
| 062 | [062-trojan-horse-strategy-ssk.md](062-trojan-horse-strategy-ssk.md) | research-project 트로이목마 전략 — 학술지+학부 이중 산출물 | 2026-03-17 |
| 070 | [070-gdrive-drivefs-upload.md](070-gdrive-drivefs-upload.md) | Google Drive DriveFS 연동 — OAuth 없이 파일 업로드 | 2026-03-23 |
| 071 | [071-remote-control-always-on.md](071-remote-control-always-on.md) | Remote Control 상시 활성화 — bashrc alias | 2026-03-23 |
| 072 | [072-session-live-read-jsonl-first.md](072-session-live-read-jsonl-first.md) | 세션 JSONL 직접 읽기 원칙 — 변환 대기 금지 | 2026-03-23 |
| 073 | [073-orient-layer-architecture.md](073-orient-layer-architecture.md) | Orient Layer Architecture — 소프트 게이트를 분기 조건으로 구조화 | 2026-03-23 |
| 074 | [074-t9os-major-surgery-2026-03-23.md](074-t9os-major-surgery-2026-03-23.md) | T9OS 대수술 — bare except 전량 제거, DB 복구, OLA Phase 1, smoke test | 2026-03-23 |
| 075 | [075-concretisation-system.md](075-concretisation-system.md) | 구체화 시스템 — rm 금지, 수렴+침전으로 부산물 정리 | 2026-03-26 |
| 076 | [076-gravitational-individuation-engine.md](076-gravitational-individuation-engine.md) | Gravity Engine — 벡터 임베딩+NLI 기반 전개체 자동 개체화 | 2026-03-26 |

## Proposed (보류)

| # | 파일 | 결정 | 날짜 | 사유 |
|---|------|------|------|------|
| 047 | [047-odnar-supabase-nextjs-mvp.md](047-odnar-supabase-nextjs-mvp.md) | ODNAR MVP 기술 스택 — Next.js + Supabase + Three.js | 2026-02-24 | ODNAR 방향성 위기 (2026-03-19). 정의 미확정, 설계자 방향 결정 대기 |

## Superseded (대체됨)

| # | 파일 | 결정 | 날짜 | 대체 ADR |
|---|------|------|------|----------|
| 028 | [028-l2u-to-t9agent-telegram.md](028-l2u-to-t9agent-telegram.md) | legacy-bot watcher 폐기 → T9 Agent 텔레그램 봇 전환 | 2026-03-06 | ADR-034 (Python 재작성) |
| 029 | [029-notion-archive-db-separation.md](029-notion-archive-db-separation.md) | Notion 실행큐 DB와 결과 아카이브 DB 분리 | 2026-03-06 | ADR-056 (Notion→로컬 이관) |
| 075-dup | [075-새로고침-런체크-합침-새로고침-시-무결성-검증도-같이-실행.md](075-새로고침-런체크-합침-새로고침-시-무결성-검증도-같이-실행.md) | 새로고침+런체크 합침 (adr_auto.py 자동 생성 중복) | 2026-03-19 | ADR-017 (t9d-refresh-integrity-merge) |

## Deprecated (폐기됨)

| # | 파일 | 결정 | 날짜 | 사유 |
|---|------|------|------|------|
| 036 | [036-finbot-model-switch-qwen.md](036-finbot-model-switch-qwen.md) | model-project 모델 변경 — DeepSeek → Qwen2.5 | 2026-03-16 | T-SUM/model-project 프로젝트 보류, 결정 무효 |
