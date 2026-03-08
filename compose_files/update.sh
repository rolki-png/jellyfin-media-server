#!/usr/bin/env bash
#
# Pull the latest images and recreate containers that have newer versions.
# GPU detection is automatic (same logic as start.sh).
#
# Usage:
#   bash compose_files/update.sh                    # update all services
#   bash compose_files/update.sh --service jellyfin # update a single service
#   bash compose_files/update.sh --force-cpu        # ignore GPU even if present

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_BASE="${SCRIPT_DIR}/docker-compose.yaml"
COMPOSE_GPU="${SCRIPT_DIR}/docker-compose.gpu.yaml"

FORCE_MODE=""
SERVICES=()

usage() {
  echo "Usage: $0 [--force-gpu | --force-cpu] [--service NAME ...]"
  echo ""
  echo "Options:"
  echo "  --force-gpu         Force GPU mode (fails if NVIDIA is unavailable)"
  echo "  --force-cpu         Force CPU-only mode even when a GPU is present"
  echo "  --service NAME      Update only the specified service(s) (repeatable)"
  echo "  -h, --help          Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force-gpu) FORCE_MODE="gpu"; shift ;;
    --force-cpu) FORCE_MODE="cpu"; shift ;;
    --service)   SERVICES+=("$2"); shift 2 ;;
    -h|--help)   usage ;;
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

# ---------------------------------------------------------------------------
# GPU detection (mirrors start.sh)
# ---------------------------------------------------------------------------
has_nvidia_gpu() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

USE_GPU=false
case "${FORCE_MODE}" in
  gpu)
    if ! has_nvidia_gpu; then
      echo "ERROR: --force-gpu specified but nvidia-smi is not available." >&2
      exit 1
    fi
    USE_GPU=true
    ;;
  cpu) USE_GPU=false ;;
  *)   has_nvidia_gpu && USE_GPU=true ;;
esac

COMPOSE_CMD=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_BASE}")
if [[ "${USE_GPU}" == "true" ]]; then
  COMPOSE_CMD+=(-f "${COMPOSE_GPU}")
  echo "==> NVIDIA GPU detected — updating with GPU overlay"
else
  echo "==> No NVIDIA GPU detected — updating CPU-only stack"
fi

# ---------------------------------------------------------------------------
# Pull → recreate → prune
# ---------------------------------------------------------------------------
echo "==> Pulling latest images..."
if [[ ${#SERVICES[@]} -gt 0 ]]; then
  "${COMPOSE_CMD[@]}" pull "${SERVICES[@]}"
else
  "${COMPOSE_CMD[@]}" pull
fi

echo "==> Recreating containers with updated images..."
if [[ ${#SERVICES[@]} -gt 0 ]]; then
  "${COMPOSE_CMD[@]}" up -d "${SERVICES[@]}"
else
  "${COMPOSE_CMD[@]}" up -d
fi

echo "==> Removing dangling images..."
docker image prune -f

echo "==> Update complete. Current container status:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
