#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_BASE="${SCRIPT_DIR}/docker-compose.yaml"
COMPOSE_GPU="${SCRIPT_DIR}/docker-compose.gpu.yaml"
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

if [[ ! -f "${COMPOSE_BASE}" ]]; then
  fail "Compose file not found: ${COMPOSE_BASE}"
fi

if [[ ! -f "${COMPOSE_GPU}" ]]; then
  fail "GPU overlay not found: ${COMPOSE_GPU}"
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

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

required_vars=(COMMON_PATH TZ)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    fail "Required variable '${var_name}' is empty in ${ENV_FILE}."
  fi
done

if [[ "${COMMON_PATH}" != /* ]]; then
  fail "COMMON_PATH must be an absolute path. Current value: '${COMMON_PATH}'"
fi

if [[ -n "${PUID:-}" && ! "${PUID}" =~ ^[0-9]+$ ]]; then
  fail "PUID must be numeric. Current value: '${PUID}'"
fi

if [[ -n "${PGID:-}" && ! "${PGID}" =~ ^[0-9]+$ ]]; then
  fail "PGID must be numeric. Current value: '${PGID}'"
fi

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_BASE}" config >/dev/null
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_BASE}" -f "${COMPOSE_GPU}" config >/dev/null

if [[ "${CI_MODE}" == "false" && ! -d "${COMMON_PATH}" ]]; then
  warn "COMMON_PATH does not exist yet (${COMMON_PATH}). Create it before running 'bash start.sh'."
fi

echo "Compose validation succeeded (base + GPU overlay) using env file: ${ENV_FILE}"
