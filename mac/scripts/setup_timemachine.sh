#!/usr/bin/env bash
# setup_timemachine.sh
#
# Thunderbolt Bridge 전용 Time Machine 설정 스크립트.
#
# "Backup Disk Not Available 169.254.x.x" 오류 원인:
#   macOS가 Thunderbolt Bridge 인터페이스가 올라오기 전에 TM 마운트를
#   시도하거나, 인터페이스가 DOWN 상태여서 공유 드라이브를 찾지 못함.
#
# 실행: sudo bash setup_timemachine.sh
#
# 환경 변수로 재정의 가능:
#   TM_HOST    백업 Mac IP (기본: 169.254.72.157 / auto = 자동탐색)
#   TM_SHARE   SMB 공유 이름 (기본: auto = smbutil로 자동탐색)
#   TM_USER    SMB 사용자 (기본: 현재 로그인 사용자)
#   TM_PASS    SMB 비밀번호 (기본: 빈값)
#   TM_MOUNT   마운트 경로 (기본: /Volumes/TimeMachine-TB)

set -euo pipefail

TM_HOST="${TM_HOST:-169.254.72.157}"
TM_SHARE="${TM_SHARE:-auto}"
TM_USER="${TM_USER:-$(stat -f '%Su' /dev/console 2>/dev/null || echo guest)}"
TM_PASS="${TM_PASS:-}"
TM_MOUNT="${TM_MOUNT:-/Volumes/TimeMachine-TB}"

log()  { printf '\033[34m[TM]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[OK]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[ERR]\033[0m %s\n' "$*" >&2; exit 1; }
warn() { printf '\033[33m[WARN]\033[0m %s\n' "$*"; }
step() { printf '\033[1m──── %s ────\033[0m\n' "$*"; }

[[ "$(uname)" == "Darwin" ]] || fail "macOS 전용 스크립트입니다."

if [[ "$EUID" -ne 0 ]]; then
    warn "root 권한이 없습니다. tmutil setdestination 실패 가능."
    warn "재실행: sudo bash $0"
fi

# ═══════════════════════════════════════════════════════════
# 1. Thunderbolt Bridge 인터페이스 찾기 & 활성화
# ═══════════════════════════════════════════════════════════
step "Thunderbolt Bridge 인터페이스 확인"

TB_IFACE=""

# networksetup으로 Thunderbolt Bridge 장치 이름 탐색
while IFS= read -r line; do
    if [[ "$line" == *"Thunderbolt Bridge"* ]]; then
        # 다음 줄이 Device: enX 또는 bridgeX
        read -r devline || true
        iface=$(echo "$devline" | awk '{print $2}')
        if [[ -n "$iface" ]]; then
            TB_IFACE="$iface"
            break
        fi
    fi
done < <(networksetup -listallhardwareports 2>/dev/null)

# 못 찾으면 ifconfig에서 169.254 주소를 가진 인터페이스 탐색
if [[ -z "$TB_IFACE" ]]; then
    TB_IFACE=$(ifconfig | awk '
        /^[a-z]/ { iface=$1; gsub(/:$/,"",iface) }
        /inet 169\.254\./ { print iface; exit }
    ')
fi

if [[ -z "$TB_IFACE" ]]; then
    warn "Thunderbolt Bridge 인터페이스를 찾지 못했습니다."
    warn "확인: 시스템 설정 > 네트워크 > Thunderbolt Bridge 가 보이는지"
    warn "케이블이 연결된 상태에서 잠시 후 재시도하거나 수동 지정:"
    warn "  TM_HOST=169.254.72.157 sudo bash $0"
else
    ok "Thunderbolt Bridge 인터페이스: $TB_IFACE"

    # 인터페이스 UP 보장
    iface_status=$(ifconfig "$TB_IFACE" 2>/dev/null | grep -c "status: active" || true)
    if [[ "$iface_status" -eq 0 ]]; then
        log "$TB_IFACE 인터페이스를 UP 상태로 전환 중..."
        ifconfig "$TB_IFACE" up 2>/dev/null || warn "ifconfig up 실패 (무시)"
    fi

    # 링크-로컬 주소 할당 대기 (최대 15초)
    for i in $(seq 1 15); do
        LOCAL_LL=$(ipconfig getifaddr "$TB_IFACE" 2>/dev/null || true)
        if [[ "$LOCAL_LL" =~ ^169\.254\. ]]; then
            ok "이 Mac의 Thunderbolt 주소: $LOCAL_LL"
            break
        fi
        [[ "$i" -eq 15 ]] && warn "링크-로컬 주소 미할당 — 인터페이스 미연결 가능성"
        sleep 1
    done
fi

# ═══════════════════════════════════════════════════════════
# 2. 백업 호스트 자동탐색 (TM_HOST=auto 또는 기본값으로 연결 불가 시)
# ═══════════════════════════════════════════════════════════
step "백업 호스트 연결 확인"

find_backup_host() {
    # ARP 캐시에서 169.254.x.x 탐색
    arp -a 2>/dev/null | grep -oE '169\.[0-9]+\.[0-9]+\.[0-9]+' | head -5
}

if ! ping -c 1 -W 2 -q "$TM_HOST" > /dev/null 2>&1; then
    warn "$TM_HOST 에 응답 없음 — 링크-로컬 네트워크에서 자동탐색..."

    FOUND_HOST=""
    for candidate in $(find_backup_host); do
        log "  탐색: $candidate"
        if ping -c 1 -W 1 -q "$candidate" > /dev/null 2>&1; then
            if nc -z -w 2 "$candidate" 445 2>/dev/null; then
                FOUND_HOST="$candidate"
                break
            fi
        fi
    done

    if [[ -n "$FOUND_HOST" ]]; then
        ok "백업 호스트 발견: $FOUND_HOST"
        TM_HOST="$FOUND_HOST"
    else
        fail "백업 호스트를 찾지 못했습니다.
  체크리스트:
  ① Thunderbolt 케이블이 양쪽 Mac에 완전히 꽂혀 있는지 확인
  ② 백업 Mac: 시스템 설정 > 일반 > 공유 > 파일 공유 가 켜져 있는지 확인
  ③ 백업 Mac: 시스템 설정 > 네트워크 > Thunderbolt Bridge 가 활성화되어 있는지 확인
  ④ 이 Mac: 시스템 설정 > 네트워크 > Thunderbolt Bridge 가 활성화되어 있는지 확인
  수동 확인: arp -a | grep 169.254"
    fi
fi

ok "백업 호스트 응답 확인: $TM_HOST"

# SMB 포트 확인
if nc -z -w 3 "$TM_HOST" 445 2>/dev/null; then
    ok "SMB 포트(445) 열림"
else
    warn "SMB 포트 445 닫힘"
    warn "백업 Mac: 시스템 설정 > 일반 > 공유 > 파일 공유 활성화 필요"
fi

# ═══════════════════════════════════════════════════════════
# 3. 공유 이름 자동탐색
# ═══════════════════════════════════════════════════════════
step "SMB 공유 탐색"

list_shares() {
    local host="$1"
    local user="$2"
    smbutil view "//${user}@${host}" 2>/dev/null \
        | grep -v "^Share\|^---\|^$" \
        | awk '{print $1}' \
        || true
}

if [[ "$TM_SHARE" == "auto" ]]; then
    log "공유 목록 조회 중: smb://$TM_USER@$TM_HOST"
    SHARES=$(list_shares "$TM_HOST" "$TM_USER")

    if [[ -z "$SHARES" ]]; then
        # guest로 재시도
        SHARES=$(list_shares "$TM_HOST" "guest")
        [[ -n "$SHARES" ]] && TM_USER="guest"
    fi

    if [[ -z "$SHARES" ]]; then
        warn "공유 목록 조회 실패 — 기본값 'TimeMachine' 사용"
        TM_SHARE="TimeMachine"
    else
        log "발견된 공유:"
        echo "$SHARES" | while IFS= read -r s; do log "  • $s"; done

        # TimeMachine / Backup / Data 순으로 우선 선택
        for preferred in TimeMachine Backup Data; do
            if echo "$SHARES" | grep -qi "^${preferred}$"; then
                TM_SHARE="$preferred"
                break
            fi
        done
        # 그 외엔 첫 번째 공유 사용
        [[ "$TM_SHARE" == "auto" ]] && TM_SHARE=$(echo "$SHARES" | head -1)
        ok "사용할 공유: $TM_SHARE"
    fi
fi

log "호스트: $TM_HOST  /  공유: $TM_SHARE  /  사용자: $TM_USER"

# ═══════════════════════════════════════════════════════════
# 4. 기존 마운트 정리
# ═══════════════════════════════════════════════════════════
step "기존 마운트 정리"

if mount | grep -q " ${TM_MOUNT} " 2>/dev/null; then
    log "기존 마운트 해제: $TM_MOUNT"
    diskutil unmount force "$TM_MOUNT" 2>/dev/null \
        || umount -f "$TM_MOUNT" 2>/dev/null \
        || warn "강제 해제 실패 — 계속 진행"
fi

# 동일 호스트의 다른 마운트 포인트도 정리 (stale)
mount | grep "//.*@${TM_HOST}/" | awk '{print $3}' | while IFS= read -r mp; do
    log "  stale 마운트 해제: $mp"
    diskutil unmount force "$mp" 2>/dev/null || true
done

mkdir -p "$TM_MOUNT"

# ═══════════════════════════════════════════════════════════
# 5. SMB 마운트
# ═══════════════════════════════════════════════════════════
step "SMB 공유 마운트"

if [[ -n "$TM_PASS" ]]; then
    MOUNT_URL="smb://${TM_USER}:${TM_PASS}@${TM_HOST}/${TM_SHARE}"
    DISPLAY_URL="smb://${TM_USER}:***@${TM_HOST}/${TM_SHARE}"
else
    MOUNT_URL="smb://${TM_USER}@${TM_HOST}/${TM_SHARE}"
    DISPLAY_URL="$MOUNT_URL"
fi

log "마운트: $DISPLAY_URL → $TM_MOUNT"

MOUNTED=false
if mount_smbfs "$MOUNT_URL" "$TM_MOUNT" 2>/dev/null; then
    MOUNTED=true
    ok "mount_smbfs 성공"
elif /sbin/mount -t smbfs "$MOUNT_URL" "$TM_MOUNT" 2>/dev/null; then
    MOUNTED=true
    ok "mount -t smbfs 성공"
fi

if [[ "$MOUNTED" == false ]]; then
    # Finder를 통해 연결 시도 후 사용자에게 안내
    open "smb://${TM_HOST}/${TM_SHARE}" 2>/dev/null || true
    fail "SMB 마운트 실패. 수동 진행:
  1. Finder > 이동 > 서버에 연결 (⌘K)
  2. 입력: smb://${TM_HOST}/${TM_SHARE}
  3. 연결 후:
       sudo tmutil setdestination -p '$TM_MOUNT'
  또는 비밀번호 설정:
       TM_PASS=비밀번호 sudo bash $0"
fi

# 마운트 확인
if ! mount | grep -q " ${TM_MOUNT} "; then
    fail "마운트 테이블에서 $TM_MOUNT 를 찾을 수 없습니다"
fi
ok "마운트 확인: $TM_MOUNT"

# ═══════════════════════════════════════════════════════════
# 6. Time Machine 등록
# ═══════════════════════════════════════════════════════════
step "Time Machine 대상 등록"

TM_SET=false
if tmutil setdestination -p "$TM_MOUNT" 2>/dev/null; then
    TM_SET=true
elif tmutil setdestination "$TM_MOUNT" 2>/dev/null; then
    TM_SET=true
fi

if [[ "$TM_SET" == true ]]; then
    ok "Time Machine 대상 설정 완료: $TM_MOUNT"
else
    warn "tmutil setdestination 실패"
    warn "수동: 시스템 설정 > 일반 > Time Machine > 백업 디스크 추가"
    warn "     마운트된 $TM_MOUNT 를 선택"
fi

# ═══════════════════════════════════════════════════════════
# 7. 결과 요약
# ═══════════════════════════════════════════════════════════
echo ""
log "현재 Time Machine 대상:"
tmutil destinationinfo 2>/dev/null \
    | grep -E "^(Name|URL|Mount Point|Kind)" \
    | sed 's/^/  /' \
    || warn "tmutil destinationinfo 읽기 실패"

echo ""
ok "설정 완료."
echo ""
echo "  지금 백업 시작:  tmutil startbackup"
echo ""
log "[재부팅 후 자동 복구] launchd 데몬 설치:"
log "  sudo cp mac/launchd/com.keepsake.timemachine-mount.plist /Library/LaunchDaemons/"
log "  sudo launchctl load /Library/LaunchDaemons/com.keepsake.timemachine-mount.plist"
