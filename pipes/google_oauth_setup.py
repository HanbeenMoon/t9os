"""Google OAuth2 스코프 재설정 — 전체 권한 통합 토큰 발급.

localhost 리다이렉트 방식. 브라우저 인증 → 자동 코드 수신 → 토큰 발급.

Usage:
    python3 T9OS/pipes/google_oauth_setup.py
"""

from __future__ import annotations

import http.server
import json
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",           # 전체 Drive (파일+댓글+공유문서)
    "https://www.googleapis.com/auth/documents",       # Google Docs
    "https://www.googleapis.com/auth/spreadsheets",    # Google Sheets
    "https://www.googleapis.com/auth/presentations",   # Google Slides
    "https://www.googleapis.com/auth/gmail.modify",    # Gmail 읽기+보내기
    "https://www.googleapis.com/auth/tasks",           # Google Tasks
    "https://www.googleapis.com/auth/contacts.readonly",  # 연락처 조회
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8085
REDIRECT_URI = f"http://localhost:{PORT}"

# 콜백으로 받은 코드 저장
_auth_code: str | None = None
_auth_error: str | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """OAuth2 콜백 수신 핸들러."""

    def do_GET(self):
        global _auth_code, _auth_error
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if "code" in qs:
            _auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>OK</h1><p>Google OAuth2 complete. Close this tab.</p>")
        else:
            _auth_error = qs.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h1>Error: {_auth_error}</h1>".encode())

    def log_message(self, format, *args):
        pass  # suppress logs


def main() -> int:
    global _auth_code, _auth_error

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 미설정")
        return 1

    # 1) 로컬 서버 시작
    server = http.server.HTTPServer(("127.0.0.1", PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    # 2) 인증 URL 생성 + 브라우저 오픈
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"{AUTH_URL}?{params}"

    print("=" * 60)
    print("Google OAuth2 — 전체 권한 재설정")
    print(f"스코프: {len(SCOPES)}개")
    for s in SCOPES:
        print(f"  - {s.split('/')[-1]}")
    print("=" * 60)
    print()
    print("브라우저가 자동으로 열립니다. 안 열리면 아래 URL 복붙:")
    print()
    print(auth_url)
    print()

    webbrowser.open(auth_url)

    # 3) 콜백 대기
    print("인증 대기 중...")
    thread.join(timeout=120)
    server.server_close()

    if _auth_error:
        print(f"ERROR: 인증 실패 — {_auth_error}")
        return 1
    if not _auth_code:
        print("ERROR: 타임아웃 (2분). 다시 실행해주세요.")
        return 1

    print("인증 코드 수신 완료!")

    # 4) Code → refresh token 교환
    data = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": _auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"ERROR: HTTP {e.code}: {err_body[:500]}")
        return 1

    refresh_token = body.get("refresh_token")
    access_token = body.get("access_token")
    scope = body.get("scope", "")

    if not refresh_token:
        print(f"ERROR: refresh_token 없음. 응답: {json.dumps(body, indent=2)}")
        return 1

    print()
    print("=" * 60)
    print("새 refresh token 발급 완료!")
    print(f"스코프: {scope}")
    print("=" * 60)
    print()
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    print()
    print("위 값을 _keys/.env.sh의 GOOGLE_REFRESH_TOKEN에 업데이트하세요.")

    # 검증
    if access_token:
        print()
        print("Drive API 접근 테스트 중...")
        test_req = urllib.request.Request(
            "https://www.googleapis.com/drive/v3/about?fields=user",
            method="GET",
        )
        test_req.add_header("Authorization", f"Bearer {access_token}")
        try:
            with urllib.request.urlopen(test_req, timeout=10) as resp:
                user_info = json.loads(resp.read().decode())
                email = user_info.get("user", {}).get("emailAddress", "?")
                print(f"Drive API OK — 계정: {email}")
        except Exception as e:
            print(f"Drive API 테스트 실패: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
