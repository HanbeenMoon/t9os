#!/usr/bin/env python3
"""
T9 OS Intent Parser v0.1
BIBLE.md + L2_interpretation.md 5축 해석 체계 구현.

규칙 기반. 외부 LLM API 호출 없음. stdlib만 사용.
t9_seed.py의 DB를 활용해 과거 엔티티 검색.

Usage:
    python3 T9OS/pipes/intent_parser.py "SSK 논문 5장 분석결과 표 다시 만들어야해 급해"
    python3 T9OS/pipes/intent_parser.py --json "ODNAR MVP 배포"
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---- 경로 ----------------------------------------------------------------
# 하드코딩 없이: 이 파일 위치 기준으로 T9OS 루트를 동적 탐색
# intent_parser.py 는 T9OS/pipes/ 에 위치 → 2단계 상위가 T9OS 루트
_THIS_FILE = Path(__file__).resolve()
T9 = _THIS_FILE.parent.parent          # T9OS/
HANBEEN = T9.parent                   # HANBEEN/
DB_PATH = T9 / ".t9.db"

# ---- 데이터 클래스 --------------------------------------------------------


@dataclass
class Plan:
    id: str            # A / B / C
    name: str          # "즉시 실행"
    steps: list[str]
    time_est: str      # "30분"
    tool: str          # cc / cx / gm / cc+cx
    strategy: str      # search / reuse / buy / build


@dataclass
class ParsedIntent:
    raw: str
    intent: str                        # create/explore/solve/earn/express/become
    state: str                         # 탐색/실행/보류
    resources: list[str]               # 필요한 자원
    constraints: list[str]             # 마감/예산/체력 등
    artifact: str                      # 예상 산출물 유형
    urgency: str                       # high/mid/low
    project: str                       # SSK/ODNAR/T9/...
    disparation: Optional[dict] = None # {"dim_a": ..., "dim_b": ...}
    confidence: float = 0.0            # 해석 신뢰도 0~1
    plans: list[Plan] = field(default_factory=list)
    similar_entities: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["plans"] = [asdict(p) for p in self.plans]
        return d

    def pretty(self) -> str:
        R, J = lambda v: ', '.join(v) or '(없음)', "\n"
        axes = [f"  Intent: {self.intent}", f"  State: {self.state}",
                f"  Resource: {R(self.resources)}", f"  Constraint: {R(self.constraints)}",
                f"  Artifact: {self.artifact}", f"  Urgency: {self.urgency}",
                f"  Project: {self.project}", f"  Confidence: {self.confidence:.0%}"]
        if self.disparation:
            axes.append(f"  Disparation: {self.disparation['dim_a']} vs {self.disparation['dim_b']}")
        if self.similar_entities:
            axes.append(f"  Similar: {len(self.similar_entities)}건 (DB)")
            axes.extend(f"    [{e['id']:3d}] {e['phase'][:12]:12s} | {e['filename'][:50]}"
                        for e in self.similar_entities[:3])
        if self.plans:
            axes.append("")
            for p in self.plans:
                axes.append(f"  Plan {p.id}: {p.name} ({p.time_est}, {p.tool}) [{p.strategy}]")
                axes.extend(f"    {s}" for s in p.steps)
        return J.join(axes)


# ---- 키워드 사전 (압축 형식: "kw1 kw2 kw3".split()) ----------------------

def _s(s: str) -> list[str]:
    return s.split()

# 의도(Intent) — t9_seed.py CONCEPT_KW 확장
INTENT_KW = {
    "create":  _s("만들 구현 개발 build create 코딩 작성 생성 설계 구축 세팅 셋업 setup deploy 배포 초안 변환 자동화 파이프 스크립트"),
    "explore": _s("조사 탐색 리서치 explore research 분석 검색 찾아 알아 확인 비교 검토 살펴 파악 읽어"),
    "solve":   _s("해결 수정 fix solve 버그 오류 debug 고치 에러 복구 패치 hotfix 문제 안됨 안돼 깨짐"),
    "earn":    _s("수익 돈 earn 매출 사업 투자 지원금 펀딩 예창패 공모 대회 상금"),
    "express": _s("발표 쓰기 express 글 에세이 보고서 논문 PPT 슬라이드 정리 요약 문서화"),
    "become":  _s("공부 배우 become 성장 학습 연습 트레이닝 스터디 강의 수업 과제"),
}
_INTENT_WEIGHT = {"create": 1.0, "solve": 1.0, "explore": 0.8, "express": 0.9, "earn": 0.7, "become": 0.6}

# 상태(State)
STATE_KW = {
    "실행": _s("해줘 해 만들어 시작 바로 지금 급해 실행 돌려 빌드 배포 커밋 push run"),
    "탐색": _s("알아봐 찾아봐 비교 검토 살펴 조사 어떻게 가능한가 방법 뭐가 어떤"),
    "보류": _s("나중에 언젠가 일단 보류 홀드 someday 기록 메모 저장"),
}

# 자원(Resource)
RESOURCE_KW = {
    "시간": _s("시간 분 hour min 오늘 내일 이번주"),
    "토큰": _s("토큰 token API 호출"),  "돈": _s("원 달러 비용 결제 유료 무료 구독"),
    "파일": _s("파일 폴더 경로 데이터 CSV JSON xlsx PDF do파일 dta"),
    "사람": _s("동우 일두 석준 성호 워니 멘토 교수 팀원 조원"),
    "도구": _s("Stata Python Next.js Supabase Claude GPT Gemini Docker GitHub Notion 텔레그램"),
    "지식": _s("논문 레퍼런스 문서 매뉴얼 가이드"),
    "GPU":  _s("GPU CUDA RTX VRAM"),
}

# 제약(Constraint)
CONSTRAINT_KW = {
    "마감": _s("마감 데드라인 deadline D- 까지 제출 오늘까지 내일까지 이번주 시험 내일"),
    "예산": _s("돈없 예산 budget 무료만 비용제한"), "체력": _s("피곤 졸려 지침 새벽 야근"),
    "실력": _s("못해 모르 처음 입문 초보"), "접근권한": _s("권한 접근 인증 API키 비밀번호 ssh VPN"),
    "용량": _s("용량 디스크 storage 메모리 RAM"),
}

# 산출물(Artifact)
ARTIFACT_KW = {
    "코드": _s("코드 스크립트 함수 클래스 모듈 do파일 py ts js"),
    "문서": _s("문서 보고서 레포트 report md docx 요약"),
    "표":   _s("표 테이블 table 결과표 통계표"),
    "시각화": _s("그래프 차트 plot 시각화 그림 figure"),
    "설계안": _s("설계 아키텍처 구조 명세 spec blueprint"),
    "데이터": _s("데이터 dataset CSV JSON dta DB"),
    "PPT":  _s("PPT 슬라이드 발표자료 프레젠테이션"),
    "웹":   _s("페이지 UI 화면 랜딩 대시보드"),
}

# 프로젝트 (CLAUDE.md 기반)
PROJECT_KW = {
    "SSK":   _s("SSK 논문 특허 임금 패널 Stata 산업 학부연구 MDIS 계량 동우 일두 RA"),
    "ODNAR": _s("ODNAR 온톨로지 벡터 임베딩 Supabase 예창패 석준 MVP unknown"),
    "SC41":  _s("수업 과제 캔버스 Canvas 시험 성적 녹음 조별 4학년 학기"),
    "T9":    _s("T9 시몽동 개체화 오케스트레이션 헌법 BIBLE seed t9_seed 파이프라인"),
    "AT1":   _s("AT1 배틀 본선"), "TSUM": _s("TSUM 멘토 파인튜닝 LoRA FinBot 박성호 T-SUM"),
    "PM3":   _s("PM3 PMILL 학술"), "L2U": _s("L2U watcher 큐"),
    "T9D":   _s("T9D 대시보드 Dashboard Vercel"), "한민혁": _s("한민혁 스테이블코인 레퍼런스트리"),
}

# 긴급도
URGENCY_KW = {
    "high": _s("급 긴급 urgent asap 마감 오늘 당장 빨리 지금 바로 즉시 핫픽스 hotfix 장애"),
    "low":  _s("나중 천천히 여유 someday 시간되면 일단 언젠가 홀드"),
}

# 긴장(Disparation) 대립쌍 — L2 기반
OPPOSITION_PAIRS = [
    (_s("빠르 급 asap urgent 당장 지금"), _s("천천히 나중 여유 someday 장기"), "urgency_high", "urgency_low"),
    (_s("build 만들 구현 개발 직접"), _s("buy 구매 외주 서비스 기존"), "build", "buy"),
    (_s("단순 최소 간단 MVP"), _s("복잡 완벽 정교 풀스택"), "simplicity", "complexity"),
    (_s("혼자 단독 내가"), _s("협업 팀 같이 분배"), "solo", "collaboration"),
    (_s("탐색 조사 리서치"), _s("실행 배포 커밋 해줘"), "exploration", "execution"),
]

# 에이전트 배정
AGENT_RULES = {
    "SSK": "cc", "ODNAR": "cc+cx", "SC41": "cx", "T9": "cc",
    "AT1": "cc", "TSUM": "cx",
}


# ---- IntentParser ---------------------------------------------------------

class IntentParser:
    """자연어 입력을 5축으로 분석하고 실행 계획을 제안."""

    def __init__(self):
        self._db_conn: Optional[sqlite3.Connection] = None

    def _get_db(self) -> Optional[sqlite3.Connection]:
        """t9_seed.py DB에 연결. 없으면 None."""
        if self._db_conn is not None:
            return self._db_conn
        if not DB_PATH.exists():
            return None
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            self._db_conn = conn
            return conn
        except Exception:
            return None

    def close(self):
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    # ---- 5축 해석 ----------------------------------------------------------

    def _detect_intent(self, text: str) -> tuple[str, float]:
        """의도 감지. (intent, confidence) 반환."""
        tl = text.lower()
        scores: dict[str, float] = {}

        for intent, keywords in INTENT_KW.items():
            score = 0.0
            weight = _INTENT_WEIGHT.get(intent, 0.8)
            for kw in keywords:
                pos = tl.find(kw.lower())
                if pos != -1:
                    # 앞쪽일수록 높은 점수 (위치 보너스)
                    position_bonus = max(0, 1.0 - pos / max(len(tl), 1))
                    score += weight * (1.0 + position_bonus * 0.5)
            scores[intent] = score

        if not any(scores.values()):
            return "explore", 0.3  # 기본값: 탐색

        best = max(scores, key=lambda k: scores[k])
        total = sum(scores.values())
        confidence = scores[best] / total if total > 0 else 0.5
        return best, min(confidence, 1.0)

    def _detect_state(self, text: str) -> str:
        """상태 감지: 탐색/실행/보류."""
        tl = text.lower()
        state_scores: dict[str, int] = {"실행": 0, "탐색": 0, "보류": 0}

        # 짧은 단어(≤2자)는 공백/문장끝/문두로 격리해 substring 오매칭 방지.
        # 예: "해"가 "뭐해" 안에서 오매칭되는 문제 차단.
        def _match_kw(kw: str, text_lower: str) -> bool:
            if len(kw) <= 2:
                return bool(re.search(r'(?<=[^가-힣a-z])' + re.escape(kw) + r'(?=[^가-힣a-z]|$)',
                                      ' ' + text_lower + ' '))
            return kw in text_lower

        for state, keywords in STATE_KW.items():
            for kw in keywords:
                if _match_kw(kw.lower(), tl):
                    state_scores[state] += 1

        best = max(state_scores, key=lambda k: state_scores[k])
        if state_scores[best] == 0:
            return "탐색"  # 기본값
        return best

    @staticmethod
    def _match_any(tl: str, kw_dict: dict[str, list[str]]) -> list[str]:
        """키워드 사전에서 매칭된 카테고리 반환 (첫 매치만)."""
        return [cat for cat, kws in kw_dict.items() if any(k.lower() in tl for k in kws)]

    @staticmethod
    def _score_kw(tl: str, kw_dict: dict[str, list[str]], default: str = "") -> str:
        """키워드 사전에서 최고 점수 카테고리 반환."""
        scores = {cat: sum(1 for k in kws if k.lower() in tl) for cat, kws in kw_dict.items()}
        best = max(scores, key=lambda k: scores[k]) if scores else default
        return best if scores.get(best, 0) > 0 else default

    def _detect_resources(self, text: str) -> list[str]:
        return self._match_any(text.lower(), RESOURCE_KW)

    def _detect_constraints(self, text: str) -> list[str]:
        return self._match_any(text.lower(), CONSTRAINT_KW)

    def _detect_artifact(self, text: str) -> str:
        return self._score_kw(text.lower(), ARTIFACT_KW, "문서")

    def _detect_urgency(self, text: str) -> str:
        tl = text.lower()
        # 복합 urgency 규칙: 단일 키워드로 못 잡는 고긴급 패턴
        _compound_high = [
            ("내일", "시험"), ("내일", "제출"), ("내일", "마감"), ("내일", "발표"),
            ("오늘", "마감"), ("오늘", "시험"), ("오늘", "제출"),
        ]
        for pair in _compound_high:
            if all(k in tl for k in pair):
                return "high"

        for level, kws in URGENCY_KW.items():
            if any(k in tl for k in kws):
                return level
        return "mid"

    def _detect_project(self, text: str) -> str:
        return self._score_kw(text.lower(), PROJECT_KW, "(미분류)")

    def _detect_disparation(self, text: str) -> Optional[dict]:
        tl = text.lower()
        for kws_a, kws_b, la, lb in OPPOSITION_PAIRS:
            if any(k in tl for k in kws_a) and any(k in tl for k in kws_b):
                return {"dim_a": la, "dim_b": lb}
        return None

    # ---- DB 검색 -----------------------------------------------------------

    def _search_similar(self, text: str, project: str) -> list[dict]:
        """t9_seed.py DB에서 유사 엔티티 검색."""
        conn = self._get_db()
        if conn is None:
            return []

        results: list[dict] = []

        # 1) FTS 검색
        # 핵심 단어 추출 (2글자 이상 한글 단어 + 영문 단어)
        words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text)
        for word in words[:5]:  # 상위 5개만
            try:
                safe = '"' + word.replace('"', '') + '"'
                rows = conn.execute(
                    "SELECT e.id, e.filename, e.phase, e.filepath "
                    "FROM entities_fts f JOIN entities e ON f.rowid = e.id "
                    "WHERE entities_fts MATCH ? LIMIT 5", (safe,)
                ).fetchall()
                for r in rows:
                    entry = {"id": r["id"], "filename": r["filename"],
                             "phase": r["phase"], "filepath": r["filepath"]}
                    if entry not in results:
                        results.append(entry)
            except Exception:
                pass

        # 2) 프로젝트 키워드 LIKE 검색 (FTS 결과 부족 시)
        if len(results) < 3 and project != "(미분류)":
            for kw in PROJECT_KW.get(project, [])[:3]:
                try:
                    rows = conn.execute(
                        "SELECT id, filename, phase, filepath FROM entities "
                        "WHERE (filename LIKE ? OR body_preview LIKE ?) "
                        "AND phase NOT IN ('dissolved') LIMIT 3",
                        (f"%{kw}%", f"%{kw}%")
                    ).fetchall()
                    for r in rows:
                        entry = {"id": r["id"], "filename": r["filename"],
                                 "phase": r["phase"], "filepath": r["filepath"]}
                        if entry not in results:
                            results.append(entry)
                except Exception:
                    pass

        return results[:8]  # 최대 8건

    # ---- 계획 제안 ----------------------------------------------------------

    def suggest_plan(self, parsed: ParsedIntent) -> list[Plan]:
        """Search -> Reuse -> Buy -> Build 순서로 계획 제안."""
        P, tool = Plan, AGENT_RULES.get(parsed.project, "cc")
        plans: list[Plan] = []

        # Plan A: Search (항상)
        n = len(parsed.similar_entities)
        plans.append(P("A", f"Search -- 기존 자원 {'재활용' if n else '탐색'}",
            [f"1. DB 유사 엔티티 {n}건 확인", "2. 관련 파일 열어서 복사/수정", "3. 산출물 확인 후 완료"]
            if n else ["1. grep/t9_seed search로 검색", "2. _ai/logs/ 과거 로그 확인", "3. 발견 시 재활용, 없으면 Plan B"],
            "15분" if n else "10분", tool if n else "cc", "search"))

        # Plan B: 핵심 실행 (urgency + intent 기반)
        _B = {  # intent -> (name, steps, time, tool_override, strategy)
            "_high":  ("즉시 실행 -- 최소 경로",
                       ["1. 핵심 산출물만 30분 내 완성", f"2. {tool}가 직접 실행", "3. 검증 최소화, 사후 보완"],
                       "30분", tool, "build"),
            "explore": ("탐색-학습 루프",
                        ["1. gm 병렬로 3가지 소스 수집", "2. 핵심 인사이트 추출 (cc)", "3. 적용 가능 패턴 도출"],
                        "1.5시간", "gm+cc", "buy"),
            "become": ("탐색-학습 루프",
                       ["1. gm 병렬로 3가지 소스 수집", "2. 핵심 인사이트 추출 (cc)", "3. 적용 가능 패턴 도출"],
                       "1.5시간", "gm+cc", "buy"),
            "solve":  ("디버깅 -- 원인 추적 후 수정",
                       ["1. 에러/증상 재현 확인", "2. 원인 추적 (로그/코드 분석)", f"3. {tool}가 수정 및 검증"],
                       "45분", tool, "build"),
            "create": ("분할 병렬 실행",
                       ["1. 하위 작업 분할", "2. cc/cx 병렬 배분", "3. 통합 및 검증"],
                       "1시간", "cc+cx", "build"),
            "express": ("문서 작성 -- 구조 선행",
                        ["1. 목차/구조 설계 (cc)", f"2. 본문 작성 (cx, {parsed.artifact})", "3. 검토 및 포맷팅"],
                        "1시간", "cc+cx", "build"),
            "earn":   ("ROI 우선 실행",
                       ["1. 비용 대비 효과 산정", "2. 최소 투입 방안 선택", "3. 빠른 검증 후 확정"],
                       "45분", "cc", "buy"),
        }
        key = "_high" if parsed.urgency == "high" else parsed.intent
        name, steps, t, tl, strat = _B.get(key, ("표준 실행",
            ["1. 요구사항 정리", f"2. {tool}가 실행", "3. 산출물 확인"], "1시간", tool, "build"))
        plans.append(P("B", name, steps, t, tl, strat))

        # Plan C: 긴장 해소 또는 Buy-first
        if parsed.disparation:
            da, db = parsed.disparation["dim_a"], parsed.disparation["dim_b"]
            plans.append(P("C", f"긴장 해소 -- {da} vs {db}",
                [f"1. {da} 측면 요구사항 정리", f"2. {db} 측면 요구사항 정리",
                 "3. 양립 가능한 해결책 도출 (transduction)"], "1시간", "cc", "build"))
        else:
            plans.append(P("C", "Buy-first -- 외부 도구 탐색",
                ["1. 기존 서비스/도구 3개 검색 (gm)", "2. 비용 효과 평가", "3. 선택 및 적용"],
                "45분", "gm", "buy"))
        return plans

    # ---- 메인 파서 ----------------------------------------------------------

    def parse(self, text: str) -> ParsedIntent:
        """자연어 입력을 5축으로 분석."""
        intent, confidence = self._detect_intent(text)
        state = self._detect_state(text)
        resources = self._detect_resources(text)
        constraints = self._detect_constraints(text)
        artifact = self._detect_artifact(text)
        urgency = self._detect_urgency(text)
        project = self._detect_project(text)
        disparation = self._detect_disparation(text)

        # 상태 보정: urgency=high이면 실행으로 강제
        if urgency == "high" and state != "실행":
            state = "실행"

        # 신뢰도 보정
        # 프로젝트 특정 + 산출물 특정 + 의도 명확 -> 높음
        if project != "(미분류)":
            confidence = min(confidence + 0.15, 1.0)
        if artifact != "문서":  # 기본값이 아닌 경우
            confidence = min(confidence + 0.1, 1.0)

        # DB에서 유사 엔티티 검색
        similar = self._search_similar(text, project)

        parsed = ParsedIntent(
            raw=text,
            intent=intent,
            state=state,
            resources=resources,
            constraints=constraints,
            artifact=artifact,
            urgency=urgency,
            project=project,
            disparation=disparation,
            confidence=confidence,
            similar_entities=similar,
        )

        # 계획 제안
        parsed.plans = self.suggest_plan(parsed)

        return parsed


# ---- t9_seed.py 통합 함수 --------------------------------------------------

def parse_for_compose(text: str) -> tuple[ParsedIntent, list[dict]]:
    """t9_seed.py cmd_compose()에서 호출할 수 있는 래퍼.
    (ParsedIntent, plans_as_dicts) 반환.

    Usage in t9_seed.py:
        from pipes.intent_parser import parse_for_compose
        parsed, plans = parse_for_compose(text)
    """
    parser = IntentParser()
    parsed = parser.parse(text)
    parser.close()

    plans_dicts = []
    for p in parsed.plans:
        plans_dicts.append({
            "id": p.id,
            "name": p.name,
            "steps": p.steps,
            "time": p.time_est,
            "tool": p.tool,
            "strategy": p.strategy,
        })
    return parsed, plans_dicts


# ---- CLI ------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    json_mode = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]
    text = " ".join(args)

    if not text.strip():
        print("  입력이 비어 있습니다.")
        return

    parser = IntentParser()
    result = parser.parse(text)
    parser.close()

    if json_mode:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"\n  === T9 Intent Parser v0.1 ===")
        print(f"  Input: {text}\n")
        print(result.pretty())
        print()


if __name__ == "__main__":
    main()
