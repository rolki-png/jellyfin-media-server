#!/usr/bin/env bash
# Nightly restic snapshot of APPDATA_PATH. Run by media-backup.timer as root.
# SQLite files are copied with `sqlite3 .backup` first so a live write never
# lands half-way through the snapshot; the raw *.db files are then excluded.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

APPDATA_PATH="${APPDATA_PATH:?APPDATA_PATH not set}"
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:?RESTIC_REPOSITORY not set}"
export RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/etc/media-server/restic.pass}"
STATE_DIR="${STATE_DIRECTORY:-/var/lib/media-server}"
SNAP_DIR="${STATE_DIR}/sqlite-snapshots"

restic cat config >/dev/null 2>&1 || restic init
restic unlock
export RESTIC_RETRY_LOCK=10m

rm -rf "${SNAP_DIR}"
mkdir -p "${SNAP_DIR}"
while IFS= read -r -d '' db; do
  rel="${db#"${APPDATA_PATH}"/}"
  mkdir -p "${SNAP_DIR}/$(dirname -- "${rel}")"
  sqlite3 -readonly "${db}" ".timeout 30000" ".backup '${SNAP_DIR}/${rel}'"
done < <(find "${APPDATA_PATH}" -type f \( -name '*.db' -o -name 'db.sqlite3' \) \
  -not -path '*/Backups/*' -not -path '*/corrupt-*' -not -name 'logs.db' -print0)

live="${APPDATA_PATH}/**"
restic backup --tag appdata --one-file-system \
  --exclude "${live}/*.db" --exclude "${live}/db.sqlite3" --exclude "${live}/*.db-wal" --exclude "${live}/*.db-shm" \
  --exclude '*/Plex Media Server/Cache' --exclude '*/Plex Media Server/Crash Reports' \
  --exclude '*/Plex Media Server/Logs' --exclude '*/logs' --exclude '*/corrupt-*' \
  "${APPDATA_PATH}" "${SNAP_DIR}"

restic forget --tag appdata --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
restic ls --recursive latest "${SNAP_DIR}" | grep '\.db$' >/dev/null || { echo "ERROR: snapshot has no SQLite copies" >&2; exit 1; }
touch "${STATE_DIR}/last-backup"
rm -rf "${SNAP_DIR}"
