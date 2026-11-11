#!/usr/bin/env bash
# Copy SQLite app configs off the mergerfs pool onto APPDATA_PATH (SSD).
# Stop the stack first so WAL files are flushed. Idempotent; does not delete the pool copy.
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
APPDATA_PATH="${APPDATA_PATH:?APPDATA_PATH not set}"
SRC="${COMMON_PATH}/configs"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [[ "${APPDATA_PATH}" == "${COMMON_PATH}" || "${APPDATA_PATH}" == "${COMMON_PATH}"/* ]]; then
  echo "ERROR: APPDATA_PATH must not be on the media pool (${COMMON_PATH})" >&2
  exit 1
fi

if [[ ! -d "${SRC}" ]]; then
  echo "No ${SRC}; nothing to migrate"
  mkdir -p "${APPDATA_PATH}"
  chown "${PUID}:${PGID}" "${APPDATA_PATH}"
  exit 0
fi

mkdir -p "${APPDATA_PATH}"
echo "rsync stack configs ${SRC} -> ${APPDATA_PATH}"
for app in sonarr radarr plex tautulli bazarr jackett qbittorrent unpackerr jellyseerr jellyfin prowlarr panelarr homarr; do
  if [[ -d "${SRC}/${app}" ]]; then
    mkdir -p "${APPDATA_PATH}/${app}"
    rsync -a "${SRC}/${app}/" "${APPDATA_PATH}/${app}/"
  fi
done
chown -R "${PUID}:${PGID}" "${APPDATA_PATH}"
echo "Migrated appdata to ${APPDATA_PATH}; pool copy left at ${SRC}"
