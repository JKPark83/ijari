#!/bin/bash
# 이 자리 로컬 스택 자동 기동 — 로그인 시 LaunchAgent(com.jkpark.ijari.stack)가 실행한다.
# 순서: T31 대기 → sparsebundle 마운트 → OrbStack 기동 → docker compose up
# 로그: ~/Library/Logs/ijari-stack.log
set -uo pipefail
export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.orbstack/bin:$PATH"

IMG="/Volumes/T31/ijari/ijari-db.sparsebundle"
MOUNT="/Volumes/IjariDB"
COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo "[$(date '+%F %T')] $*"; }

# 외장 드라이브는 로그인 직후 늦게 마운트될 수 있다
for _ in $(seq 1 30); do [ -d "${IMG%/*}" ] && break; sleep 2; done
if [ ! -d "${IMG%/*}" ]; then log "T31 미마운트 — 중단"; exit 1; fi

if [ ! -d "$MOUNT" ]; then
  log "sparsebundle 마운트"
  hdiutil attach -noautoopen "$IMG" >/dev/null || { log "hdiutil attach 실패"; exit 1; }
fi

log "OrbStack 기동 대기"
open -ga OrbStack
for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
docker info >/dev/null 2>&1 || { log "docker 데몬 응답 없음 — 중단"; exit 1; }

cd "$COMPOSE_DIR" && docker compose up -d
log "완료: $(docker ps --format '{{.Names}}' | tr '\n' ' ')"
