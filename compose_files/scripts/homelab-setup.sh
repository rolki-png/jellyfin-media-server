#!/usr/bin/env bash
# Apply stack policy to Radarr, Sonarr, qBittorrent, Recyclarr, Unpackerr, Bazarr, Plex, and Tautulli (SIMKL).
# --mode=boot  hardlink + Plex host prefs only (systemd ExecStartPost; no queue wipes / qBit restart)
# --mode=all   full first-run / manual (default)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"
MODE="all"
if [[ "${1:-}" == "--mode=boot" ]]; then
  MODE="boot"
fi

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

export PYTHONPATH="${SCRIPT_DIR}"

policy() {
  python3 -m stack_policy "$@"
}

log() {
  echo "==> $*"
}

arr_get() {
  local port=$1 key=$2 path=$3
  curl -sf -H "X-Api-Key: ${key}" "http://localhost:${port}${path}"
}

arr_put() {
  local port=$1 key=$2 path=$3
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X PUT "http://localhost:${port}${path}" -d @- >/dev/null
}

arr_post() {
  local port=$1 key=$2 path=$3
  curl -sf -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
    -X POST "http://localhost:${port}${path}" -d @- >/dev/null
}

fix_media_management() {
  local port=$1 key=$2 name=$3
  log "Fixing ${name} media management"
  arr_get "${port}" "${key}" "/api/v3/config/mediamanagement" \
    | policy patch-media-mgmt \
    | arr_put "${port}" "${key}" "/api/v3/config/mediamanagement"
}

fix_download_client() {
  local port=$1 key=$2 name=$3
  log "Fixing ${name} qBittorrent download client"
  local current id
  current="$(arr_get "${port}" "${key}" "/api/v3/downloadclient")"
  id="$(CURRENT="${current}" python3 -c 'import json,os; print(json.loads(os.environ["CURRENT"])[0]["id"])')"
  printf '%s' "${current}" | policy patch-download-client \
    | arr_put "${port}" "${key}" "/api/v3/downloadclient/${id}"
}

ensure_root_folder() {
  local port=$1 key=$2 name=$3 path=$4
  log "Ensuring ${name} root folder ${path}"
  local existing
  existing="$(arr_get "${port}" "${key}" "/api/v3/rootfolder")"
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
  printf '%s' "{\"path\":\"${path}\"}" | arr_post "${port}" "${key}" "/api/v3/rootfolder"
}

ensure_remote_path_mapping() {
  local port=$1 key=$2 name=$3
  local host="${4:-qbittorrent}"
  local remote="${5:-/downloads/}"
  local local_path="${6:-${COMMON_PATH}/qbittorrent/downloads/}"

  log "Ensuring ${name} remote path mapping ${remote} -> ${local_path}"
  local existing
  existing="$(arr_get "${port}" "${key}" "/api/v3/remotepathmapping")"
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
  HOST="${host}" REMOTE="${remote}" LOCAL="${local_path}" python3 - <<'PY' \
    | arr_post "${port}" "${key}" "/api/v3/remotepathmapping"
import json, os
print(json.dumps({
    "host": os.environ["HOST"],
    "remotePath": os.environ["REMOTE"],
    "localPath": os.environ["LOCAL"],
}))
PY
}

ensure_same_disk_script() {
  local port=$1 key=$2 name=$3
  local script_path="/scripts/same-disk-import.sh"

  log "Ensuring ${name} same-disk Custom Script Connect"
  local existing match_id payload
  existing="$(arr_get "${port}" "${key}" "/api/v3/notification")"
  match_id="$(printf '%s' "${existing}" | policy custom-script-id "${script_path}" || true)"
  payload="$(policy custom-script-payload "${name}" "${script_path}")"

  if [[ -n "${match_id}" ]]; then
    PAYLOAD="${payload}" ID="${match_id}" python3 - <<'PY' \
      | arr_put "${port}" "${key}" "/api/v3/notification/${match_id}"
import json, os
body = json.loads(os.environ["PAYLOAD"])
body["id"] = int(os.environ["ID"])
print(json.dumps(body))
PY
    log "${name} same-disk script notification updated (id=${match_id})"
  else
    printf '%s' "${payload}" | arr_post "${port}" "${key}" "/api/v3/notification"
    log "${name} same-disk script notification created"
  fi
}

clear_stuck_queue() {
  local port=$1 key=$2 name=$3
  log "Clearing stuck ${name} queue items"
  local queue ids_json count
  queue="$(arr_get "${port}" "${key}" "/api/v3/queue?pageSize=200")"
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
  count="$(IDS="${ids_json}" python3 -c 'import json,os; print(len(json.loads(os.environ["IDS"])))')"
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
  printf '%s' "{\"name\":\"DownloadedMoviesScan\",\"path\":\"${downloads}\",\"importMode\":\"Auto\"}" \
    | arr_post 7878 "${RADARR_KEY}" "/api/v3/command" || true
  printf '%s' '{"name":"RefreshMonitoredDownloads"}' \
    | arr_post 7878 "${RADARR_KEY}" "/api/v3/command" || true
  printf '%s' "{\"name\":\"DownloadedEpisodesScan\",\"path\":\"${downloads}\",\"importMode\":\"Auto\"}" \
    | arr_post 8989 "${SONARR_KEY}" "/api/v3/command" || true
  printf '%s' '{"name":"RefreshMonitoredDownloads"}' \
    | arr_post 8989 "${SONARR_KEY}" "/api/v3/command" || true
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
  local radarr_name sonarr_name radarr_profile sonarr_profile tmp
  tmp="$(mktemp -d)"
  radarr_name="$(policy profile-name radarr)"
  sonarr_name="$(policy profile-name sonarr)"

  radarr_profile="$(arr_get 7878 "${RADARR_KEY}" "/api/v3/qualityprofile" | policy profile-id "${radarr_name}" || true)"
  sonarr_profile="$(arr_get 8989 "${SONARR_KEY}" "/api/v3/qualityprofile" | policy profile-id "${sonarr_name}" || true)"

  if [[ -n "${radarr_profile:-}" ]]; then
    arr_get 7878 "${RADARR_KEY}" "/api/v3/movie" \
      | policy editor-payload movie "${radarr_profile}" > "${tmp}/radarr-editor.json"
    if [[ "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["movieIds"]))' "${tmp}/radarr-editor.json")" -gt 0 ]]; then
      arr_put 7878 "${RADARR_KEY}" "/api/v3/movie/editor" < "${tmp}/radarr-editor.json"
      log "Updated Radarr movies to ${radarr_name}"
    fi
  fi

  if [[ -n "${sonarr_profile:-}" ]]; then
    arr_get 8989 "${SONARR_KEY}" "/api/v3/series" \
      | policy editor-payload series "${sonarr_profile}" > "${tmp}/sonarr-editor.json"
    if [[ "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["seriesIds"]))' "${tmp}/sonarr-editor.json")" -gt 0 ]]; then
      arr_put 8989 "${SONARR_KEY}" "/api/v3/series/editor" < "${tmp}/sonarr-editor.json"
      log "Updated Sonarr series to ${sonarr_name}"
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

bazarr_config_path() {
  local cfg="${COMMON_PATH}/configs/bazarr/config/config.yaml"
  if [[ -f "${cfg}" ]]; then
    echo "${cfg}"
    return 0
  fi
  cfg="${COMMON_PATH}/configs/bazarr/config.yaml"
  if [[ -f "${cfg}" ]]; then
    echo "${cfg}"
    return 0
  fi
  return 1
}

fix_bazarr() {
  local cfg
  if ! cfg="$(bazarr_config_path)"; then
    log "Bazarr config not found yet — start bazarr, then re-run homelab-setup"
    return 0
  fi
  log "Applying Direct Play subtitle policy to Bazarr (${cfg})"
  policy apply-bazarr-config "${cfg}" --sonarr-key "${SONARR_KEY}" --radarr-key "${RADARR_KEY}"
  if docker ps --format '{{.Names}}' | grep -qx bazarr; then
    docker restart bazarr >/dev/null
  fi
  ensure_bazarr_english_profile "${cfg}"
}

ensure_bazarr_english_profile() {
  local cfg=$1
  if ! docker ps --format '{{.Names}}' | grep -qx bazarr; then
    return 0
  fi
  local _wait
  for _wait in $(seq 1 30); do
    if curl -sf -o /dev/null "http://127.0.0.1:6767/"; then
      break
    fi
    sleep 1
  done
  log "Ensuring Bazarr English languages profile"
  CFG="${cfg}" python3 - <<'PY' || log "Bazarr English profile setup failed — open http://localhost:6767 Settings → Languages"
import json, os, pathlib, re, sys, urllib.request

from stack_policy.bazarr import english_settings_form

cfg = pathlib.Path(os.environ["CFG"])
text = cfg.read_text(encoding="utf-8")
match = re.search(r"^auth:\n  apikey:\s*(\S+)", text, re.M)
if not match:
    sys.exit(1)
apikey = match.group(1)
headers = {"X-API-KEY": apikey, "Accept": "application/json"}

req = urllib.request.Request(
    "http://127.0.0.1:6767/api/system/settings",
    data=english_settings_form(),
    method="POST",
    headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
)
with urllib.request.urlopen(req, timeout=60) as resp:
    if resp.status not in (200, 204):
        sys.exit(1)

def get(path):
    r = urllib.request.Request(f"http://127.0.0.1:6767/api{path}", headers=headers)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.load(resp)

def post(path):
    r = urllib.request.Request(
        f"http://127.0.0.1:6767/api{path}", data=b"", method="POST", headers=headers
    )
    with urllib.request.urlopen(r, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(path)

for row in get("/series").get("data") or []:
    if row.get("profileId") != 1:
        post(f"/series?seriesid={row['sonarrSeriesId']}&profileid=1")
for row in get("/movies").get("data") or []:
    if row.get("profileId") != 1:
        post(f"/movies?radarrid={row['radarrId']}&profileid=1")
PY
}

run_recyclarr_sync() {
  if ! docker ps --format '{{.Names}}' | grep -qx recyclarr; then
    log "Recyclarr not running yet (will sync after compose up)"
    return 0
  fi
  log "Running Recyclarr sync"
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

fix_plex_host() {
  local transcode_dir="${PLEX_TRANSCODE_DIR:-/var/lib/plex-transcode}"
  local prefs
  prefs="$(plex_preferences_path)"

  log "Ensuring Plex transcode directory (${transcode_dir})"
  mkdir -p "${transcode_dir}"
  chown "${PUID:-1000}:${PGID:-1000}" "${transcode_dir}"

  if [[ ! -f "${prefs}" ]]; then
    log "Plex preferences not found yet — skipping prefs rewrite"
    return 0
  fi

  policy apply-plex-prefs "${prefs}" --advertise "${PLEX_ADVERTISE_IP:-}"
  log "Set Plex TranscoderTempDirectory=/transcode advertise=${PLEX_ADVERTISE_IP:-unset}"
}

ensure_plex_notification() {
  local port=$1 key=$2 name=$3

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
  if arr_get "${port}" "${key}" "/api/v3/notification" \
    | python3 -c "import json,sys; sys.exit(0 if any(n.get('implementation')=='PlexServer' for n in json.load(sys.stdin)) else 1)"; then
    log "${name} Plex notification already configured"
    return 0
  fi

  log "Configuring ${name} Plex library refresh notification"
  local body
  body="$(TOKEN="${token}" HOST="${host}" python3 - <<'PY'
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
)"
  if ! printf '%s' "${body}" | curl -sf --max-time 30 -H "X-Api-Key: ${key}" -H "Content-Type: application/json" \
      -X POST "http://localhost:${port}/api/v3/notification" -d @- >/dev/null; then
    log "${name} Plex notification setup failed — configure Plex under Settings → Connect in ${name}"
    return 0
  fi
}

tautulli_config_path() {
  echo "${COMMON_PATH}/configs/tautulli/config.ini"
}

wait_for_tautulli() {
  local _wait
  for _wait in $(seq 1 40); do
    if curl -sf -o /dev/null "http://127.0.0.1:8181/"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

ensure_tautulli_simkl() {
  local cfg prefs
  cfg="$(tautulli_config_path)"
  mkdir -p "${COMMON_PATH}/configs/tautulli"
  chown "${PUID:-1000}:${PGID:-1000}" "${COMMON_PATH}/configs/tautulli"

  if ! docker ps --format '{{.Names}}' | grep -qx tautulli; then
    log "Tautulli not running — start it, then re-run homelab-setup for SIMKL"
    return 0
  fi

  if ! wait_for_tautulli; then
    log "Tautulli UI not ready — skip SIMKL webhook setup"
    return 0
  fi

  prefs="$(plex_preferences_path)"
  if [[ ! -f "${prefs}" || ! -f "${cfg}" ]]; then
    log "Tautulli or Plex config missing — complete first start, then re-run homelab-setup"
    return 0
  fi

  local changed
  changed="$(PREFS="${prefs}" INI="${cfg}" HOST="${PLEX_INTERNAL_HOST:-plex}" python3 - <<'PY'
import os
from pathlib import Path
from stack_policy.tautulli import apply_pms_ini, plex_connection_from_prefs

prefs = Path(os.environ["PREFS"]).read_text(encoding="utf-8")
ini_path = Path(os.environ["INI"])
ini = ini_path.read_text(encoding="utf-8")
conn = plex_connection_from_prefs(prefs)
updated = apply_pms_ini(
    ini,
    token=conn["token"],
    identifier=conn["identifier"],
    name=conn["name"],
    host=os.environ["HOST"],
)
if updated != ini:
    ini_path.write_text(updated, encoding="utf-8")
    print("changed")
else:
    print("ok")
PY
)"
  if [[ "${changed}" == "changed" ]]; then
    log "Pointed Tautulli at Plex (${PLEX_INTERNAL_HOST:-plex}:32400) — restarting Tautulli (not Plex)"
    docker restart tautulli >/dev/null
    if ! wait_for_tautulli; then
      log "Tautulli did not come back after restart"
      return 0
    fi
  fi

  local webhook="${SIMKL_PLEX_WEBHOOK_URL:-}"
  if [[ -z "${webhook}" ]]; then
    log "SIMKL: copy your webhook URL from https://simkl.com/apps/plex into compose_files/.env as SIMKL_PLEX_WEBHOOK_URL, then re-run homelab-setup"
    return 0
  fi

  log "Ensuring Tautulli SIMKL webhook notifier"
  INI="${cfg}" WEBHOOK="${webhook}" python3 - <<'PY' || log "Tautulli SIMKL webhook setup failed — add a Webhook agent in Tautulli (Watched trigger)"
import json, os, pathlib, sys, urllib.error, urllib.parse, urllib.request

from stack_policy.tautulli import (
    WEBHOOK_AGENT_ID,
    find_simkl_notifier_id,
    tautulli_api_key,
    webhook_notifier_fields,
    webhook_url_from_config,
)

api_key = tautulli_api_key(pathlib.Path(os.environ["INI"]).read_text(encoding="utf-8"))
if not api_key:
    sys.exit(1)
webhook = os.environ["WEBHOOK"].strip()
base = "http://127.0.0.1:8181/api/v2"

def tautulli(cmd, extra=None):
    params = {"apikey": api_key, "cmd": cmd}
    if extra:
        params.update(extra)
    url = base + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.load(resp)
    if payload.get("response", {}).get("result") != "success":
        raise RuntimeError(payload)
    return payload["response"].get("data")

notifiers = tautulli("get_notifiers") or []
notifier_id = find_simkl_notifier_id(notifiers)
if notifier_id is None:
    tautulli("add_notifier_config", {"agent_id": str(WEBHOOK_AGENT_ID)})
    notifiers = tautulli("get_notifiers") or []
    notifier_id = find_simkl_notifier_id(notifiers)
    if notifier_id is None:
        # Newly added webhook has an empty friendly_name until set_notifier_config.
        webhooks = [n for n in notifiers if n.get("agent_id") == WEBHOOK_AGENT_ID or n.get("agent_name") == "webhook"]
        if len(webhooks) == 1:
            notifier_id = int(webhooks[0]["id"])
        else:
            unnamed = [n for n in webhooks if not n.get("friendly_name")]
            if len(unnamed) != 1:
                raise RuntimeError("could not identify new webhook notifier")
            notifier_id = int(unnamed[0]["id"])

config = tautulli("get_notifier_config", {"notifier_id": str(notifier_id)}) or {}
if webhook_url_from_config(config) == webhook:
    sys.exit(0)

fields = webhook_notifier_fields(webhook)
fields["notifier_id"] = str(notifier_id)
tautulli("set_notifier_config", fields)
PY
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

apply_hardlink_policy() {
  setup_qbit_categories
  fix_media_management 7878 "${RADARR_KEY}" Radarr
  fix_media_management 8989 "${SONARR_KEY}" Sonarr
  ensure_root_folder 7878 "${RADARR_KEY}" Radarr "${COMMON_PATH}/radarr/movies"
  ensure_root_folder 8989 "${SONARR_KEY}" Sonarr "${COMMON_PATH}/sonarr/tv"
  ensure_remote_path_mapping 7878 "${RADARR_KEY}" Radarr
  ensure_remote_path_mapping 8989 "${SONARR_KEY}" Sonarr
  fix_download_client 7878 "${RADARR_KEY}" Radarr
  fix_download_client 8989 "${SONARR_KEY}" Sonarr
  ensure_same_disk_script 7878 "${RADARR_KEY}" Radarr
  ensure_same_disk_script 8989 "${SONARR_KEY}" Sonarr
  write_recyclarr_secrets
  write_unpackerr_secrets
  remove_empty_plex_dir
  fix_plex_host
  ensure_plex_notification 7878 "${RADARR_KEY}" Radarr
  ensure_plex_notification 8989 "${SONARR_KEY}" Sonarr
  fix_bazarr
  ensure_tautulli_simkl
}

main() {
  log "Homelab setup mode=${MODE} COMMON_PATH=${COMMON_PATH}"
  apply_hardlink_policy

  if [[ "${MODE}" == "boot" ]]; then
    log "Homelab setup complete (boot: skipped queue/scan/qBit restart/Recyclarr/profiles)"
    return 0
  fi

  clear_stuck_queue 7878 "${RADARR_KEY}" Radarr
  clear_stuck_queue 8989 "${SONARR_KEY}" Sonarr
  trigger_download_scan
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

main
