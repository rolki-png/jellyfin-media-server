#!/usr/bin/env bash
# Configure Radarr, Sonarr, qBittorrent paths, clear stuck queues, and sync TRaSH guides.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

COMMON_PATH="${COMMON_PATH:?COMMON_PATH not set}"
RADARR_CONFIG="${COMMON_PATH}/configs/radarr/config.xml"
SONARR_CONFIG="${COMMON_PATH}/configs/sonarr/config.xml"
QBIT_CATEGORIES="${COMMON_PATH}/configs/qbittorrent/qBittorrent/categories.json"
RECYCLARR_SECRETS="${COMPOSE_DIR}/recyclarr/secrets.yml"

RADARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${RADARR_CONFIG}")"
SONARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${SONARR_CONFIG}")"

log() {
  echo "==> $*"
}

fix_radarr_media() {
  log "Fixing Radarr media management"
  local current updated
  current="$(curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/config/mediamanagement)"
  updated="$(CURRENT="${current}" python3 - <<'PY'
import json, os
cfg = json.loads(os.environ["CURRENT"])
cfg["copyUsingHardlinks"] = True
cfg["importExtraFiles"] = True
cfg["extraFileExtensions"] = "srt"
cfg["minimumFreeSpaceWhenImporting"] = 10240
cfg["skipFreeSpaceCheckWhenImporting"] = False
print(json.dumps(cfg))
PY
)"
  curl -sf -H "X-Api-Key: ${RADARR_KEY}" -H "Content-Type: application/json" \
    -X PUT http://localhost:7878/api/v3/config/mediamanagement -d "${updated}" >/dev/null
}

fix_sonarr_media() {
  log "Fixing Sonarr media management"
  local current updated
  current="$(curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/config/mediamanagement)"
  updated="$(CURRENT="${current}" python3 - <<'PY'
import json, os
cfg = json.loads(os.environ["CURRENT"])
cfg["copyUsingHardlinks"] = True
cfg["importExtraFiles"] = True
cfg["extraFileExtensions"] = "srt"
cfg["minimumFreeSpaceWhenImporting"] = 10240
cfg["skipFreeSpaceCheckWhenImporting"] = False
print(json.dumps(cfg))
PY
)"
  curl -sf -H "X-Api-Key: ${SONARR_KEY}" -H "Content-Type: application/json" \
    -X PUT http://localhost:8989/api/v3/config/mediamanagement -d "${updated}" >/dev/null
}

fix_download_client() {
  local port=$1
  local key=$2
  local name=$3

  log "Fixing ${name} qBittorrent download client"
  local current updated id
  current="$(curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/downloadclient")"
  id="$(CURRENT="${current}" python3 - <<'PY'
import json, os
print(json.loads(os.environ["CURRENT"])[0]["id"])
PY
)"
  updated="$(CURRENT="${current}" python3 - <<'PY'
import json, os
client = json.loads(os.environ["CURRENT"])[0]
# Keep completed torrents so qBit can seed via hardlinked library files.
client["removeCompletedDownloads"] = False
client["removeFailedDownloads"] = True
print(json.dumps(client))
PY
)"
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X PUT "http://localhost:${port}/api/v3/downloadclient/${id}" -d "${updated}" >/dev/null
}

ensure_root_folder() {
  local port=$1
  local key=$2
  local name=$3
  local path=$4

  log "Ensuring ${name} root folder ${path}"
  local existing
  existing="$(curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/rootfolder")"
  if EXISTING="${existing}" WANT="${path}" python3 - <<'PY'
import json, os, sys
want = os.environ["WANT"].rstrip("/")
roots = json.loads(os.environ["EXISTING"])
sys.exit(0 if any(r.get("path", "").rstrip("/") == want for r in roots) else 1)
PY
  then
    log "${name} root folder already set"
    return 0
  fi
  mkdir -p "${path}"
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X POST "http://localhost:${port}/api/v3/rootfolder" \
    -d "{\"path\":\"${path}\"}" >/dev/null
}

ensure_remote_path_mapping() {
  local port=$1
  local key=$2
  local name=$3
  local host="${4:-qbittorrent}"
  local remote="${5:-/downloads/}"
  local local_path="${6:-${COMMON_PATH}/qbittorrent/downloads/}"

  log "Ensuring ${name} remote path mapping ${remote} -> ${local_path}"
  local existing
  existing="$(curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/remotepathmapping")"
  if EXISTING="${existing}" HOST="${host}" REMOTE="${remote}" LOCAL="${local_path}" python3 - <<'PY'
import json, os, sys
rows = json.loads(os.environ["EXISTING"])
host = os.environ["HOST"]
remote = os.environ["REMOTE"].rstrip("/") + "/"
local = os.environ["LOCAL"].rstrip("/") + "/"
sys.exit(0 if any(
    r.get("host") == host
    and r.get("remotePath", "").rstrip("/") + "/" == remote
    and r.get("localPath", "").rstrip("/") + "/" == local
    for r in rows
) else 1)
PY
  then
    log "${name} remote path mapping already set"
    return 0
  fi
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X POST "http://localhost:${port}/api/v3/remotepathmapping" \
    -d "$(HOST="${host}" REMOTE="${remote}" LOCAL="${local_path}" python3 - <<'PY'
import json, os
print(json.dumps({
    "host": os.environ["HOST"],
    "remotePath": os.environ["REMOTE"],
    "localPath": os.environ["LOCAL"],
}))
PY
)" >/dev/null
}

ensure_same_disk_script() {
  local port=$1
  local key=$2
  local name=$3
  local script_path="/scripts/same-disk-import.sh"

  log "Ensuring ${name} same-disk Custom Script Connect"
  local existing
  existing="$(curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/notification")"
  local match_id
  match_id="$(EXISTING="${existing}" PATH_WANT="${script_path}" python3 - <<'PY'
import json, os
want = os.environ["PATH_WANT"]
for n in json.loads(os.environ["EXISTING"]):
    if n.get("implementation") != "CustomScript":
        continue
    fields = {f.get("name"): f.get("value") for f in n.get("fields", [])}
    if fields.get("path") == want:
        print(n["id"])
        break
PY
)"

  local payload
  payload="$(NAME="${name}" PATH_WANT="${script_path}" python3 - <<'PY'
import json, os
name = os.environ["NAME"]
# Sonarr supports onImportComplete; Radarr schema omits it — only set for Sonarr.
body = {
    "name": "Same-disk hardlink",
    "implementation": "CustomScript",
    "configContract": "CustomScriptSettings",
    "onDownload": True,
    "onUpgrade": True,
    "onRename": False,
    "fields": [
        {"name": "path", "value": os.environ["PATH_WANT"]},
    ],
    "tags": [],
}
if name == "Sonarr":
    body["onImportComplete"] = True
print(json.dumps(body))
PY
)"

  if [[ -n "${match_id}" ]]; then
    curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
      -X PUT "http://localhost:${port}/api/v3/notification/${match_id}" \
      -d "$(PAYLOAD="${payload}" ID="${match_id}" python3 - <<'PY'
import json, os
body = json.loads(os.environ["PAYLOAD"])
body["id"] = int(os.environ["ID"])
print(json.dumps(body))
PY
)" >/dev/null
    log "${name} same-disk script notification updated (id=${match_id})"
  else
    curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
      -X POST "http://localhost:${port}/api/v3/notification" \
      -d "${payload}" >/dev/null
    log "${name} same-disk script notification created"
  fi
}

clear_stuck_queue() {
  local port=$1
  local key=$2
  local name=$3

  log "Clearing stuck ${name} queue items"
  local queue ids_json count
  queue="$(curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/queue?pageSize=200")"
  ids_json="$(QUEUE="${queue}" python3 - <<'PY'
import json, os
q = json.loads(os.environ["QUEUE"])
ids = [
    r["id"] for r in q.get("records", [])
    if r.get("status") == "completed" or r.get("trackedDownloadStatus") == "warning"
]
print(json.dumps(ids))
PY
)"
  count="$(IDS="${ids_json}" python3 - <<'PY'
import json, os
print(len(json.loads(os.environ["IDS"])))
PY
)"
  if [[ "${count}" -eq 0 ]]; then
    log "No stuck ${name} queue items"
    return 0
  fi
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X DELETE "http://localhost:${port}/api/v3/queue/bulk?removeFromClient=true&blocklist=false&skipRedownload=true" \
    -d "{\"ids\": ${ids_json}}" >/dev/null
  log "Removed ${count} stuck ${name} queue item(s)"
}

trigger_download_scan() {
  local downloads="${COMMON_PATH}/qbittorrent/downloads"
  log "Triggering download folder scans (${downloads})"
  curl -sf -H "X-Api-Key: ${RADARR_KEY}" -H "Content-Type: application/json" \
    -X POST http://localhost:7878/api/v3/command \
    -d "{\"name\":\"DownloadedMoviesScan\",\"path\":\"${downloads}\",\"importMode\":\"Auto\"}" >/dev/null || true
  curl -sf -H "X-Api-Key: ${RADARR_KEY}" -H "Content-Type: application/json" \
    -X POST http://localhost:7878/api/v3/command \
    -d '{"name":"RefreshMonitoredDownloads"}' >/dev/null || true
  curl -sf -H "X-Api-Key: ${SONARR_KEY}" -H "Content-Type: application/json" \
    -X POST http://localhost:8989/api/v3/command \
    -d "{\"name\":\"DownloadedEpisodesScan\",\"path\":\"${downloads}\",\"importMode\":\"Auto\"}" >/dev/null || true
  curl -sf -H "X-Api-Key: ${SONARR_KEY}" -H "Content-Type: application/json" \
    -X POST http://localhost:8989/api/v3/command \
    -d '{"name":"RefreshMonitoredDownloads"}' >/dev/null || true
}

setup_qbit_categories() {
  log "Configuring qBittorrent category save paths"
  mkdir -p "${COMMON_PATH}/qbittorrent/downloads/radarr" \
           "${COMMON_PATH}/qbittorrent/downloads/tv-sonarr"
  python3 - <<PY
import json
from pathlib import Path

path = Path("${QBIT_CATEGORIES}")
data = json.loads(path.read_text()) if path.exists() else {}
data.setdefault("radarr", {})["save_path"] = "/downloads/radarr"
data.setdefault("tv-sonarr", {})["save_path"] = "/downloads/tv-sonarr"
path.write_text(json.dumps(data, indent=4) + "\n")
PY
}

set_default_quality_profiles() {
  log "Applying UHD quality profiles to existing media"
  local radarr_profile sonarr_profile
  local tmp
  tmp="$(mktemp -d)"

  radarr_profile="$(curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/qualityprofile | python3 -c "
import json,sys
for p in json.load(sys.stdin):
    if p['name'] == 'UHD Bluray + WEB':
        print(p['id']); break
" 2>/dev/null || true)"

  sonarr_profile="$(curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/qualityprofile | python3 -c "
import json,sys
for p in json.load(sys.stdin):
    if p['name'] == 'WEB-2160p':
        print(p['id']); break
" 2>/dev/null || true)"

  if [[ -n "${radarr_profile:-}" ]]; then
    curl -sf -H "X-Api-Key: ${RADARR_KEY}" http://localhost:7878/api/v3/movie -o "${tmp}/movies.json"
    python3 - "${tmp}/movies.json" "${radarr_profile}" <<'PY' > "${tmp}/radarr-editor.json"
import json, sys
movies = json.load(open(sys.argv[1]))
profile = int(sys.argv[2])
ids = [m["id"] for m in movies if m.get("qualityProfileId") != profile]
print(json.dumps({"movieIds": ids, "qualityProfileId": profile}))
PY
    if [[ "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["movieIds"]))' "${tmp}/radarr-editor.json")" -gt 0 ]]; then
      curl -sf -H "X-Api-Key: ${RADARR_KEY}" -H "Content-Type: application/json" \
        -X PUT http://localhost:7878/api/v3/movie/editor -d @"${tmp}/radarr-editor.json" >/dev/null
      log "Updated Radarr movies to UHD Bluray + WEB"
    fi
  fi

  if [[ -n "${sonarr_profile:-}" ]]; then
    curl -sf -H "X-Api-Key: ${SONARR_KEY}" http://localhost:8989/api/v3/series -o "${tmp}/series.json"
    python3 - "${tmp}/series.json" "${sonarr_profile}" <<'PY' > "${tmp}/sonarr-editor.json"
import json, sys
series = json.load(open(sys.argv[1]))
profile = int(sys.argv[2])
ids = [s["id"] for s in series if s.get("qualityProfileId") != profile]
print(json.dumps({"seriesIds": ids, "qualityProfileId": profile}))
PY
    if [[ "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["seriesIds"]))' "${tmp}/sonarr-editor.json")" -gt 0 ]]; then
      curl -sf -H "X-Api-Key: ${SONARR_KEY}" -H "Content-Type: application/json" \
        -X PUT http://localhost:8989/api/v3/series/editor -d @"${tmp}/sonarr-editor.json" >/dev/null
      log "Updated Sonarr series to WEB-2160p"
    fi
  fi

  rm -rf "${tmp}"
}

write_recyclarr_secrets() {
  log "Writing Recyclarr secrets.yml"
  cat > "${RECYCLARR_SECRETS}" <<EOF
radarr_api_key: ${RADARR_KEY}
sonarr_api_key: ${SONARR_KEY}
EOF
  chmod 600 "${RECYCLARR_SECRETS}"
}

write_unpackerr_secrets() {
  log "Writing Unpackerr API key files"
  local unpackerr_dir="${COMMON_PATH}/configs/unpackerr"
  mkdir -p "${unpackerr_dir}"
  printf '%s' "${RADARR_KEY}" > "${unpackerr_dir}/radarr_api_key"
  printf '%s' "${SONARR_KEY}" > "${unpackerr_dir}/sonarr_api_key"
  chmod 600 "${unpackerr_dir}/radarr_api_key" "${unpackerr_dir}/sonarr_api_key"
}

run_recyclarr_sync() {
  if ! docker ps --format '{{.Names}}' | grep -qx recyclarr; then
    log "Recyclarr not running yet (will sync after compose up)"
    return 0
  fi
  log "Running Recyclarr sync"
  docker exec recyclarr recyclarr state repair --adopt >/dev/null 2>&1 || true
  docker exec recyclarr recyclarr sync || {
    log "Recyclarr sync failed — check: docker logs recyclarr"
    return 0
  }
}

remove_empty_plex_dir() {
  local plex_dir="${COMMON_PATH}/plex"
  if [[ -d "${plex_dir}" ]] && [[ -z "$(ls -A "${plex_dir}" 2>/dev/null)" ]]; then
    log "Removing empty legacy plex directory"
    rmdir "${plex_dir}" 2>/dev/null || true
  fi
}

plex_preferences_path() {
  echo "${COMMON_PATH}/configs/plex/Library/Application Support/Plex Media Server/Preferences.xml"
}

plex_auth_token() {
  local prefs
  prefs="$(plex_preferences_path)"
  if [[ ! -f "${prefs}" ]]; then
    return 1
  fi
  grep -oP 'PlexOnlineToken="\K[^"]+' "${prefs}" || true
}

fix_plex_transcode_dir() {
  local transcode_dir="${PLEX_TRANSCODE_DIR:-/var/lib/plex-transcode}"
  local prefs
  prefs="$(plex_preferences_path)"

  log "Ensuring Plex transcode directory (${transcode_dir})"
  mkdir -p "${transcode_dir}"
  chown "${PUID:-1000}:${PGID:-1000}" "${transcode_dir}"

  if [[ ! -f "${prefs}" ]]; then
    log "Plex preferences not found yet — skipping transcode path setup"
    return 0
  fi

  PREFS="${prefs}" python3 - <<'PY'
import os, re
path = os.environ["PREFS"]
with open(path, encoding="utf-8") as f:
    xml = f.read()
target = "/transcode"
if re.search(r'TranscoderTempDirectory="[^"]*"', xml):
    updated = re.sub(
        r'TranscoderTempDirectory="[^"]*"',
        f'TranscoderTempDirectory="{target}"',
        xml,
    )
else:
    updated = xml.replace(
        "<Preferences ",
        f'<Preferences TranscoderTempDirectory="{target}" ',
        1,
    )
if updated != xml:
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
PY
  log "Set Plex TranscoderTempDirectory to /transcode (host: ${transcode_dir})"
}

ensure_plex_notification() {
  local port=$1
  local key=$2
  local name=$3

  if ! docker ps --format '{{.Names}}' | grep -qx plex; then
    log "Plex not running — skipping ${name} Plex notification setup"
    return 0
  fi

  local token host
  token="$(plex_auth_token || true)"
  if [[ -z "${token}" ]]; then
    log "Plex token not found — complete Plex sign-in, then re-run homelab-setup"
    return 0
  fi

  host="${PLEX_INTERNAL_HOST:-plex}"
  if curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}/api/v3/notification" \
    | python3 -c "import json,sys; sys.exit(0 if any(n.get('implementation')=='PlexServer' for n in json.load(sys.stdin)) else 1)"; then
    log "${name} Plex notification already configured"
    return 0
  fi

  log "Configuring ${name} Plex library refresh notification"
  curl -sf --max-time 30 -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X POST "http://localhost:${port}/api/v3/notification" \
    -d "$(TOKEN="${token}" HOST="${host}" python3 - <<'PY'
import json, os
print(json.dumps({
    "name": "Plex",
    "implementation": "PlexServer",
    "configContract": "PlexServerSettings",
    "onDownload": True,
    "onUpgrade": True,
    "onRename": True,
    "fields": [
        {"name": "host", "value": os.environ["HOST"]},
        {"name": "port", "value": 32400},
        {"name": "useSsl", "value": False},
        {"name": "authToken", "value": os.environ["TOKEN"]},
        {"name": "updateLibrary", "value": True},
    ],
    "tags": [],
}))
PY
)" >/dev/null || {
    log "${name} Plex notification setup failed — configure Plex under Settings → Connect in ${name}"
    return 0
  }
}

trigger_plex_library_scan() {
  if ! docker ps --format '{{.Names}}' | grep -qx plex; then
    return 0
  fi

  local token
  token="$(plex_auth_token || true)"
  if [[ -z "${token}" ]]; then
    return 0
  fi

  log "Triggering Plex library scan"
  curl -sf --max-time 10 -X POST "http://localhost:32400/library/sections/3/refresh?X-Plex-Token=${token}" >/dev/null || true
  curl -sf --max-time 10 -X POST "http://localhost:32400/library/sections/4/refresh?X-Plex-Token=${token}" >/dev/null || true
}

main() {
  log "Homelab setup (COMMON_PATH=${COMMON_PATH})"
  setup_qbit_categories
  fix_radarr_media
  fix_sonarr_media
  ensure_root_folder 7878 "${RADARR_KEY}" Radarr "${COMMON_PATH}/radarr/movies"
  ensure_root_folder 8989 "${SONARR_KEY}" Sonarr "${COMMON_PATH}/sonarr/tv"
  ensure_remote_path_mapping 7878 "${RADARR_KEY}" Radarr
  ensure_remote_path_mapping 8989 "${SONARR_KEY}" Sonarr
  fix_download_client 7878 "${RADARR_KEY}" Radarr
  fix_download_client 8989 "${SONARR_KEY}" Sonarr
  ensure_same_disk_script 7878 "${RADARR_KEY}" Radarr
  ensure_same_disk_script 8989 "${SONARR_KEY}" Sonarr
  clear_stuck_queue 7878 "${RADARR_KEY}" Radarr
  clear_stuck_queue 8989 "${SONARR_KEY}" Sonarr
  trigger_download_scan
  write_recyclarr_secrets
  write_unpackerr_secrets
  remove_empty_plex_dir
  fix_plex_transcode_dir
  ensure_plex_notification 7878 "${RADARR_KEY}" Radarr
  ensure_plex_notification 8989 "${SONARR_KEY}" Sonarr
  trigger_plex_library_scan

  if docker ps --format '{{.Names}}' | grep -qx qbittorrent; then
    log "Restarting qBittorrent for category path changes"
    docker restart qbittorrent >/dev/null
    sleep 4
  fi

  run_recyclarr_sync
  set_default_quality_profiles
  trigger_download_scan
  log "Homelab setup complete"
}

main "$@"
