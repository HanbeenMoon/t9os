# ADR-047: ODNAR MVP 기술 스택 — Next.js + Supabase + Three.js

- 날짜: 2026-02-24 (구조 확인), 2026-03-01 (랜딩 정리), 2026-03-07 (Three.js 구현)
- 상태: 보류(Proposed)
- 사유: ODNAR 방향성 위기 (2026-03-19). 정의 미확정, 한빈이 직접 방향 잡기 전까지 MVP 기술 스택 결정 보류
- 결정: ODNAR MVP를 Next.js(App Router) + Supabase(인증+DB) + Three.js(인터랙티브 시각화)로 구축한다. Zod로 타입 안전 데이터 검증, RPC 기반 Supabase 호출을 사용한다.
- 이유: Next.js는 SSR/SSG 지원으로 SEO 확보, Supabase는 Firebase 대비 SQL 기반으로 온톨로지 데이터 모델링에 적합, Three.js는 ODNAR의 "도넛 빈 곳" 메타포를 시각적으로 구현 가능.
- 대안: React SPA (SEO 불리), Firebase (NoSQL로 관계 데이터 부적합), D3.js만 (3D 시각화 제한)
- 결과: Supabase DDL 실행, 14페이지 빌드 성공, 인터랙티브 Three.js 온톨로지 장면 구현
- 출처: 20260224_CC_002_113227_ODNAR프로젝트구조확인.txt, 20260301_CX_002_(1-odnar)_130327_ODNAR랜딩정리.txt, 20260307_CX_008_(ODNAR)_103847_인터랙티브홈페이지Threejs구현.txt

## Simondon Mapping
기술적 앙상블의 구성: 각 기술(Next.js, Supabase, Three.js)이 독립 요소가 아니라 ODNAR의 비전(개인 온톨로지)을 구현하는 통합 기술적 개체로 구체화됨.
