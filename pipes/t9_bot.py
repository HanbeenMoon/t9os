#!/usr/bin/env python3
"""t9tb — T9 Telegram Bot. WSLpolling execution.
T9 OSinterface."""
import subprocess, time, sys, os, signal, shlex
from pathlib import Path
from datetime import datetime

# common moduleTelegram function
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_common import tg_send, tg_updates, tg_download_file, CHAT_ID, T9, HANBEEN

PIDFILE = T9 / ".t9bot.pid"
LOCKFILE = T9 / ".t9bot.lock"


def acquire_lock():
    """instance . PID file (NTFSfcntl )."""
    if PIDFILE.exists():
        old_pid = PIDFILE.read_text().strip()
        try:
            os.kill(int(old_pid), 0)  # process check
            print(f"[t9tb] execution (PID {old_pid}). end.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass  # PID —
    PIDFILE.write_text(str(os.getpid()))
    return None


def run_t9(cmd):
    """T9 Seed command execution"""
    try:
        r = subprocess.run(
            ["python3", str(T9 / "t9_seed.py")] + shlex.split(cmd),
            capture_output=True, text=True, timeout=30, cwd=str(HANBEEN)
        )
        return (r.stdout + r.stderr).strip() or "(output not found)"
    except subprocess.TimeoutExpired:
        return "[timeout] 30 "
    except Exception as e:
        return f"[] {e}"


def run_cc(question):
    """Claude Code(non-interactive)"""
    try:
        r = subprocess.run(
            ["claude", "-p", question],
            capture_output=True, text=True, timeout=300, cwd=str(HANBEEN)
        )
        return (r.stdout + r.stderr).strip()[:3500] or "(response not found)"
    except subprocess.TimeoutExpired:
        return "[timeout] 5 "
    except FileNotFoundError:
        return "[] claude CLI "
    except Exception as e:
        return f"[] {e}"


def run_brief():
    """CEO brief execution"""
    try:
        from t9_ceo_brief import build_brief
        brief = build_brief()
        return brief or "report  not found — "
    except Exception as e:
        return f"[] brief create failed: {e}"


def run_auto():
    """auto Individuating engine execution"""
    try:
        from t9_auto import run_auto as _run_auto
        report = _run_auto(dry_run=False)
        return (
            f"t9_auto completed\n"
            f"concepts: +{report['concepts_added']}\n"
            f"urgency: +{report['urgency_set']}\n"
            f"project: +{report['projects_set']}\n"
            f"transition: +{report['transitioned']}"
        )
    except Exception as e:
        return f"[] auto failed: {e}"


def handle_voice(file_id, chat_id):
    """voice/→ → Whisper transcription"""
    tg_send("  + transcription ...", chat_id)
    local_path = tg_download_file(file_id)
    if not local_path:
        return " failed"
    try:
        r = subprocess.run(
            ["python3", str(T9 / "pipes" / "whisper_pipeline.py"), "transcribe", str(local_path)],
            capture_output=True, text=True, timeout=600, cwd=str(HANBEEN)
        )
        output = (r.stdout + r.stderr).strip()
        transcripts_dir = T9 / "artifacts" / "transcripts"
        latest = sorted(transcripts_dir.glob("*.md"), key=lambda f: f.stat().st_mtime)
        if latest:
            content = latest[-1].read_text(encoding="utf-8", errors="replace")
            if "---" in content:
                parts = content.split("---", 2)
                body = parts[2].strip() if len(parts) > 2 else content
            else:
                body = content
            return f"transcription completed ({latest[-1].name})\n\n{body[:3000]}"
        return output[:3500] or "transcription completed (result file check)"
    except subprocess.TimeoutExpired:
        return "[timeout] 10 "
    except Exception as e:
        return f"[] {e}"


HELP_TEXT = """t9tb command:
/status — T9 OS /daily — brief
/brief — CEO brief ()
/deadline — deadline list
/auto — auto Individuating (Geminiclassify/)
/search <key> — search
/capture <content> — Preindividual save
/compose <content> — generate plans
/tidy — clean up execution
/ask <> — CCmessage → response inbox save (token 0)"""


def handle(text):
    """message """
    if text.startswith("/status"):
        return run_t9("status")
    elif text.startswith("/daily"):
        return run_t9("daily")
    elif text.startswith("/brief"):
        return run_brief()
    elif text.startswith("/deadline"):
        return run_t9("daily")  # dailydeadline
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
        # default : response inbox save (token 0, CC call not found)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = text[:20].replace(" ", "_").replace("/", "_").replace("\n", "_")
        filename = f"{ts}_{slug}.md"
        inbox = T9 / "field" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        filepath = inbox / filename
        filepath.write_text(f"# {text[:50]}\n\n{text}\n\n---\n*via t9tb {ts}*\n", encoding="utf-8")
        return None  # None = response


def main():
    lock_fd = acquire_lock()
    print(f"t9tb start (PID {os.getpid()})")
    print(f"T9: {T9}")
    tg_send("t9tb ")

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

                # voice/→ auto transcription
                if msg.get("voice") or msg.get("audio"):
                    file_id = (msg.get("voice") or msg.get("audio"))["file_id"]
                    result = handle_voice(file_id, chat_id)
                    tg_send(result, chat_id)
                    continue

                if not text:
                    continue

                print(f"[{time.strftime('%H:%M:%S')}] {text[:50]}")

                result = handle(text)
                if result is not None:  # Noneresponse (inbox save)
                    tg_send(result, chat_id)
        except KeyboardInterrupt:
            tg_send("t9tb end")
            print("end")
            break
        except Exception as e:
            print(f"[] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
