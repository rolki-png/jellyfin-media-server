#!/usr/bin/env bash
# Scan qBittorrent download folders and auto-import via Radarr/Sonarr manual import API.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

COMMON_PATH="${COMMON_PATH:?COMMON_PATH not set}"
DOWNLOADS="${COMMON_PATH}/qbittorrent/downloads"
RADARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${COMMON_PATH}/configs/radarr/config.xml")"
SONARR_KEY="$(grep -oP '(?<=<ApiKey>)[^<]+' "${COMMON_PATH}/configs/sonarr/config.xml")"

log() { echo "==> $*"; }

import_radarr_folder() {
  local folder=$1
  local response imported
  response="$(curl -sf -H "X-Api-Key: ${RADARR_KEY}" \
    "http://localhost:7878/api/v3/manualimport?folder=${folder}&filterExistingFiles=true" 2>/dev/null || echo '[]')"
  imported="$(RESPONSE="${response}" python3 - <<'PY'
import json, os
items = json.loads(os.environ.get("RESPONSE") or "[]")
ready = []
for item in items:
    if not item.get("movie"):
        continue
    entry = {
        "path": item["path"],
        "movieId": item["movie"]["id"],
        "quality": item["quality"],
        "languages": item.get("languages") or [{"id": 1, "name": "English"}],
        "releaseGroup": item.get("releaseGroup"),
        "indexerFlags": item.get("indexerFlags", 0),
    }
    ready.append(entry)
print(json.dumps(ready))
PY
)"
  local count
  count="$(COUNT="${imported}" python3 -c 'import json,os; print(len(json.loads(os.environ["COUNT"])))')"
  if [[ "${count}" -eq 0 ]]; then
    return 0
  fi
  curl -sf -H "X-Api-Key: ${RADARR_KEY}" -H "Content-Type: application/json" \
    -X POST "http://localhost:7878/api/v3/manualimport" \
    -d "{\"importMode\":\"Auto\",\"files\":${imported}}" >/dev/null
  log "Radarr imported ${count} file(s) from ${folder}"
}

import_sonarr_folder() {
  local folder=$1
  local response imported
  response="$(curl -sf -H "X-Api-Key: ${SONARR_KEY}" \
    "http://localhost:8989/api/v3/manualimport?folder=${folder}&filterExistingFiles=true" 2>/dev/null || echo '[]')"
  imported="$(RESPONSE="${response}" python3 - <<'PY'
import json, os
items = json.loads(os.environ.get("RESPONSE") or "[]")
ready = []
for item in items:
    if not item.get("episodes"):
        continue
    entry = {
        "path": item["path"],
        "seriesId": item["series"]["id"],
        "episodeIds": [ep["id"] for ep in item["episodes"]],
        "quality": item["quality"],
        "languages": item.get("languages") or [{"id": 1, "name": "English"}],
        "releaseGroup": item.get("releaseGroup"),
        "indexerFlags": item.get("indexerFlags", 0),
    }
    ready.append(entry)
print(json.dumps(ready))
PY
)"
  local count
  count="$(COUNT="${imported}" python3 -c 'import json,os; print(len(json.loads(os.environ["COUNT"])))')"
  if [[ "${count}" -eq 0 ]]; then
    return 0
  fi
  curl -sf -H "X-Api-Key: ${SONARR_KEY}" -H "Content-Type: application/json" \
    -X POST "http://localhost:8989/api/v3/manualimport" \
    -d "{\"importMode\":\"Auto\",\"files\":${imported}}" >/dev/null
  log "Sonarr imported ${count} file(s) from ${folder}"
}

log "Scanning ${DOWNLOADS} for importable media"
while IFS= read -r -d '' dir; do
  container_path="/downloads/${dir#"${DOWNLOADS}/"}"
  import_radarr_folder "${container_path}" || true
  import_sonarr_folder "${container_path}" || true
done < <(find "${DOWNLOADS}" -mindepth 1 -maxdepth 1 -type d -print0)

log "Import scan complete"
