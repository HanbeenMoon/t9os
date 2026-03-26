"""Google OAuth2 config — total permission Integrate token .

localhost . auth → auto → token .

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
    "https://www.googleapis.com/auth/drive",           # total Drive (file++)
    "https://www.googleapis.com/auth/documents",       # Google Docs
    "https://www.googleapis.com/auth/spreadsheets",    # Google Sheets
    "https://www.googleapis.com/auth/presentations",   # Google Slides
    "https://www.googleapis.com/auth/gmail.modify",    # Gmail +
    "https://www.googleapis.com/auth/tasks",           # Google Tasks
    "https://www.googleapis.com/auth/contacts.readonly",  # query
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8085
REDIRECT_URI = f"http://localhost:{PORT}"

# callbacksave
_auth_code: str | None = None
_auth_error: str | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """OAuth2 callback handler."""

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
        print("ERROR: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET config")
        return 1

    # 1) start
    server = http.server.HTTPServer(("127.0.0.1", PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    # 2) auth URL create +
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
    print("Google OAuth2 — total permission config")
    print(f": {len(SCOPES)}")
    for s in SCOPES:
        print(f"  - {s.split('/')[-1]}")
    print("=" * 60)
    print()
    print("auto. URL :")
    print()
    print(auth_url)
    print()

    webbrowser.open(auth_url)

    # 3) callback
    print("auth waiting...")
    thread.join(timeout=120)
    server.server_close()

    if _auth_error:
        print(f"ERROR: auth failed — {_auth_error}")
        return 1
    if not _auth_code:
        print("ERROR: timeout (2). execution.")
        return 1

    print("auth completed!")

    # 4) Code → refresh token
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
        print(f"ERROR: refresh_token not found. response: {json.dumps(body, indent=2)}")
        return 1

    print()
    print("=" * 60)
    print("refresh token completed!")
    print(f": {scope}")
    print("=" * 60)
    print()
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    print()
    print("value_keys/.env.shGOOGLE_REFRESH_TOKEN.")

    # verification
    if access_token:
        print()
        print("Drive API access test ...")
        test_req = urllib.request.Request(
            "https://www.googleapis.com/drive/v3/about?fields=user",
            method="GET",
        )
        test_req.add_header("Authorization", f"Bearer {access_token}")
        try:
            with urllib.request.urlopen(test_req, timeout=10) as resp:
                user_info = json.loads(resp.read().decode())
                email = user_info.get("user", {}).get("emailAddress", "?")
                print(f"Drive API OK — : {email}")
        except Exception as e:
            print(f"Drive API test failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
