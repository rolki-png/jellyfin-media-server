#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yaml"
DEFAULT_ENV_FILE="${SCRIPT_DIR}/.env"
EXAMPLE_ENV_FILE="${SCRIPT_DIR}/.env.example"
CI_MODE=false

if [[ "${1:-}" == "--ci" ]]; then
  CI_MODE=true
fi

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

warn() {
  echo "WARN: $*" >&2
}

check_command() {
  local cmd=$1
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    fail "Missing required command: ${cmd}"
  fi
}

check_command docker
if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose is not available. Install Docker Compose v2 plugin."
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  fail "Compose file not found: ${COMPOSE_FILE}"
fi

ENV_FILE="${DEFAULT_ENV_FILE}"
if [[ ! -f "${DEFAULT_ENV_FILE}" ]]; then
  if [[ "${CI_MODE}" == "true" && -f "${EXAMPLE_ENV_FILE}" ]]; then
    ENV_FILE="${EXAMPLE_ENV_FILE}"
    warn "No compose_files/.env found; using compose_files/.env.example for CI validation."
  else
    fail "Missing ${DEFAULT_ENV_FILE}. Copy compose_files/.env.example to compose_files/.env and customize values."
  fi
fi

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/scripts/load-dotenv.sh" "${ENV_FILE}"

required_vars=(COMMON_PATH APPDATA_PATH TZ)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    fail "Required variable '${var_name}' is empty in ${ENV_FILE}."
  fi
done

if [[ "${COMMON_PATH}" != /* ]]; then
  fail "COMMON_PATH must be an absolute path. Current value: '${COMMON_PATH}'"
fi

if [[ "${APPDATA_PATH}" != /* ]]; then
  fail "APPDATA_PATH must be an absolute path. Current value: '${APPDATA_PATH}'"
fi

path_must_not_be_under() {
  local child=$1 parent=$2 reason=$3
  if [[ "${child}" == "${parent}" || "${child}" == "${parent}"/* ]]; then
    fail "${reason}"
  fi
}

path_must_not_be_under "${APPDATA_PATH}" "${COMMON_PATH}" \
  "APPDATA_PATH must not be under COMMON_PATH (SQLite on mergerfs corrupts). APPDATA_PATH=${APPDATA_PATH}"

PLEX_TRANSCODE_DIR="${PLEX_TRANSCODE_DIR:-/var/lib/plex-transcode}"
if [[ "${PLEX_TRANSCODE_DIR}" != /* ]]; then
  fail "PLEX_TRANSCODE_DIR must be an absolute path. Current value: '${PLEX_TRANSCODE_DIR}'"
fi
# Pool is COMMON_PATH's parent (AGENTS.md / systemd README). Sibling paths like
# ${pool}/transcode still bind onto mergerfs even when outside the library tree.
MEDIA_POOL="$(dirname -- "${COMMON_PATH}")"
path_must_not_be_under "${PLEX_TRANSCODE_DIR}" "${COMMON_PATH}" \
  "PLEX_TRANSCODE_DIR must not be under COMMON_PATH (transcode on mergerfs stutters). PLEX_TRANSCODE_DIR=${PLEX_TRANSCODE_DIR}"
if [[ "${MEDIA_POOL}" != "/" ]]; then
  path_must_not_be_under "${PLEX_TRANSCODE_DIR}" "${MEDIA_POOL}" \
    "PLEX_TRANSCODE_DIR must not be under the media pool ${MEDIA_POOL} (parent of COMMON_PATH; mergerfs). PLEX_TRANSCODE_DIR=${PLEX_TRANSCODE_DIR}"
fi

if [[ -n "${PUID:-}" && ! "${PUID}" =~ ^[0-9]+$ ]]; then
  fail "PUID must be numeric. Current value: '${PUID}'"
fi

if [[ -n "${PGID:-}" && ! "${PGID}" =~ ^[0-9]+$ ]]; then
  fail "PGID must be numeric. Current value: '${PGID}'"
fi

if [[ "${CI_MODE}" == "false" && ! "${HOMARR_SECRET_ENCRYPTION_KEY:-}" =~ ^[0-9a-fA-F]{64}$ ]]; then
  fail "HOMARR_SECRET_ENCRYPTION_KEY must be 64 hex characters. Generate with: openssl rand -hex 32"
fi

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config >/dev/null

SCRIPT_PATH="${SCRIPT_DIR}/scripts/same-disk-import.sh"
if [[ ! -f "${SCRIPT_PATH}" ]]; then
  fail "Missing same-disk import script: ${SCRIPT_PATH}"
fi
if [[ ! -x "${SCRIPT_PATH}" ]]; then
  fail "same-disk import script is not executable: ${SCRIPT_PATH}"
fi

tmp_config="$(mktemp)"
if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config --format json >"${tmp_config}" 2>/dev/null; then
  :
else
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config >"${tmp_config}"
fi
PYTHONPATH="${SCRIPT_DIR}/scripts" python3 -m stack_policy check-compose "${tmp_config}" \
  || { rm -f "${tmp_config}"; fail "Radarr/Sonarr volume layout invalid (see above)"; }
rm -f "${tmp_config}"

if [[ "${CI_MODE}" == "false" && ! -d "${COMMON_PATH}" ]]; then
  warn "COMMON_PATH does not exist yet (${COMMON_PATH}). Create it before running 'docker compose up -d'."
fi
if [[ "${CI_MODE}" == "false" && ! -d "${APPDATA_PATH}" ]]; then
  warn "APPDATA_PATH does not exist yet (${APPDATA_PATH}). Run compose_files/scripts/migrate-appdata.sh after stopping the stack."
fi

if [[ "${CI_MODE}" == "false" && -d "${COMMON_PATH}/radarr/movies" && -d "${COMMON_PATH}/qbittorrent/downloads" ]]; then
  probe_dir="${COMMON_PATH}/.hardlink-probe-$$"
  mkdir -p "${probe_dir}/lib" "${probe_dir}/dl"
  echo probe > "${probe_dir}/dl/a.bin"
  if ln "${probe_dir}/dl/a.bin" "${probe_dir}/lib/a.bin" 2>/dev/null; then
    echo "Hardlink probe OK under ${COMMON_PATH}"
  else
    rm -rf "${probe_dir}"
    fail "Hardlink probe failed under ${COMMON_PATH} (library/downloads not same filesystem view)"
  fi
  rm -rf "${probe_dir}"
fi

if [[ "${CI_MODE}" == "false" ]]; then
  unit_src="${SCRIPT_DIR}/systemd/media-server.service.in"
  unit_dst="/etc/systemd/system/media-server.service"
  if [[ ! -f "${unit_src}" ]]; then
    fail "Missing ${unit_src}"
  fi
  if [[ ! -f "${unit_dst}" ]]; then
    warn "media-server.service is not installed yet at ${unit_dst}. Run: sudo bash compose_files/systemd/install-media-server-unit.sh"
  else
    if ! grep -q 'boot-ensure-hardlink-policy.sh' "${unit_dst}"; then
      fail "${unit_dst} is outdated (missing boot-ensure-hardlink-policy.sh). Reinstall from compose_files/systemd/"
    fi
    if ! grep -q 'RequiresMountsFor=' "${unit_dst}"; then
      fail "${unit_dst} is outdated (missing RequiresMountsFor). Reinstall from compose_files/systemd/"
    fi
    if ! systemctl is-enabled media-server >/dev/null 2>&1; then
      fail "media-server.service is not enabled (will not start on boot)"
    fi
  fi
  if findmnt -n "${COMMON_PATH}/qbittorrent/downloads" >/dev/null 2>&1; then
    fail "${COMMON_PATH}/qbittorrent/downloads is a separate mount; keep the SSD bind commented in /etc/fstab"
  fi
  if ! grep -E '^[^#]*fuse\.mergerfs' /etc/fstab | grep -q 'category.create=epmfs'; then
    warn "fstab mergerfs line should include category.create=epmfs (HDD-first creates)"
  fi
  transcode_probe="${PLEX_TRANSCODE_DIR}"
  while [[ ! -e "${transcode_probe}" && "${transcode_probe}" != "/" ]]; do
    transcode_probe="$(dirname -- "${transcode_probe}")"
  done
  transcode_fstype="$(findmnt -n -o FSTYPE --target "${transcode_probe}" 2>/dev/null || true)"
  if [[ "${transcode_fstype}" == *mergerfs* ]]; then
    fail "PLEX_TRANSCODE_DIR is on mergerfs (${transcode_fstype} at ${transcode_probe}). Use local disk."
  fi
fi

echo "Compose validation succeeded using env file: ${ENV_FILE}"
