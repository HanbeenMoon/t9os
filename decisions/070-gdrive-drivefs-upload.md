# ADR-070: Google Drive DriveFS 연동

- 날짜: 2026-03-23
- 상태: 채택됨
- 결정: Google Drive File Stream (G:) 마운트를 발견하여 OAuth 재인증 없이 파일 업로드 가능. `gdrive_upload.py` 파이프라인 작성.
- 이유:
  - Google Drive API로 업로드하려 했으나 기존 OAuth 토큰이 Calendar 스코프만 보유 → 403 에러 발생.
  - DriveFS가 이미 설치돼 있어서 `sudo mount -t drvfs G: /mnt/g` → `cp`로 해결 가능.
  - API 기반 업로드는 Drive 스코프 추가 시 사용할 수 있도록 파이프라인을 함께 작성.
- 대안:
  - **Google Drive API 직접 호출**: OAuth 토큰에 Drive 스코프 없음 → 재인증 필요. 스코프 재설정 도구(`google_oauth_setup.py`) 작성해둠.
  - **rclone**: 추가 설치+설정 필요 — DriveFS가 이미 있으므로 불필요.
  - **수동 업로드**: 반복 불가, 자동화 불가능 — 폐기.
- 결과:
  - `T9OS/pipes/gdrive_upload.py` — API 기반 업로드 (Drive 스코프 추가 시)
  - `T9OS/pipes/google_oauth_setup.py` — Drive 스코프 재설정 도구
  - DriveFS 경로: `/mnt/g/내 드라이브/` (WSL에서 mount 필요)

## Simondon Mapping
이 결정이 시몽동의 어떤 원리를 구현하는가: 전개체→개체 (산발적 파일 공유 → 체계적 Drive 연동). 개별적으로 흩어진 파일 전송 행위가 DriveFS 마운트를 통해 하나의 통합된 파일 공유 경로로 개체화된다.
