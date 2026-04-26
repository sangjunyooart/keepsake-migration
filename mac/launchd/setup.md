# Mac mini 자동 시작 설정 (launchd)

Mac mini 재부팅 시 모든 서비스가 자동으로 시작됩니다.

---

## 자동 시작 서비스 목록

| 서비스 | Label | 설명 |
|--------|-------|------|
| keepsake-drift | `com.keepsake.drift` | keepsake-drift 서버 (OpenAI auto OFF) |
| lens: human_time | `com.keepsake.migration.lens-human-time` | 학습 시스템 1 |
| lens: infrastructure_time | `com.keepsake.migration.lens-infrastructure-time` | 학습 시스템 2 |
| lens: environmental_time | `com.keepsake.migration.lens-environmental-time` | 학습 시스템 3 |
| lens: digital_time | `com.keepsake.migration.lens-digital-time` | 학습 시스템 4 |
| lens: liminal_time | `com.keepsake.migration.lens-liminal-time` | 학습 시스템 5 |
| lens: more_than_human_time | `com.keepsake.migration.lens-more-than-human-time` | 학습 시스템 6 |
| dashboard | `com.keepsake.migration.dashboard` | Flask 대시보드 (port 8080) |
| Chrome opener | `com.keepsake.chrome-opener` | admin/monitor 페이지 자동 열기 |

Chrome은 부팅 후 15초 뒤에 다음 페이지를 자동으로 엽니다:
- `http://localhost:8080` — 로컬 대시보드 (admin)
- `http://localhost:8080/monitor` — 로컬 모니터
- `https://keepsake-drift.net/monitor/` — 원격 모니터

---

## 최초 설치 (한 번만 실행)

```bash
cd ~/keepsake-migration
bash mac/launchd/install.sh
```

`install.sh`가 자동으로:
1. 현재 macOS 사용자 이름으로 경로 치환
2. `~/Library/LaunchAgents/`에 plist 복사
3. 모든 서비스 로드 (즉시 시작)

---

## 수동 설치 (install.sh 사용하지 않을 경우)

```bash
# 실제 username 확인
whoami

# 각 plist의 YOUR_USERNAME을 실제 username으로 교체한 뒤:
cp com.keepsake.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.keepsake.migration.lens-human-time.plist
# ... 나머지도 동일하게
```

---

## 서비스 관리 명령어

```bash
# 현재 로드된 keepsake 서비스 확인
launchctl list | grep keepsake

# 특정 서비스 재시작
launchctl unload ~/Library/LaunchAgents/com.keepsake.migration.dashboard.plist
launchctl load   ~/Library/LaunchAgents/com.keepsake.migration.dashboard.plist

# 모든 서비스 제거 (uninstall)
bash mac/launchd/uninstall.sh

# 로그 확인
tail -f ~/keepsake-migration/mac/logs/lens-human-time.log
tail -f ~/keepsake-migration/mac/logs/dashboard.log
tail -f ~/keepsake-drift/logs/server.log
```

---

## keepsake-drift OpenAI auto tick OFF 설정

`com.keepsake.drift.plist`와 `start-drift.sh` 모두 `OPENAI_AUTO=false` 환경변수를 설정합니다.  
`.env` 파일에 `OPENAI_AUTO=true`가 있어도 `start-drift.sh`에서 재덮어쓰므로 항상 OFF로 시작됩니다.

keepsake-drift 프로젝트가 이 환경변수를 읽는 방식:
```python
# keepsake-drift 코드에서:
import os
openai_auto = os.getenv("OPENAI_AUTO", "false").lower() == "true"
```

---

## 디렉토리 구조 가정

```
~/keepsake-migration/   ← keepsake-migration 프로젝트
~/keepsake-drift/       ← keepsake-drift 프로젝트
```

keepsake-drift 경로가 다르면 `start-drift.sh`의 `PROJECT_DIR` 수정 필요.

---

## 문제 해결

**서비스가 시작하지 않을 때:**
```bash
# .err 파일 확인
cat ~/keepsake-migration/mac/logs/lens-human-time.err

# launchctl 상세 로그
log show --predicate 'subsystem == "com.apple.launchd"' --last 5m | grep keepsake
```

**venv가 없을 때:**
```bash
cd ~/keepsake-migration/mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
