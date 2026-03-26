#!/usr/bin/env python3
"""t9tb — T9 Telegram Bot. WSL에서 polling 방식으로 실행.
모바일에서 T9 OS를 제어하는 유일한 인터페이스."""
import subprocess, time, sys, os, signal, shlex
from pathlib import Path
from datetime import datetime

# 공통 모듈에서 텔레그램 함수 임포트
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send, tg_updates, tg_download_file, CHAT_ID, T9, HANBEEN

PIDFILE = T9 / ".t9bot.pid"
LOCKFILE = T9 / ".t9bot.lock"


def acquire_lock():
    """단일 인스턴스 보장. PID 파일 기반 (NTFS에서 fcntl 불가)."""
    if PIDFILE.exists():
        old_pid = PIDFILE.read_text().strip()
        try:
            os.kill(int(old_pid), 0)  # 프로세스 존재 확인
            print(f"[t9tb] 이미 실행 중 (PID {old_pid}). 종료.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass  # 죽은 PID — 계속 진행
    PIDFILE.write_text(str(os.getpid()))
    return None


def run_t9(cmd):
    """T9 Seed 명령 실행"""
    try:
        r = subprocess.run(
            ["python3", str(T9 / "t9_seed.py")] + shlex.split(cmd),
            capture_output=True, text=True, timeout=30, cwd=str(HANBEEN)
        )
        return (r.stdout + r.stderr).strip() or "(출력 없음)"
    except subprocess.TimeoutExpired:
        return "[타임아웃] 30초 초과"
    except Exception as e:
        return f"[에러] {e}"


def run_cc(question):
    """Claude Code에게 질문 (non-interactive)"""
    try:
        r = subprocess.run(
            ["claude", "-p", question],
            capture_output=True, text=True, timeout=300, cwd=str(HANBEEN)
        )
        return (r.stdout + r.stderr).strip()[:3500] or "(응답 없음)"
    except subprocess.TimeoutExpired:
        return "[타임아웃] 5분 초과"
    except FileNotFoundError:
        return "[에러] claude CLI 미설치"
    except Exception as e:
        return f"[에러] {e}"


def run_brief():
    """CEO brief 인라인 실행"""
    try:
        from t9_ceo_brief import build_brief
        brief = build_brief()
        return brief or "보고할 것 없음 — 평온"
    except Exception as e:
        return f"[에러] brief 생성 실패: {e}"


def run_auto():
    """자동 개체화 엔진 실행"""
    try:
        from t9_auto import run_auto as _run_auto
        report = _run_auto(dry_run=False)
        return (
            f"t9_auto 완료\n"
            f"concepts: +{report['concepts_added']}\n"
            f"urgency: +{report['urgency_set']}\n"
            f"project: +{report['projects_set']}\n"
            f"transition: +{report['transitioned']}"
        )
    except Exception as e:
        return f"[에러] auto 실패: {e}"


def handle_file(msg, chat_id):
    """문서/사진/비디오/파일 → 다운로드 → field/inbox/ 저장 + t9_seed capture"""
    inbox = T9 / "field" / "inbox"
    doc = msg.get("document")
    photo_list = msg.get("photo")
    video = msg.get("video")
    caption = msg.get("caption", "")

    if doc:
        file_id = doc["file_id"]
        orig_name = doc.get("file_name", "unknown")
        file_size = doc.get("file_size", 0)
        prefix = Path(orig_name).stem
    elif photo_list:
        file_id = photo_list[-1]["file_id"]
        orig_name = "photo.jpg"
        file_size = photo_list[-1].get("file_size", 0)
        prefix = "photo"
    elif video:
        file_id = video["file_id"]
        orig_name = video.get("file_name", "video.mp4")
        file_size = video.get("file_size", 0)
        prefix = Path(orig_name).stem
    else:
        return None

    # 20MB 제한 체크 (TG Bot API 제한)
    if file_size > 20 * 1024 * 1024:
        return f"파일 너무 큼 ({file_size // (1024*1024)}MB). Google Drive(G:)에 올려줘."

    size_str = f"{file_size // 1024}KB" if file_size < 1024 * 1024 else f"{file_size // (1024*1024)}MB"
    tg_send(f"파일 수신 중: {orig_name} ({size_str})", chat_id)
    local_path = tg_download_file(file_id, save_dir=str(inbox), filename_prefix=prefix)
    if not local_path:
        return "파일 다운로드 실패"

    # t9_seed capture로 등록 (shlex injection 방지: 리스트로 전달)
    desc = caption or f"TG 수신 파일: {orig_name}"
    try:
        subprocess.run(
            ["python3", str(T9 / "t9_seed.py"), "capture", f"{desc} — 파일: {local_path.name}"],
            capture_output=True, text=True, timeout=30, cwd=str(HANBEEN)
        )
    except Exception:
        pass
    return f"저장 완료: {local_path.name} ({size_str})\n경로: {local_path}"


def handle_voice(file_id, chat_id):
    """음성/오디오 → 다운로드 → Whisper 전사 → inbox 저장 + DB 등록"""
    tg_send("녹음 다운로드 + 전사 중...", chat_id)
    local_path = tg_download_file(file_id)
    if not local_path:
        return "다운로드 실패"
    try:
        r = subprocess.run(
            ["python3", str(T9 / "pipes" / "whisper_pipeline.py"), "transcribe", str(local_path)],
            capture_output=True, text=True, timeout=600, cwd=str(HANBEEN)
        )
        output = (r.stdout + r.stderr).strip()
        transcripts_dir = T9 / "artifacts" / "transcripts"
        latest = sorted(transcripts_dir.glob("*.md"), key=lambda f: f.stat().st_mtime)
        if latest:
            transcript = latest[-1]
            content = transcript.read_text(encoding="utf-8", errors="replace")

            # inbox에 복사 (DB reindex 대상)
            inbox_copy = T9 / "field" / "inbox" / transcript.name
            if not inbox_copy.exists():
                inbox_copy.write_text(content, encoding="utf-8")

            # t9_seed capture로 DB 등록
            try:
                subprocess.run(
                    ["python3", str(T9 / "t9_seed.py"), "capture",
                     f"음성 전사 완료: {transcript.name}"],
                    capture_output=True, text=True, timeout=30, cwd=str(HANBEEN)
                )
            except Exception:
                pass

            if "---" in content:
                parts = content.split("---", 2)
                body = parts[2].strip() if len(parts) > 2 else content
            else:
                body = content
            return f"전사 완료 ✓ ({transcript.name})\n\n{body[:3000]}"
        return output[:3500] or "전사 완료 (결과 파일 확인)"
    except subprocess.TimeoutExpired:
        return "[타임아웃] 10분 초과"
    except Exception as e:
        return f"[에러] {e}"


HELP_TEXT = """t9tb 명령어:
/status — T9 OS 현황
/daily — 오늘 브리프
/brief — CEO 브리프 (행동 필요 사항만)
/deadline — 마감일 목록
/auto — 자동 개체화 (Gemini로 분류/태깅)
/search <키워드> — 엔티티 검색
/capture <내용> — 전개체 저장
/compose <내용> — 플랜 생성
/tidy — 정리 실행
/ask <질문> — CC에게 질문
그냥 메시지 → 무응답 inbox 저장 (토큰 0)"""


def handle(text):
    """메시지 라우팅"""
    if text.startswith("/status"):
        return run_t9("status")
    elif text.startswith("/daily"):
        return run_t9("daily")
    elif text.startswith("/brief"):
        return run_brief()
    elif text.startswith("/deadline"):
        return run_t9("daily")  # daily에 마감일 포함
    elif text.startswith("/search "):
        return run_t9(f"search {text[8:]}")
    elif text.startswith("/capture "):
        return run_t9(f"capture {text[9:]}")
    elif text.startswith("/compose "):
        return run_t9(f"compose {text[9:]}")
    elif text.startswith("/tidy"):
        return run_t9("tidy")
    elif text.startswith("/auto"):
        return run_auto()
    elif text.startswith("/help"):
        return HELP_TEXT
    elif text.startswith("/ask "):
        return run_cc(text[5:])
    else:
        # 기본 동작: capture로 전개체 저장 + 결과 회신
        result = run_t9(f"capture {text}")
        # 정제 결과에서 핵심만 추출해서 회신
        lines = (result or "").split("\n")
        reply_parts = []
        for l in lines:
            if "[마감 감지]" in l or "[정제]" in l:
                reply_parts.append(l.strip())
        if reply_parts:
            return "저장 ✓ " + " / ".join(reply_parts)
        return "저장 ✓"


def main():
    lock_fd = acquire_lock()
    print(f"t9tb 시작 (PID {os.getpid()})")
    print(f"T9: {T9}")
    tg_send("t9tb 가동")

    offset = 0
    while True:
        try:
            data = tg_updates(offset)
            if not data.get("ok"):
                time.sleep(5)
                continue
            for update in data["result"]:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()

                if chat_id != CHAT_ID:
                    continue

                # 문서/사진/비디오 → 자동 저장
                if msg.get("document") or msg.get("photo") or msg.get("video"):
                    result = handle_file(msg, chat_id)
                    if result:
                        tg_send(result, chat_id)
                    continue

                # 음성/오디오 → 자동 전사
                if msg.get("voice") or msg.get("audio"):
                    file_id = (msg.get("voice") or msg.get("audio"))["file_id"]
                    result = handle_voice(file_id, chat_id)
                    tg_send(result, chat_id)
                    continue

                if not text:
                    continue

                print(f"[{time.strftime('%H:%M:%S')}] {text[:50]}")

                result = handle(text)
                if result is not None:  # None이면 무응답 (inbox 저장)
                    tg_send(result, chat_id)
        except KeyboardInterrupt:
            tg_send("t9tb 종료")
            print("종료")
            break
        except Exception as e:
            print(f"[에러] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
