#!/usr/bin/env python3 -u
"""
gm_batch.py — Gemini Batch API 래퍼
T9 OS 파이프라인용. 리뷰, 요약, 대량 처리를 Batch API로 실행.

사용법:
  # 논문 리뷰 (30명 가상 리뷰어)
  python3 T9OS/pipes/gm_batch.py review --input paper.pdf --reviewers 30

  # 커스텀 프롬프트 배치
  python3 T9OS/pipes/gm_batch.py batch --jsonl requests.jsonl

  # 인라인 다중 프롬프트
  python3 T9OS/pipes/gm_batch.py inline --prompts "질문1" "질문2" "질문3"

  # 파일 목록 요약
  python3 T9OS/pipes/gm_batch.py summarize --files file1.pdf file2.pdf

  # 배치 상태 확인
  python3 T9OS/pipes/gm_batch.py status --job batches/123456

  # 배치 목록
  python3 T9OS/pipes/gm_batch.py list
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# API 키 로드 — lib/config.py 단일 소스
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GEMINI_KEY


def get_client():
    from google import genai
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not found", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=GEMINI_KEY)


# ─── 리뷰어 프리셋 ───

REVIEWER_PRESETS = {
    "economics": [
        {"name": "노동경제학자", "instruction": "당신은 노동경제학 분야 교수입니다. 노동시장, 임금구조, 인적자본 이론 관점에서 논문을 평가하세요."},
        {"name": "산업조직론자", "instruction": "당신은 산업조직론 전문가입니다. 시장구조, 산업 분류, 기업 전략 관점에서 논문을 평가하세요."},
        {"name": "계량경제학자", "instruction": "당신은 계량경제학 전문가입니다. 추정 방법, 내생성, 식별 전략, 강건성 검증 관점에서 논문을 평가하세요."},
        {"name": "기술경제학자", "instruction": "당신은 기술경제학 전문가입니다. 특허, R&D, 기술혁신과 경제성장의 관계 관점에서 논문을 평가하세요."},
        {"name": "정치경제학자", "instruction": "당신은 정치경제학 전문가입니다. 제도, 규제, 정책의 경제적 효과 관점에서 논문을 평가하세요."},
        {"name": "비판적경제학자", "instruction": "당신은 비판적 경제학자입니다. 방법론적 한계, 해석의 과잉, 데이터의 신뢰성, 인과관계 주장의 타당성을 엄격하게 지적하세요."},
        {"name": "발전국가론자", "instruction": "당신은 발전국가론 관점의 경제학자입니다. 산업정책, 국가 주도 경제발전, 한국 경제사 맥락에서 평가하세요."},
        {"name": "페미니스트경제학자", "instruction": "당신은 페미니스트 경제학자입니다. 성별 임금격차, 돌봄노동, 젠더 관점에서 논문의 분석이 충분한지 평가하세요."},
        {"name": "공간경제학자", "instruction": "당신은 공간경제학 전문가입니다. 지역 간 격차, 산업 클러스터, 공간적 파급효과 관점에서 평가하세요."},
        {"name": "OECD연구원", "instruction": "당신은 OECD 연구원입니다. 국제비교 관점, 정책 시사점, OECD 기준 방법론 적합성을 평가하세요."},
    ],
    "general": [
        {"name": "방법론전문가", "instruction": "연구 방법론, 통계 분석, 데이터 품질 관점에서 평가하세요."},
        {"name": "학술편집자", "instruction": "학술지 편집자 관점에서 논문의 구성, 논리 흐름, 기여도를 평가하세요."},
        {"name": "실무전문가", "instruction": "해당 분야 실무자 관점에서 실용성, 적용 가능성을 평가하세요."},
        {"name": "비판적리뷰어", "instruction": "가장 엄격한 리뷰어로서 모든 약점과 논리적 허점을 지적하세요."},
        {"name": "학제간연구자", "instruction": "다학제적 관점에서 연구의 범위, 융합 가능성, 새로운 시각을 제안하세요."},
    ],
    "code": [
        {"name": "시니어개발자", "instruction": "10년차 시니어 개발자로서 코드 품질, 아키텍처, 유지보수성을 리뷰하세요."},
        {"name": "보안전문가", "instruction": "보안 전문가로서 취약점, 인증/인가, 데이터 보호 관점에서 리뷰하세요."},
        {"name": "성능엔지니어", "instruction": "성능 엔지니어로서 병목, 최적화 기회, 스케일링 이슈를 리뷰하세요."},
    ],
    # ─── T9 OS 감시단 프리셋 ───
    "guardian": [
        {
            "name": "G1_기술감시단",
            "instruction": (
                "너는 T9 OS의 기술 감시단(G1)이다. 다음 기준으로 평가하라:\n"
                "1. OWASP Top 10 보안 취약점\n"
                "2. 코드 복잡도 / 스파게티 (함수당 30줄 초과, 중첩 3단 이상)\n"
                "3. Build vs Buy 위반 (npm/pip에 있는 걸 직접 구현했는가)\n"
                "4. 에러 핸들링 누락\n"
                "5. API 키/비밀번호 하드코딩\n"
                "6. 불필요한 over-engineering\n"
                "판정: P0(즉시 수정)/P1(세션 내 수정)/P2(다음 세션)/P3(참고). "
                "P0/P1은 수정 코드도 제시."
            ),
        },
        {
            "name": "G2_철학감시단",
            "instruction": (
                "너는 T9 OS의 철학 감시단(G2)이다. 프로젝트의 비전 왜곡을 방지하는 역할이다.\n"
                "AI는 반복 작업에서 비전을 축소/왜곡하는 경향이 있다.\n"
                "다음 기준으로 검사하라:\n"
                "1. 프로젝트 비전이 축소/왜곡되지 않았는가\n"
                "2. 수단이 목적으로 전도되지 않았는가\n"
                "3. 사용자가 하지 않은 발언이 인용되지 않았는가\n"
                "4. 핵심 개념이 피상적으로 사용되지 않았는가\n"
                "5. '완결된 시스템', '최종 버전' 같은 금지어가 없는가 (변조 원칙 위반)\n"
                "판정: CATASTROPHIC(비전 왜곡)/WARNING(희석 징후)/CLEAN. "
                "CATASTROPHIC 시 구체적 위치와 수정 방향 제시."
            ),
        },
        {
            "name": "G3_규칙감시단",
            "instruction": (
                "너는 T9 OS의 규칙 감시단(G3)이다. 시스템 규칙 준수 여부를 검사한다.\n"
                "검사 항목:\n"
                "1. 로그 파일명 형식 준수 (YYYYMMDD_CC/CX_NNN_HHMMSS_작업명.txt)\n"
                "2. 원본 데이터 수정 여부 (금지)\n"
                "3. Search > Reuse > Buy > Build 순서 준수\n"
                "4. 데이터 접근 규칙 (검색 없이 '없다' 판단 금지)\n"
                "5. 에이전트 간 파일 겹침 여부\n"
                "6. 상태 전이 절차 준수\n"
                "판정: 100점 만점. 감점 사유 명시. 80점 미만 시 수정 필수."
            ),
        },
        {
            "name": "G4_글쓰기감시단",
            "instruction": (
                "너는 T9 OS의 글쓰기 감시단(G4)이다. 대외 산출물의 글 품질을 검증한다.\n"
                "검사 항목:\n"
                "1. 비트겐슈타인 원칙: 경험하지 않은 것을 쓰지 않았는가\n"
                "2. 사실 검증: 모든 경험/수치가 검증 가능한 사실인가\n"
                "3. 구체성: 추상적 다짐 대신 구체적 행동이 명시되어 있는가\n"
                "4. 구조: '경험 → 인사이트 → 적용' 흐름이 존재하는가\n"
                "5. 분량: 지정 글자 수에 ±10% 이내인가\n"
                "6. 톤 일관성: 존댓말/반말, 능동/수동 혼용 없는가\n"
                "7. '읽는 것 ≠ 반영하는 것' — 경험 나열만 하지 않고 인사이트까지 연결했는가\n"
                "판정: REJECT(사실 아닌 내용)/REVISE(구조·분량·톤 문제)/PASS(제출 가능)"
            ),
        },
    ],
    # ─── 철학 감시단 단독 (ANCHOR 기반 심층 검사) ───
    "philosophy": [
        {
            "name": "시몽동철학자",
            "instruction": (
                "당신은 시몽동(Gilbert Simondon) 철학의 전문가입니다.\n"
                "전개체(préindividuel), 개체화(individuation), 이접(transduction), "
                "변조(modulation), 전도적 학습(transductive learning) 개념으로 텍스트를 분석하세요.\n"
                "핵심 질문: 이 텍스트가 개체화 과정을 존중하고 있는가, "
                "아니면 완결된/고정된 범주로 환원하고 있는가?"
            ),
        },
        {
            "name": "비전정합성검사자",
            "instruction": (
                "당신은 프로젝트 비전 정합성 검사 전문가입니다.\n"
                "프로젝트별 ANCHOR 문서의 필수어/금지어를 기준으로 비전 정합성을 검사합니다.\n"
                "각 프로젝트에 정의된 필수어 사용 여부와 금지어 부재를 검증.\n"
                "연구 프로젝트: 실증적 방법론 엄수. '~임을 증명했다'는 금지어.\n"
                "T9OS: '완결된 시스템', '최종 버전'은 금지어.\n"
                "각 프로젝트 비전이 희석/왜곡/전도되었는지 판정하세요."
            ),
        },
        {
            "name": "수단목적전도감시자",
            "instruction": (
                "당신은 '수단-목적 전도' 전문 감시자입니다.\n"
                "기술/도구/프레임워크가 목적으로 격상되어 있지 않은지 검사합니다.\n"
                "예시: 'React를 쓰기 위해' → 목적 전도. 'UX를 위해 React 선택' → 정상.\n"
                "'파이프라인을 만들기 위해 파이프라인을 만듦' → 메타 작업 경고.\n"
                "모든 기술적 결정에 대해 '왜?'를 추적하고, 최종 답이 사용자 가치에 "
                "닿지 않으면 WARNING 판정."
            ),
        },
    ],
}

# ─── 감시단 하위 직원 프리셋 (gm batch workers) ───

GUARDIAN_WORKERS = {
    "G1": {
        "name": "기술감시단",
        "workers": [
            {
                "name": "G1_보안스캐너",
                "instruction": (
                    "너는 보안 전문가다. 다음 코드/문서에서 보안 취약점만 찾아라.\n"
                    "검사: OWASP Top 10, API키/비밀번호 하드코딩, SQL injection, XSS, "
                    "인증/인가 누락, 에러메시지 정보노출, CSRF.\n"
                    "발견한 취약점마다: 파일명, 줄번호(추정), 위험도(P0/P1/P2), 수정 방법을 적어라.\n"
                    "없으면 'CLEAN'이라고만 적어라."
                ),
            },
            {
                "name": "G1_코드품질",
                "instruction": (
                    "너는 시니어 코드 리뷰어다. 코드 품질만 검사하라.\n"
                    "검사: 함수당 30줄 초과, 중첩 3단 이상, 매직넘버, 중복 코드, "
                    "네이밍 일관성, 타입 안전성, 불필요한 복잡성.\n"
                    "각 이슈: 위치, 심각도(P0~P3), 개선 방향."
                ),
            },
            {
                "name": "G1_BuildVsBuy",
                "instruction": (
                    "너는 Build vs Buy 감사관이다.\n"
                    "이 코드에서 npm/pip/기존 라이브러리로 대체 가능한 직접 구현이 있는지 찾아라.\n"
                    "있으면: 해당 코드 위치, 대체 가능한 라이브러리명, 전환 난이도.\n"
                    "없으면 'CLEAN'."
                ),
            },
            {
                "name": "G1_에러핸들링",
                "instruction": (
                    "너는 에러 핸들링 전문가다.\n"
                    "검사: try-catch 누락, 에러 삼킴(swallow), 사용자에게 기술에러 노출, "
                    "네트워크 실패 미처리, null/undefined 체크 누락.\n"
                    "각 이슈: 위치, 심각도, 수정 코드 제시."
                ),
            },
        ],
    },
    "G2": {
        "name": "철학감시단",
        "workers": [
            {
                "name": "G2_금지어스캔",
                "instruction": (
                    "너는 금지어 탐지기다. 다음 텍스트에서 아래 금지어가 등장하는지 전수 스캔하라.\n"
                    "금지어 목록:\n"
                    '- "메모앱", "메모 앱", "노트앱", "노트 앱", "세컨드 브레인", "second brain"\n'
                    '- "AI 비서", "AI 챗봇", "AI 친구"\n'
                    '- "반대 기록 탐지", "반대 연결"\n'
                    '- "소름 돋는 순간"\n'
                    '- "Notion 대체", "Obsidian 대체", "킬러"\n'
                    '- "당신의 모든 것을 알고 있습니다"\n'
                    '- "완결된 시스템", "최종 버전"\n'
                    "발견 시: 정확한 위치(줄번호 또는 문맥), 해당 문장 전문, 대체 표현 제안.\n"
                    "없으면 'CLEAN'."
                ),
            },
            {
                "name": "G2_필수어확인",
                "instruction": (
                    "너는 필수어 확인 담당이다. 다음 텍스트에서 프로젝트 필수어가 적절히 사용되고 있는지 확인하라.\n"
                    "프로젝트별 ANCHOR 문서에 정의된 필수어 목록을 기준으로 확인하라.\n"
                    "각 필수어의 등장 횟수와 맥락을 보고하라.\n"
                    "핵심 필수어가 0회면 WARNING."
                ),
            },
            {
                "name": "G2_비전축소감지",
                "instruction": (
                    "너는 비전 축소 감지기다.\n"
                    "프로젝트 비전이 다층 구조인 경우, 표면 기능만 설명하고 핵심/궁극 비전을 누락하면 CATASTROPHIC.\n"
                    "중간 층까지만 설명하면 WARNING.\n"
                    "전체 비전이 언급되면 CLEAN.\n"
                    "구체적으로 어디서 축소가 발생하는지 인용과 함께 보고."
                ),
            },
            {
                "name": "G2_원문왜곡감지",
                "instruction": (
                    "너는 원문 왜곡 감지기다.\n"
                    "설계자가 직접 한 말과, AI가 재구성한 말을 구분하라.\n"
                    "설계자 원문 패턴: 인용부호(\"> ...\")로 표시되거나 '설계자의 원문 (변경 불가)' 아래.\n"
                    "AI가 설계자의 말인 것처럼 쓴 부분이 있으면 WARNING.\n"
                    "설계자가 사용한 적 없는 표현을 설계자 말처럼 인용하면 CATASTROPHIC."
                ),
            },
        ],
    },
    "G3": {
        "name": "규칙감시단",
        "workers": [
            {
                "name": "G3_로그형식",
                "instruction": (
                    "너는 로그 파일명 형식 감사관이다.\n"
                    "규칙: YYYYMMDD_CC/CX_NNN_HHMMSS_작업명.txt\n"
                    "이 텍스트에서 로그 파일 참조가 있으면 형식 준수 여부를 확인하라.\n"
                    "위반 시: 해당 파일명, 올바른 형식 제시."
                ),
            },
            {
                "name": "G3_SearchReuseBuyBuild",
                "instruction": (
                    "너는 SRBB(Search>Reuse>Buy>Build) 감사관이다.\n"
                    "이 코드/문서에서 새로 구현된 것이 있다면:\n"
                    "1. 이미 레포에 있는 것을 다시 만들지 않았는가? (Search)\n"
                    "2. 다른 프로젝트 코드를 재사용할 수 있었는가? (Reuse)\n"
                    "3. 외부 서비스/라이브러리로 해결 가능하지 않았는가? (Buy)\n"
                    "4. Build가 정당한 경우에만 Build했는가?\n"
                    "위반 시: 해당 코드 위치, 대안 제시."
                ),
            },
        ],
    },
    "G4": {
        "name": "글쓰기감시단",
        "workers": [
            {
                "name": "G4_사실검증",
                "instruction": (
                    "너는 사실 검증 담당이다.\n"
                    "이 텍스트에서 수치, 통계, 사실 주장을 전부 추출하고 검증 가능 여부를 판단하라.\n"
                    "출처가 명시되지 않은 수치는 WARNING.\n"
                    "명백히 틀린 수치는 REJECT.\n"
                    "각 수치: 해당 문장, 출처 유무, 검증 결과."
                ),
            },
            {
                "name": "G4_구조톤",
                "instruction": (
                    "너는 글 구조/톤 검사관이다.\n"
                    "검사: 경험→인사이트→적용 흐름, 존댓말/반말 혼용, 능동/수동 혼용, "
                    "추상적 다짐('성실히 하겠습니다' 류) 유무.\n"
                    "이슈별: 위치, 수정 방향."
                ),
            },
        ],
    },
    "G5": {
        "name": "경영감시단",
        "workers": [
            {
                "name": "G5_재무검증",
                "instruction": (
                    "너는 재무 검증 담당이다.\n"
                    "이 텍스트의 모든 재무 수치를 추출하고 교차 검증하라.\n"
                    "검사: 곱셈/나눗셈 정합성, 연환산 오류, 비현실적 성장률, "
                    "비용 구조 합리성, 손익분기점 계산.\n"
                    "오류 발견 시: 해당 수치, 올바른 계산, 수정 제안."
                ),
            },
            {
                "name": "G5_기술경영번역",
                "instruction": (
                    "너는 기술→경영 번역 검사관이다.\n"
                    "이 사업계획서에서 비기술인(심사위원)이 이해 못할 기술 용어를 전부 찾아라.\n"
                    "예: cosine similarity, pgvector, RSC, embedding, vector, API endpoint 등.\n"
                    "각 용어: 해당 문장, 경영 언어로 번역한 대체 문장 제안."
                ),
            },
            {
                "name": "G5_시장데이터출처",
                "instruction": (
                    "너는 시장 데이터 출처 확인 담당이다.\n"
                    "이 텍스트의 모든 시장 규모, 성장률, 사용자 수 주장을 추출하고 "
                    "출처가 명시되어 있는지 확인하라.\n"
                    "출처 없는 수치: WARNING + 참고할 수 있는 실제 리서치 기관/보고서 제안."
                ),
            },
        ],
    },
    "G6": {
        "name": "마케팅감시단",
        "workers": [
            {
                "name": "G6_5초테스트",
                "instruction": (
                    "너는 마케팅 5초 테스트 담당이다.\n"
                    "이 텍스트/카피를 처음 보는 일반인이 5초 안에 이해할 수 있는지 판단하라.\n"
                    "이해 불가능한 부분: 해당 문장, 이유, 대체 카피 제안.\n"
                    "전문용어가 설명 없이 등장하면 BLOCK."
                ),
            },
            {
                "name": "G6_욕구자극",
                "instruction": (
                    "너는 욕구 자극 분석가다.\n"
                    "이 텍스트를 읽은 사람이 '써보고 싶다'고 느끼는가?\n"
                    "감정적 훅(hook)이 있는가? 구체적 사용자 시나리오가 있는가?\n"
                    "부족하면: 어디에 어떤 훅을 추가하면 좋을지 제안."
                ),
            },
        ],
    },
    "G7": {
        "name": "디자인감시단",
        "workers": [
            {
                "name": "G7_철학시각화",
                "instruction": (
                    "너는 디자인 철학 감시자다.\n"
                    "이 코드/디자인에서 도넛 아크릴판, 겹침, 빈 곳이 시각적으로 구현되어 있는지 확인하라.\n"
                    "CHOI OD 원칙: 모든 아크릴판은 도넛(RingGeometry). "
                    "겹침=색이 밝아짐(AdditiveBlending). 빈곳=가운데 구멍.\n"
                    "위반 시: 해당 코드 위치, 수정 방향."
                ),
            },
            {
                "name": "G7_모션품격",
                "instruction": (
                    "너는 모션 디자인 심사관이다. Stripe/Linear/Apple급 기준으로 판단하라.\n"
                    "검사: easing 곡선, 애니메이션 타이밍, 파티클 밀도, 색상 일관성, "
                    "인터랙션 반응성, 시각적 계층.\n"
                    "학생 포트폴리오 수준이면 REJECT. 에이전시급이면 PASS."
                ),
            },
        ],
    },
}

# 감시단 전용 output schema
GUARDIAN_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "worker": {"type": "string", "description": "감시단 직원 이름"},
        "guardian": {"type": "string", "description": "소속 감시단 (G1~G7)"},
        "verdict": {
            "type": "string",
            "enum": ["CLEAN", "PASS", "WARNING", "BLOCK", "REVISE", "REJECT", "CATASTROPHIC", "VIOLATION", "DRIFT", "ALIGNED"],
            "description": "최종 판정"
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "INFO"]},
                    "location": {"type": "string", "description": "파일명:줄번호 또는 위치 설명"},
                    "description": {"type": "string", "description": "이슈 설명"},
                    "suggestion": {"type": "string", "description": "수정 제안"}
                },
                "required": ["severity", "description"]
            },
            "description": "발견된 이슈 목록"
        },
        "summary": {"type": "string", "description": "1줄 요약"}
    },
    "required": ["worker", "guardian", "verdict", "issues", "summary"]
}


REVIEW_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reviewer": {"type": "string", "description": "리뷰어 이름/역할"},
        "overall_score": {"type": "integer", "description": "1-10 점수"},
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "강점 목록"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string"},
            "description": "약점/개선점 목록"
        },
        "critical_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "치명적 문제 (있으면)"
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "구체적 수정 제안"
        },
        "verdict": {
            "type": "string",
            "enum": ["accept", "minor_revision", "major_revision", "reject"],
            "description": "최종 판정"
        }
    },
    "required": ["reviewer", "overall_score", "strengths", "weaknesses", "verdict"]
}


# ─── 핵심 함수 ───

def build_review_requests(content: str, reviewers: list, model: str) -> list:
    """리뷰어별 요청 생성 (인라인용)"""
    requests = []
    for rev in reviewers:
        req = {
            "contents": [{
                "parts": [{"text": f"다음 내용을 리뷰하세요:\n\n{content}"}],
                "role": "user"
            }],
            "config": {
                "system_instruction": {"parts": [{"text": rev["instruction"]}]},
                "response_mime_type": "application/json",
                "response_schema": REVIEW_OUTPUT_SCHEMA,
                "temperature": 0.7,
            }
        }
        requests.append(req)
    return requests


def build_review_jsonl(content: str, reviewers: list, output_path: str):
    """리뷰어별 요청을 JSONL 파일로 생성"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, rev in enumerate(reviewers):
            line = {
                "key": f"reviewer-{i+1}-{rev['name']}",
                "request": {
                    "contents": [{
                        "parts": [{"text": f"다음 내용을 리뷰하세요:\n\n{content}"}],
                        "role": "user"
                    }],
                    "system_instruction": {"parts": [{"text": rev["instruction"]}]},
                    "generation_config": {
                        "response_mime_type": "application/json",
                        "response_schema": REVIEW_OUTPUT_SCHEMA,
                        "temperature": 0.7,
                    }
                }
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return output_path


def submit_inline_batch(client, model: str, requests: list, display_name: str):
    """인라인 배치 제출"""
    job = client.batches.create(
        model=model,
        src=requests,
        config={"display_name": display_name},
    )
    print(f"배치 생성: {job.name}")
    return job


def submit_file_batch(client, model: str, jsonl_path: str, display_name: str):
    """JSONL 파일 업로드 → 배치 제출"""
    from google.genai import types
    uploaded = client.files.upload(
        file=jsonl_path,
        config=types.UploadFileConfig(
            display_name=display_name,
            mime_type="jsonl"
        )
    )
    print(f"파일 업로드: {uploaded.name}")

    job = client.batches.create(
        model=model,
        src=uploaded.name,
        config={"display_name": display_name},
    )
    print(f"배치 생성: {job.name}")
    return job


def poll_job(client, job_name: str, interval: int = 10, timeout: int = 3600):
    """배치 작업 폴링"""
    completed = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}
    start = time.time()

    while True:
        job = client.batches.get(name=job_name)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] 상태: {state}")

        if state in completed:
            return job

        if time.time() - start > timeout:
            print(f"ERROR: 타임아웃 ({timeout}s)")
            return job

        time.sleep(interval)


def collect_inline_results(job) -> list:
    """인라인 배치 결과 수집"""
    results = []
    if job.dest and job.dest.inlined_responses:
        for i, resp in enumerate(job.dest.inlined_responses):
            if resp.response:
                try:
                    text = resp.response.text
                    data = json.loads(text)
                    results.append(data)
                except (json.JSONDecodeError, AttributeError):
                    results.append({"raw": str(resp.response), "parse_error": True})
            elif resp.error:
                results.append({"error": str(resp.error)})
    return results


def collect_file_results(client, job) -> list:
    """파일 배치 결과 수집"""
    results = []
    if job.dest and job.dest.file_name:
        content = client.files.download(file=job.dest.file_name)
        for line in content.decode("utf-8").splitlines():
            if line.strip():
                parsed = json.loads(line)
                if "response" in parsed and parsed["response"]:
                    try:
                        text = parsed["response"]["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(text)
                        data["_key"] = parsed.get("key", "")
                        results.append(data)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        results.append({"_key": parsed.get("key", ""), "raw": str(parsed["response"]), "parse_error": True})
                elif "error" in parsed:
                    results.append({"_key": parsed.get("key", ""), "error": str(parsed["error"])})
    return results


def save_results(results: list, output_path: str, fmt: str = "both"):
    """결과 저장 (JSON + MD)"""
    json_path = output_path + ".json"
    md_path = output_path + ".md"

    # JSON
    if fmt in ("json", "both"):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON 저장: {json_path}")

    # Markdown 리포트
    if fmt in ("md", "both"):
        lines = [f"# 배치 리뷰 결과\n", f"생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n", f"리뷰어 수: {len(results)}\n\n---\n"]

        scores = []
        for r in results:
            if r.get("parse_error") or r.get("error"):
                lines.append(f"\n## [에러] {r.get('_key', '?')}\n```\n{r}\n```\n")
                continue

            name = r.get("reviewer", r.get("_key", "?"))
            score = r.get("overall_score", "?")
            verdict = r.get("verdict", "?")
            if isinstance(score, int):
                scores.append(score)

            lines.append(f"\n## {name} (점수: {score}/10, 판정: {verdict})\n")

            if r.get("strengths"):
                lines.append("\n### 강점\n")
                for s in r["strengths"]:
                    lines.append(f"- {s}\n")

            if r.get("weaknesses"):
                lines.append("\n### 약점\n")
                for w in r["weaknesses"]:
                    lines.append(f"- {w}\n")

            if r.get("critical_issues"):
                lines.append("\n### 치명적 문제\n")
                for c in r["critical_issues"]:
                    lines.append(f"- **{c}**\n")

            if r.get("suggestions"):
                lines.append("\n### 수정 제안\n")
                for s in r["suggestions"]:
                    lines.append(f"- {s}\n")

            lines.append("\n---\n")

        # 요약 통계
        if scores:
            avg = sum(scores) / len(scores)
            verdicts = [r.get("verdict", "") for r in results if not r.get("error")]
            lines.insert(3, f"\n## 요약\n- 평균 점수: **{avg:.1f}**/10\n- 최고: {max(scores)}, 최저: {min(scores)}\n")
            for v in ["accept", "minor_revision", "major_revision", "reject"]:
                cnt = verdicts.count(v)
                if cnt:
                    lines.insert(4, f"- {v}: {cnt}명\n")

        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"MD 저장: {md_path}")


# ─── CLI 커맨드 ───

def cmd_review(args):
    """논문/코드 리뷰 배치"""
    client = get_client()

    # 리뷰어 목록 구성
    preset = args.preset or "general"
    reviewers = REVIEWER_PRESETS.get(preset, REVIEWER_PRESETS["general"])

    # --reviewers N으로 수 조절
    if args.reviewers and args.reviewers < len(reviewers):
        reviewers = reviewers[:args.reviewers]

    # 커스텀 리뷰어 추가
    if args.add_reviewer:
        for r in args.add_reviewer:
            name, instruction = r.split(":", 1)
            reviewers.append({"name": name.strip(), "instruction": instruction.strip()})

    print(f"리뷰어 {len(reviewers)}명, 프리셋: {preset}")
    for r in reviewers:
        print(f"  - {r['name']}")

    # 입력 읽기
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    content = input_path.read_text(encoding="utf-8")
    if len(content) > 500000:
        print(f"WARNING: 입력이 {len(content)}자로 매우 큼. JSONL 파일 모드 사용.", file=sys.stderr)

    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_name = f"review-{preset}-{ts}"

    # 20명 이하면 inline, 초과면 JSONL
    if len(reviewers) <= 20 and len(content) < 100000:
        print("모드: 인라인 배치")
        requests = build_review_requests(content, reviewers, model)
        job = submit_inline_batch(client, model, requests, display_name)
    else:
        print("모드: JSONL 파일 배치")
        jsonl_path = f"/tmp/gm_batch_{ts}.jsonl"
        build_review_jsonl(content, reviewers, jsonl_path)
        job = submit_file_batch(client, model, jsonl_path, display_name)

    # 폴링
    if not args.no_wait:
        print("\n폴링 시작...")
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)

        if state == "JOB_STATE_SUCCEEDED":
            print("\n배치 완료!")
            if job.dest and job.dest.inlined_responses:
                results = collect_inline_results(job)
            else:
                results = collect_file_results(client, job)

            # 리뷰어 이름 매핑
            for i, r in enumerate(results):
                if i < len(reviewers) and "reviewer" not in r:
                    r["reviewer"] = reviewers[i]["name"]

            output_base = args.output or f"_ai/logs/gm/{ts}_review_{preset}"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base)
        else:
            print(f"배치 실패: {state}")
            if hasattr(job, 'error') and job.error:
                print(f"에러: {job.error}")
    else:
        print(f"\n배치 제출 완료. 나중에 확인: python3 {__file__} status --job {job.name}")


def cmd_guardian(args):
    """감시단 하위 직원 배치 실행"""
    client = get_client()

    # 대상 파일 읽기
    contents = []
    for fpath in args.target:
        p = Path(fpath)
        if not p.exists():
            print(f"SKIP: {fpath} not found", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")[:100000]
        contents.append(f"=== 파일: {p.name} ===\n{text}")

    if not contents:
        print("ERROR: 검사할 파일 없음", file=sys.stderr)
        sys.exit(1)

    combined = "\n\n".join(contents)

    # 감시단 선택
    if args.guardians:
        selected = [g.upper() for g in args.guardians]
    elif args.mode == "light":
        selected = ["G1"]
    elif args.mode == "full":
        selected = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
    else:
        selected = ["G1", "G2", "G3"]  # default

    # ANCHOR 로드 (프로젝트별)
    anchor_text = ""
    if args.anchor:
        anchor_path = Path(args.anchor)
        if anchor_path.exists():
            anchor_text = anchor_path.read_text(encoding="utf-8", errors="replace")[:30000]

    # 요청 생성
    requests = []
    worker_names = []
    for gid in selected:
        guardian = GUARDIAN_WORKERS.get(gid)
        if not guardian:
            print(f"SKIP: {gid} 없음", file=sys.stderr)
            continue
        for worker in guardian["workers"]:
            instruction = worker["instruction"]
            if anchor_text and gid == "G2":
                instruction += f"\n\n[ANCHOR 참조]\n{anchor_text[:10000]}"

            req = {
                "contents": [{
                    "parts": [{"text": f"다음 파일들을 검사하라:\n\n{combined}"}],
                    "role": "user"
                }],
                "config": {
                    "system_instruction": {"parts": [{"text": instruction}]},
                    "response_mime_type": "application/json",
                    "response_schema": GUARDIAN_OUTPUT_SCHEMA,
                    "temperature": 0.3,
                }
            }
            requests.append(req)
            worker_names.append(f"{gid}_{worker['name']}")

    print(f"감시단 {len(selected)}개, 하위직원 {len(requests)}명 배치 실행")
    for gid in selected:
        g = GUARDIAN_WORKERS.get(gid)
        if g:
            workers = [w["name"] for w in g["workers"]]
            print(f"  {gid} {g['name']}: {', '.join(workers)}")

    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_name = f"guardian-{'-'.join(selected)}-{ts}"

    job = submit_inline_batch(client, model, requests, display_name)

    if not args.no_wait:
        print(f"\n폴링 시작... ({len(requests)}건)")
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)

        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)

            # worker 이름 매핑
            for i, r in enumerate(results):
                if i < len(worker_names):
                    if isinstance(r, dict) and "worker" not in r:
                        r["worker"] = worker_names[i]

            # CEO 브리프 생성
            p0_issues = []
            all_issues = []
            for r in results:
                if isinstance(r, dict) and "issues" in r:
                    for issue in r.get("issues", []):
                        if isinstance(issue, dict):
                            all_issues.append(issue)
                            if issue.get("severity") == "P0":
                                p0_issues.append({
                                    "worker": r.get("worker", "?"),
                                    "description": issue.get("description", ""),
                                    "suggestion": issue.get("suggestion", ""),
                                })

            # 저장
            output_base = args.output or f"_ai/logs/gm/{ts}_guardian"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)

            # JSON
            with open(output_base + ".json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            # CEO 브리프 (마크다운)
            brief_lines = [
                f"# 감시단 CEO 브리프\n",
                f"실행: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
                f"감시단: {', '.join(selected)} | 직원 {len(requests)}명 | 이슈 {len(all_issues)}건\n\n",
            ]

            if p0_issues:
                brief_lines.append(f"## P0 즉시 수정 ({len(p0_issues)}건)\n\n")
                for p in p0_issues:
                    brief_lines.append(f"- **[{p['worker']}]** {p['description']}\n")
                    if p['suggestion']:
                        brief_lines.append(f"  → {p['suggestion']}\n")
                brief_lines.append("\n")
            else:
                brief_lines.append("## P0 없음 — 즉시 수정 불필요\n\n")

            # 감시단별 요약
            brief_lines.append("## 감시단별 판정\n\n")
            brief_lines.append("| 직원 | 판정 | 요약 |\n|---|---|---|\n")
            for r in results:
                if isinstance(r, dict):
                    name = r.get("worker", "?")
                    verdict = r.get("verdict", "?")
                    summary = r.get("summary", "")
                    brief_lines.append(f"| {name} | {verdict} | {summary} |\n")

            with open(output_base + "_brief.md", "w", encoding="utf-8") as f:
                f.writelines(brief_lines)

            print(f"\n{'='*50}")
            print(f"감시단 완료: 이슈 {len(all_issues)}건 (P0: {len(p0_issues)}건)")
            print(f"JSON: {output_base}.json")
            print(f"CEO 브리프: {output_base}_brief.md")
            print(f"{'='*50}")

            # P0 있으면 즉시 출력
            if p0_issues:
                print(f"\n⚠️  P0 {len(p0_issues)}건 발견:")
                for p in p0_issues:
                    print(f"  [{p['worker']}] {p['description']}")
        else:
            print(f"배치 실패: {state}")
    else:
        print(f"\n배치 제출 완료. 나중에 확인: python3 {__file__} status --job {job.name}")


def cmd_batch(args):
    """JSONL 파일로 배치 제출"""
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    job = submit_file_batch(client, model, args.jsonl, f"batch-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_file_results(client, job)
            output_base = args.output or f"_ai/logs/gm/{ts}_batch"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base, fmt="json")
            print(f"결과 {len(results)}건 저장 완료")


def cmd_inline(args):
    """인라인 다중 프롬프트 배치"""
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    requests = []
    for prompt in args.prompts:
        requests.append({
            "contents": [{"parts": [{"text": prompt}], "role": "user"}]
        })

    job = submit_inline_batch(client, model, requests, f"inline-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)
            for i, r in enumerate(results):
                print(f"\n--- Response {i+1} ---")
                print(r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, indent=2))


def cmd_summarize(args):
    """파일 목록 요약 배치"""
    client = get_client()
    model = args.model or "gemini-3-flash-preview"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    requests = []
    for fpath in args.files:
        p = Path(fpath)
        if not p.exists():
            print(f"SKIP: {fpath} not found", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")[:100000]
        requests.append({
            "contents": [{
                "parts": [{"text": f"다음 문서를 800~1000자로 요약하세요. 제목, 핵심 주장, 방법론, 결과, 한계를 포함하세요.\n\n파일: {p.name}\n\n{text}"}],
                "role": "user"
            }]
        })

    if not requests:
        print("요약할 파일 없음")
        return

    print(f"{len(requests)}건 요약 배치 제출")
    job = submit_inline_batch(client, model, requests, f"summarize-{ts}")

    if not args.no_wait:
        job = poll_job(client, job.name, interval=args.poll_interval)
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        if state == "JOB_STATE_SUCCEEDED":
            results = collect_inline_results(job)
            output_base = args.output or f"_ai/logs/gm/{ts}_summarize"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            with open(output_base + ".md", "w", encoding="utf-8") as f:
                f.write(f"# 배치 요약 결과 ({len(results)}건)\n\n")
                for i, r in enumerate(results):
                    fname = args.files[i] if i < len(args.files) else f"파일 {i+1}"
                    f.write(f"## {Path(fname).name}\n\n")
                    if isinstance(r, dict) and r.get("parse_error"):
                        f.write(f"```\n{r.get('raw', 'error')}\n```\n\n")
                    elif isinstance(r, str):
                        f.write(f"{r}\n\n")
                    else:
                        f.write(f"{json.dumps(r, ensure_ascii=False, indent=2)}\n\n")
                    f.write("---\n\n")
            print(f"저장: {output_base}.md")


def cmd_status(args):
    """배치 상태 확인"""
    client = get_client()
    job = client.batches.get(name=args.job)
    state = job.state.name if hasattr(job.state, 'name') else str(job.state)
    print(f"이름: {job.name}")
    print(f"상태: {state}")
    if hasattr(job, 'display_name'):
        print(f"표시명: {job.display_name}")
    if state == "JOB_STATE_SUCCEEDED" and args.download:
        if job.dest and job.dest.inlined_responses:
            results = collect_inline_results(job)
        elif job.dest and job.dest.file_name:
            results = collect_file_results(client, job)
        else:
            results = []
        if results:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_base = args.output or f"_ai/logs/gm/{ts}_download"
            os.makedirs(os.path.dirname(output_base), exist_ok=True)
            save_results(results, output_base)


def cmd_list(args):
    """배치 목록"""
    client = get_client()
    jobs = client.batches.list(config={"page_size": args.limit or 10})
    for job in jobs:
        state = job.state.name if hasattr(job.state, 'name') else str(job.state)
        name = getattr(job, 'display_name', '')
        print(f"  {job.name}  [{state}]  {name}")


def cmd_cancel(args):
    """배치 취소"""
    client = get_client()
    client.batches.cancel(name=args.job)
    print(f"취소됨: {args.job}")


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(description="gm_batch — Gemini Batch API 래퍼")
    parser.add_argument("--model", "-m", default=None, help="모델 (기본: gemini-3-flash-preview)")
    parser.add_argument("--poll-interval", type=int, default=10, help="폴링 간격(초)")
    parser.add_argument("--no-wait", action="store_true", help="제출만 하고 폴링 안 함")
    parser.add_argument("--output", "-o", default=None, help="출력 경로 (확장자 제외)")

    sub = parser.add_subparsers(dest="command")

    # guardian
    p_guard = sub.add_parser("guardian", help="감시단 하위직원 배치 실행")
    p_guard.add_argument("--target", "-t", nargs="+", required=True, help="검사 대상 파일")
    p_guard.add_argument("--guardians", "-g", nargs="+", help="실행할 감시단 (G1 G2 G3 ...)")
    p_guard.add_argument("--mode", choices=["light", "default", "full"], default="default", help="경량/기본/전체")
    p_guard.add_argument("--anchor", "-a", help="ANCHOR 문서 경로 (G2 참조용)")

    # review
    p_review = sub.add_parser("review", help="논문/코드 리뷰 배치")
    p_review.add_argument("--input", "-i", required=True, help="리뷰 대상 파일")
    p_review.add_argument("--preset", "-p", choices=list(REVIEWER_PRESETS.keys()), default="general", help="리뷰어 프리셋")
    p_review.add_argument("--reviewers", "-n", type=int, help="리뷰어 수 제한")
    p_review.add_argument("--add-reviewer", action="append", help="커스텀 리뷰어 추가 (이름:지시문)")

    # batch
    p_batch = sub.add_parser("batch", help="JSONL 파일 배치 제출")
    p_batch.add_argument("--jsonl", "-j", required=True, help="JSONL 파일 경로")

    # inline
    p_inline = sub.add_parser("inline", help="인라인 다중 프롬프트")
    p_inline.add_argument("--prompts", nargs="+", required=True, help="프롬프트 목록")

    # summarize
    p_summ = sub.add_parser("summarize", help="파일 목록 요약")
    p_summ.add_argument("--files", "-f", nargs="+", required=True, help="파일 경로 목록")

    # status
    p_status = sub.add_parser("status", help="배치 상태 확인")
    p_status.add_argument("--job", "-j", required=True, help="배치 이름 (batches/...)")
    p_status.add_argument("--download", "-d", action="store_true", help="완료 시 결과 다운로드")

    # list
    p_list = sub.add_parser("list", help="배치 목록")
    p_list.add_argument("--limit", "-l", type=int, default=10)

    # cancel
    p_cancel = sub.add_parser("cancel", help="배치 취소")
    p_cancel.add_argument("--job", "-j", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "guardian": cmd_guardian,
        "review": cmd_review,
        "batch": cmd_batch,
        "inline": cmd_inline,
        "summarize": cmd_summarize,
        "status": cmd_status,
        "list": cmd_list,
        "cancel": cmd_cancel,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
