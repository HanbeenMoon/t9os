# ADR-049: Syncthing + Tailscale 멀티 PC 동기화

- 날짜: 2026-02-20 (초기 설정), 2026-02-28 (전수조사)
- 상태: 채택됨
- 결정: local-PC와 remote-PC 간 workspace 폴더를 Syncthing으로 양방향 동기화하고, Tailscale VPN으로 네트워크를 연결한다.
- 이유: 두 거점에서 동일한 작업 환경이 필요. 클라우드 스토리지(Google Drive 등)는 대용량 파일/심볼릭 링크 처리가 불안정. Syncthing은 P2P 암호화 동기화로 제3자 서버 불필요.
- 대안: Google Drive (심볼릭 링크 미지원), OneDrive (이미 혼란 유발), rsync+cron (단방향)
- 결과: 두 PC에서 동일 workspace 폴더 구조 유지, .stignore로 node_modules 등 제외
