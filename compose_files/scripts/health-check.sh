#!/usr/bin/env bash
# Print automation pipeline health summary for manual dashboard checks.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

COMMON_PATH="${COMMON_PATH:?COMMON_PATH not set}"
RADARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${COMMON_PATH}/configs/radarr/config.xml")"
SONARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${COMMON_PATH}/configs/sonarr/config.xml")"

echo "=== Media Server Health ==="
echo "MergerFS: $(df -h /mnt/combined-media 2>/dev/null | awk 'NR==2 {print $3 " used / " $2 " total (" $5 ")"}')"
echo "Downloads: $(du -sh "${COMMON_PATH}/qbittorrent/downloads" 2>/dev/null | awk '{print $1}')"
echo

# Core always-on vs optional (compose profiles: jellyfin, prowlarr).
for svc in plex radarr sonarr jackett qbittorrent flaresolverr seerr unpackerr recyclarr watchtower; do
  if docker ps --format '{{.Names}}' | grep -qx "${svc}"; then
    status="$(docker inspect --format '{{.State.Status}}' "${svc}" 2>/dev/null)"
    echo "[OK] ${svc}: ${status}"
  else
    echo "[--] ${svc}: not running"
  fi
done
echo "--- optional (parked unless COMPOSE_PROFILES enables them) ---"
for svc in jellyfin prowlarr; do
  if docker ps --format '{{.Names}}' | grep -qx "${svc}"; then
    status="$(docker inspect --format '{{.State.Status}}' "${svc}" 2>/dev/null)"
    echo "[ON] ${svc}: ${status}"
  else
    echo "[parked] ${svc}"
  fi
done
echo

echo "=== Radarr Health ==="
curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/health | python3 -m json.tool 2>/dev/null || echo "[]"
echo "Queue: $(curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/queue | python3 -c 'import json,sys; print(json.load(sys.stdin).get("totalRecords",0))') items"
echo

echo "=== Sonarr Health ==="
curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/health | python3 -m json.tool 2>/dev/null || echo "[]"
echo "Queue: $(curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/queue | python3 -c 'import json,sys; print(json.load(sys.stdin).get("totalRecords",0))') items"
