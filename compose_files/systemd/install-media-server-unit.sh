#!/usr/bin/env bash
# Render media-server.service from this clone + compose_files/.env and install it.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"
TEMPLATE="${SCRIPT_DIR}/media-server.service.in"
DEST="${1:-/etc/systemd/system/media-server.service}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

COMMON_PATH="${COMMON_PATH:?COMMON_PATH not set}"
SSD="${SAME_DISK_SSD_ROOT:-/mnt/samsung-media/Isyrr}"
HDD="${SAME_DISK_HDD_ROOT:-/mnt/4tb-media-2/Isyrr}"
APPDATA_PATH="${APPDATA_PATH:-${SSD}/appdata}"

parent_of() {
  local p=$1
  p="${p%/}"
  dirname "${p}"
}

unique_mounts=""
for p in "$(parent_of "${COMMON_PATH}")" "$(parent_of "${SSD}")" "$(parent_of "${HDD}")" "$(parent_of "${APPDATA_PATH}")"; do
  case " ${unique_mounts} " in
    *" ${p} "*) ;;
    *) unique_mounts="${unique_mounts:+${unique_mounts} }${p}" ;;
  esac
done
mounts="${unique_mounts}"

render() {
  sed -e "s|@@COMPOSE_DIR@@|${COMPOSE_DIR}|g" -e "s|@@MOUNTS@@|${mounts}|g" "$1"
}

if [[ "${DEST}" == "-" ]]; then
  render "${TEMPLATE}"
  exit 0
fi

render "${TEMPLATE}" > "${DEST}"
if [[ "${DEST}" != "${SCRIPT_DIR}/media-server.service" ]]; then
  render "${TEMPLATE}" > "${SCRIPT_DIR}/media-server.service"
fi

if [[ "${DEST}" == /etc/systemd/system/* ]]; then
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Wrote ${DEST}; run as root to daemon-reload, or: sudo systemctl daemon-reload" >&2
    exit 1
  fi
  # Backup + health-alert timers ride along with the main unit.
  for tpl in "${SCRIPT_DIR}"/media-backup.*.in "${SCRIPT_DIR}"/media-monitor.*.in; do
    name="$(basename -- "${tpl}" .in)"
    render "${tpl}" > "/etc/systemd/system/${name}"
  done
  systemctl daemon-reload
  systemctl enable --now media-backup.timer media-monitor.timer
fi

echo "Installed ${DEST} (WorkingDirectory=${COMPOSE_DIR} RequiresMountsFor=${mounts})"
