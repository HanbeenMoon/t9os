# T9 OS 퀵스타트 — 한빈 전용

> 마지막 업데이트: 2026-03-17

---

## 매일 아침 (30초)

```bash
cd ~/code/HANBEEN
t9 daily
```

→ 오늘 마감, 개인화된 브리프, 현황 한눈에 출력.

---

## 핵심 5가지 동작

### 1. 아이디어 포착
머릿속에 뭔가 떠올랐다. 일단 던진다.

```bash
t9 idea "ODNAR 온보딩 영상 만들어야 할 것 같음"
# (= python3 T9OS/t9_seed.py capture "...")
```

→ preindividual 상태로 저장됨. 잊어도 된다.

---

### 2. 작업으로 만들기
아이디어를 실제 할 일로 바꾸고 싶을 때.

```bash
t9 do "ODNAR 예창패 발표 슬라이드"
# (= python3 T9OS/t9_seed.py compose "...")
```

→ Plan A / B / C 3가지 나옴. 하나 고른다.

```bash
t9 approve <id> A
# (= python3 T9OS/t9_seed.py approve <id> A)
```

→ individuating 상태로 이동. 이제 진짜 작업.

---

### 3. 현황 확인

```bash
t9 status
# (= python3 T9OS/t9_seed.py status)
```

```
preindividual   278  (아직 판단 안 된 것들)
individuating     4  (지금 하고 있는 것)
stabilized        8  (완료)
tension_detected  1  (충돌/긴장 감지됨)
```

---

### 4. 검색

```bash
t9 search "SSK"
t9 search "예창패"
t9 legacy "스테이블코인"   # 옛날 노션 데이터까지 뒤짐
# (= python3 T9OS/t9_seed.py search / legacy "...")
```

---

### 5. 완료 처리

```bash
t9 done <id>              # stabilized로 전이
t9 go <id>                # individuating으로 전이 (재개)
# (= python3 T9OS/t9_seed.py transition <id> stabilized/individuating)

# 사유 첨부 시:
python3 T9OS/t9_seed.py transition <id> stabilized "발표 제출 완료"
```

---

## 텔레그램 (모바일)

@T9_hanbeen_bot 에게 그냥 말 걸면 됨.

| 입력 | 결과 |
|------|------|
| `/status` | 전체 현황 |
| `/daily` | 오늘 브리프 |
| `/search SSK` | SSK 관련 검색 |
| `/capture 아이디어 내용` | 전개체 저장 |
| `/ask SSK 논문 어디까지 됐어?` | CC가 답변 |
| 그냥 메시지 | CC가 자동 판단 처리 |

---

## 수업 녹음 전사

```bash
# 아이폰 녹음 → PERSONAL/recordings/ 복사 후:
python3 T9OS/pipes/whisper_pipeline.py transcribe ML_0316.m4a

# 자동 감시 모드 (파일 넣으면 알아서 전사):
python3 T9OS/pipes/whisper_pipeline.py watch
```

---

## FinBot (재무 AI)

```bash
cd /mnt/c/Users/winn/HANBEEN/_legacy/finbot-tsum
source .venv/bin/activate
python3 scripts/chat.py
```

```
질문> 삼성전자 최근 영업이익 분석해줘
질문> PER 기준으로 지금 저평가된 섹터는?
질문> exit
```

---

## T9 Dashboard

```
배포 후: https://t9-dashboard.vercel.app

로컬 실행:
cd ~/code/HANBEEN/PROJECTS/t9-dashboard
npm run dev
→ http://localhost:3000
```

---

## 자주 쓰는 명령어 한장 요약

| 상황 | 단축 명령어 | (전체 형태) |
|------|------------|-------------|
| 오늘 뭐해야 해? | `t9 daily` | `python3 T9OS/t9_seed.py daily` |
| 아이디어 메모 | `t9 idea "..."` | `python3 T9OS/t9_seed.py capture "..."` |
| 플랜 3개 뽑기 | `t9 do "..."` | `python3 T9OS/t9_seed.py compose "..."` |
| 플랜 승인 | `t9 approve <id> A` | `python3 T9OS/t9_seed.py approve <id> A` |
| 전체 현황 | `t9 status` | `python3 T9OS/t9_seed.py status` |
| 키워드 검색 | `t9 search "..."` | `python3 T9OS/t9_seed.py search "..."` |
| 완료 처리 | `t9 done <id>` | `python3 T9OS/t9_seed.py transition <id> stabilized` |
| 작업 재개 | `t9 go <id>` | `python3 T9OS/t9_seed.py transition <id> individuating` |
| 주간 회고 | `python3 T9OS/t9_seed.py reflect` | — |
| 엔티티 연결 | `python3 T9OS/t9_seed.py relate <id1> <id2>` | — |
| 이력 확인 | `python3 T9OS/t9_seed.py history <id>` | — |
| 오래된 데이터 검색 | `t9 legacy "..."` | `python3 T9OS/t9_seed.py legacy "..."` |
| 재무 AI | `cd _legacy/finbot-tsum && source .venv/bin/activate && python3 scripts/chat.py` | — |

> `t9` alias는 `.bashrc`에 등록됨: `alias t9="python3 ~/code/HANBEEN/T9OS/t9_seed.py"`

---

## 상태 흐름

```
preindividual      →  impulse, tension_detected, dissolved
impulse            →  tension_detected, preindividual, dissolved
tension_detected   →  candidate_generated, suspended, dissolved
candidate_generated→  individuating, suspended, dissolved
individuating      →  stabilized, split, merged, suspended, dissolved
stabilized         →  archived, split, merged, dissolved, suspended, reactivated
split/merged       →  preindividual, tension_detected, individuating, suspended
suspended          →  reactivated, archived, dissolved
archived           →  reactivated   ← dissolved 불가
reactivated        →  tension_detected
dissolved          →  (종단, 전이 없음)
```

> compose + approve 흐름: preindividual → (compose) → candidate_generated → (approve) → individuating

---

## cc (Claude Code) 쓸 때

```bash
cd ~/code/HANBEEN
claude  # 또는 cc
```

CLAUDE.md 자동 로딩됨. 아무거나 던지면 됨.

---

## 긴급 상황

```bash
# DB 날아갔을 때
python3 T9OS/t9_seed.py reindex

# 뭔가 꼬였을 때
cat ~/code/HANBEEN/.claude/WORKING.md   # 마지막 작업 상태
cat ~/code/HANBEEN/T9OS/telos/GOALS.md  # 현재 목표
```
