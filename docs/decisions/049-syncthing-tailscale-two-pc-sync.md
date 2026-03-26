# ADR-049: Syncthing + Tailscale 서울-remote PC 동기화

- 날짜: 2026-02-20 (초기 설정), 2026-02-28 (전수조사)
- 상태: 채택됨
- 결정: local-PC(DESKTOP-AI2ATA5)와 remote-PC(DESKTOP-U1RP8EF) 간 workspace 폴더를 Syncthing으로 양방향 동기화하고, Tailscale VPN(100.101.140.26, 100.115.65.112)으로 네트워크를 연결한다.
- 이유: 서울-remote 두 거점에서 동일한 작업 환경이 필요. 클라우드 스토리지(Google Drive 등)는 대용량 파일/심볼릭 링크 처리가 불안정. Syncthing은 P2P 암호화 동기화로 제3자 서버 불필요.
- 대안: Google Drive (심볼릭 링크 미지원), OneDrive (이미 혼란 유발), rsync+cron (단방향)
- 결과: 두 PC에서 동일 workspace 폴더 구조 유지, .stignore로 node_modules 등 제외
- 출처: 20260220_CC_002_222046_seoul_setup_script.txt, 20260228_CC_001_(2-t9)_165211_서울전수조사.txt

## Simondon Mapping
연합 환경(associated milieu)의 확장: 단일 물리 머신에서 2개 머신으로 환경이 확장되면서도 Syncthing이 동기화를 보장하여 기술적 개체(T9 OS)의 일관성 유지.
