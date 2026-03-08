#!/usr/bin/env bash
#
# Manually pull the latest images and recreate containers that have newer versions.
# Usage:
#   bash compose_files/update.sh                    # update the GPU stack
#   bash compose_files/update.sh --no-gpu           # update the non-GPU stack
#   bash compose_files/update.sh --service jellyfin # update a single service

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_GPU="${SCRIPT_DIR}/docker-compose-nvidia.yaml"
COMPOSE_NO_GPU="${SCRIPT_DIR}/docker-compose-no-gpu.yaml"

NO_GPU=false
SERVICES=()

usage() {
  echo "Usage: $0 [--no-gpu] [--service NAME ...]"
  echo ""
  echo "Options:"
  echo "  --no-gpu            Use the non-GPU compose file"
  echo "  --service NAME      Update only the specified service(s) (repeatable)"
  echo "  -h, --help          Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-gpu)
      NO_GPU=true
      shift
      ;;
    --service)
      SERVICES+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} not found. Copy .env.example to .env first." >&2
  exit 1
fi

if [[ "${NO_GPU}" == "true" ]]; then
  COMPOSE_FILE="${COMPOSE_NO_GPU}"
else
  COMPOSE_FILE="${COMPOSE_GPU}"
fi

echo "==> Pulling latest images..."
if [[ ${#SERVICES[@]} -gt 0 ]]; then
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" pull "${SERVICES[@]}"
else
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" pull
fi

echo "==> Recreating containers with updated images..."
if [[ ${#SERVICES[@]} -gt 0 ]]; then
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d "${SERVICES[@]}"
else
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d
fi

echo "==> Removing dangling images..."
docker image prune -f

echo "==> Update complete. Current container status:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
