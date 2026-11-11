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

if ! command docker info >/dev/null 2>&1; then
  # sudo docker is the engine binary, not this function.
  # shellcheck disable=SC2032,SC2033
  docker() { sudo docker "$@"; }
fi

COMMON_PATH="${COMMON_PATH:?COMMON_PATH not set}"
APPDATA_PATH="${APPDATA_PATH:?APPDATA_PATH not set}"
RADARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${APPDATA_PATH}/radarr/config.xml")"
SONARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${APPDATA_PATH}/sonarr/config.xml")"
PLEX_PREFS="${APPDATA_PATH}/plex/Library/Application Support/Plex Media Server/Preferences.xml"

queue_count() {
  local url=$1 key=$2
  local body
  body="$(curl -sf -H "X-Api-Key: ${key}" "${url}" || true)"
  python3 -c 'import json,sys; raw=sys.stdin.read();
print("?") if not raw.strip() else print(json.loads(raw).get("totalRecords",0))' <<<"${body}"
}

docker_ok() {
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$1"
}

echo "=== Media Server Health ==="
echo "MergerFS: $(df -h /mnt/combined-media 2>/dev/null | awk 'NR==2 {print $3 " used / " $2 " total (" $5 ")"}')"
echo "Downloads: $(du -sh "${COMMON_PATH}/qbittorrent/downloads" 2>/dev/null | awk '{print $1}')"
echo "Appdata: ${APPDATA_PATH} fstype=$(findmnt -n -o FSTYPE --target "${APPDATA_PATH}" 2>/dev/null || echo '?')"
if findmnt -n -o FSTYPE --target "${APPDATA_PATH}" 2>/dev/null | grep -qi 'fuse.mergerfs'; then
  echo "[FAIL] APPDATA_PATH is on mergerfs — SQLite will corrupt"
fi
echo

# Core always-on vs optional (compose profiles: jellyfin, prowlarr).
for svc in plex tautulli radarr sonarr jackett qbittorrent flaresolverr seerr unpackerr bazarr recyclarr watchtower panelarr homarr paperless paperless-redis paperless-gotenberg paperless-tika; do
  if docker_ok "${svc}"; then
    status="$(docker inspect --format '{{.State.Status}}' "${svc}" 2>/dev/null)"
    echo "[OK] ${svc}: ${status}"
  else
    echo "[--] ${svc}: not running"
  fi
done
echo "--- optional (parked unless COMPOSE_PROFILES enables them) ---"
for svc in jellyfin prowlarr; do
  if docker_ok "${svc}"; then
    status="$(docker inspect --format '{{.State.Status}}' "${svc}" 2>/dev/null)"
    echo "[ON] ${svc}: ${status}"
  else
    echo "[parked] ${svc}"
  fi
done
echo

echo "=== Radarr Health ==="
curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/health | python3 -m json.tool 2>/dev/null || echo "[]"
echo "Queue: $(queue_count http://localhost:7878/api/v3/queue "${RADARR_KEY}") items"
echo

echo "=== Sonarr Health ==="
curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/health | python3 -m json.tool 2>/dev/null || echo "[]"
echo "Queue: $(queue_count http://localhost:8989/api/v3/queue "${SONARR_KEY}") items"
echo

echo "=== Plex libraries ==="
if [[ -f "${PLEX_PREFS}" ]]; then
  token="$(python3 -c 'import xml.etree.ElementTree as ET,sys; print(ET.parse(sys.argv[1]).getroot().attrib.get("PlexOnlineToken",""))' "${PLEX_PREFS}")"
  sections="$(curl -sf --max-time 10 "http://localhost:32400/library/sections?X-Plex-Token=${token}" || true)"
  python3 -c '
import sys, xml.etree.ElementTree as ET
raw=sys.stdin.read()
if not raw.strip():
    print("[FAIL] Plex sections API empty")
    sys.exit(0)
root=ET.fromstring(raw)
dirs=root.findall("Directory")
print("sections", len(dirs))
for d in dirs:
    locs=[l.get("path") for l in d.findall("Location")]
    print(" ", d.get("title"), locs)
if len(dirs)==0:
    print("[FAIL] Plex has no libraries")
' <<<"${sections}"
else
  echo "[FAIL] missing Plex Preferences.xml"
fi
