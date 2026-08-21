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

parent_of() {
  local p=$1
  p="${p%/}"
  dirname "${p}"
}

unique_mounts=""
for p in "$(parent_of "${COMMON_PATH}")" "$(parent_of "${SSD}")" "$(parent_of "${HDD}")"; do
  case " ${unique_mounts} " in
    *" ${p} "*) ;;
    *) unique_mounts="${unique_mounts:+${unique_mounts} }${p}" ;;
  esac
done
mounts="${unique_mounts}"

unit="$(sed \
  -e "s|@@COMPOSE_DIR@@|${COMPOSE_DIR}|g" \
  -e "s|@@MOUNTS@@|${mounts}|g" \
  "${TEMPLATE}")"

if [[ "${DEST}" == "-" ]]; then
  printf '%s\n' "${unit}"
  exit 0
fi

printf '%s\n' "${unit}" > "${DEST}"
if [[ "${DEST}" != "${SCRIPT_DIR}/media-server.service" ]]; then
  printf '%s\n' "${unit}" > "${SCRIPT_DIR}/media-server.service"
fi

if [[ "${DEST}" == /etc/systemd/system/* ]]; then
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Wrote ${DEST}; run as root to daemon-reload, or: sudo systemctl daemon-reload" >&2
    exit 1
  fi
  systemctl daemon-reload
fi

echo "Installed ${DEST} (WorkingDirectory=${COMPOSE_DIR} RequiresMountsFor=${mounts})"
