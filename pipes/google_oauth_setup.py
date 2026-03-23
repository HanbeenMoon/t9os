"""Google OAuth2 스코프 재설정 — Drive + Calendar 통합 토큰 발급.

기존 refresh token이 Calendar 스코프만 포함하여 Drive API 403 발생 시,
이 스크립트로 Drive + Calendar 스코프를 모두 포함한 새 refresh token을 발급받는다.

Usage:
    python3 T9OS/pipes/google_oauth_setup.py
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


def main() -> int:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("ERROR: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 미설정")
        return 1

    # 1) Authorization URL 생성
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
    print("Google OAuth2 스코프 재설정")
    print(f"스코프: {', '.join(SCOPES)}")
    print("=" * 60)
    print()
    print("아래 URL을 브라우저에서 열어 인증하세요:")
    print()
    print(auth_url)
    print()

    # 2) Authorization code 입력
    code = input("인증 후 받은 authorization code를 입력: ").strip()
    if not code:
        print("ERROR: code가 비어있음")
        return 1

    # 3) Code → refresh token 교환
    data = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
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
        print(f"ERROR: refresh_token이 응답에 없음. 응답: {json.dumps(body, indent=2)}")
        return 1

    print()
    print("=" * 60)
    print("새 refresh token 발급 완료")
    print(f"스코프: {scope}")
    print("=" * 60)
    print()
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    print()
    print("위 값을 _keys/.env.txt의 GOOGLE_REFRESH_TOKEN에 업데이트하세요.")

    # 검증: access token으로 Drive API 접근 테스트
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
