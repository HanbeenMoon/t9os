#!/usr/bin/env python3
"""T9 텔레그램 공통 모듈 — config.py에서 설정 로드."""
import json, urllib.request, urllib.parse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import TG_TOKEN, TG_CHAT, T9, HANBEEN

TOKEN = TG_TOKEN
CHAT_ID = TG_CHAT
API = f"https://api.telegram.org/bot{TOKEN}"


def tg_send(text, chat_id=None, parse_mode=None):
    """텔레그램 메시지 전송 (4096자 자동 분할)"""
    chat_id = chat_id or CHAT_ID
    if not TOKEN or not chat_id:
        print("[tg_send 실패] T9_TG_TOKEN 또는 T9_TG_CHAT 환경변수 없음")
        return
    for i in range(0, max(len(text), 1), 4000):
        chunk = text[i:i + 4000]
        params = {"chat_id": chat_id, "text": chunk}
        if parse_mode:
            params["parse_mode"] = parse_mode
        data = urllib.parse.urlencode(params).encode()
        try:
            urllib.request.urlopen(f"{API}/sendMessage", data, timeout=10)
        except Exception as e:
            print(f"[tg_send 실패] {e}")


def tg_updates(offset=0):
    """텔레그램 업데이트 (long polling)"""
    try:
        resp = urllib.request.urlopen(f"{API}/getUpdates?timeout=30&offset={offset}", timeout=35)
        return json.loads(resp.read())
    except Exception:
        return {"ok": False, "result": []}


def tg_download_file(file_id):
    """텔레그램 파일 다운로드 → 로컬 경로 반환"""
    from datetime import datetime
    try:
        resp = urllib.request.urlopen(f"{API}/getFile?file_id={file_id}", timeout=10)
        file_info = json.loads(resp.read())
        if not file_info.get("ok"):
            return None
        file_path = file_info["result"]["file_path"]
        ext = Path(file_path).suffix or ".ogg"
        local_name = f"{datetime.now():%Y%m%d_%H%M%S}_voice{ext}"
        rec_dir = HANBEEN / "PERSONAL" / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        local_path = rec_dir / local_name
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        urllib.request.urlretrieve(url, str(local_path))
        return local_path
    except Exception as e:
        print(f"[다운로드실패] {e}")
        return None
