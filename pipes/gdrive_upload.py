"""Google Drive file pipeline.

Usage:
    python3 T9OS/pipes/gdrive_upload.py "file1" "file2" --folder "2026"
    python3 T9OS/pipes/gdrive_upload.py report.pdf
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def _refresh_access_token() -> str:
    """Refresh token → access token."""
    data = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())

    if "access_token" not in body:
        raise RuntimeError(f"Token refresh failed: {body}")
    return body["access_token"]


def _find_folder(token: str, name: str) -> str | None:
    """nameDrive folder search. ID return."""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    params = urllib.parse.urlencode({"q": q, "fields": "files(id,name)", "pageSize": "1"})
    url = f"{DRIVE_FILES_URL}?{params}"

    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())

    files = body.get("files", [])
    return files[0]["id"] if files else None


def _create_folder(token: str, name: str) -> str:
    """Drive folder create, ID return."""
    metadata = json.dumps({
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }).encode()

    req = urllib.request.Request(DRIVE_FILES_URL, data=metadata, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())

    return body["id"]


def _upload_file(token: str, filepath: Path, folder_id: str | None = None) -> dict:
    """Multipart upload (metadata + content)."""
    mime_type = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
    file_content = filepath.read_bytes()

    metadata: dict = {"name": filepath.name}
    if folder_id:
        metadata["parents"] = [folder_id]
    metadata_json = json.dumps(metadata).encode()

    boundary = uuid.uuid4().hex
    sep = f"--{boundary}".encode()
    end = f"--{boundary}--".encode()

    body = b"\r\n".join([
        sep,
        b"Content-Type: application/json; charset=UTF-8\r\n",
        metadata_json,
        sep,
        f"Content-Type: {mime_type}\r\n".encode(),
        file_content,
        end,
    ])

    url = f"{DRIVE_UPLOAD_URL}?uploadType=multipart&fields=id,name,webViewLink"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/related; boundary={boundary}")

    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(description="Google Drive file ")
    parser.add_argument("files", nargs="+", help=" file path")
    parser.add_argument("--folder", help=" target folder name ( create)")
    args = parser.parse_args()

    if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN]):
        print("ERROR: Google auth config. config.py check .")
        return 1

    # file check
    paths: list[Path] = []
    for f in args.files:
        p = Path(f).resolve()
        if not p.is_file():
            print(f"ERROR: file not found — {p}")
            return 1
        paths.append(p)

    try:
        print("Access token ...")
        token = _refresh_access_token()

        # folder process
        folder_id = None
        if args.folder:
            folder_id = _find_folder(token, args.folder)
            if folder_id:
                print(f"folder found: {args.folder} ({folder_id})")
            else:
                folder_id = _create_folder(token, args.folder)
                print(f"folder Created: {args.folder} ({folder_id})")

        #
        for p in paths:
            print(f": {p.name} ({p.stat().st_size:,} bytes)...")
            result = _upload_file(token, p, folder_id)
            link = result.get("webViewLink", f"https://drive.google.com/file/d/{result['id']}")
            print(f"  completed: {link}")

    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"HTTP Error {e.code}: {err_body[:500]}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    print(f"\n{len(paths)}file completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
