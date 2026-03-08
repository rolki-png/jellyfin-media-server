#!/usr/bin/env bash
#
# Start the media-server stack with automatic GPU detection.
#
# If an NVIDIA GPU and the nvidia-container-toolkit are available, Jellyfin and
# Plex are launched with hardware-transcoding support.  Otherwise the stack
# falls back to CPU-only transcoding — no manual flag needed.
#
# Usage:
#   bash compose_files/start.sh              # start the full stack
#   bash compose_files/start.sh --force-gpu  # force GPU mode (fail if unavailable)
#   bash compose_files/start.sh --force-cpu  # force CPU-only mode
#   bash compose_files/start.sh -- <args>    # pass extra args to docker compose

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_BASE="${SCRIPT_DIR}/docker-compose.yaml"
COMPOSE_GPU="${SCRIPT_DIR}/docker-compose.gpu.yaml"
ENV_FILE="${SCRIPT_DIR}/.env"

FORCE_MODE=""
EXTRA_ARGS=()

usage() {
  echo "Usage: $0 [--force-gpu | --force-cpu] [-- <docker-compose-args>]"
  echo ""
  echo "Options:"
  echo "  --force-gpu   Force GPU mode (fails if NVIDIA is unavailable)"
  echo "  --force-cpu   Force CPU-only mode even when a GPU is present"
  echo "  -- <args>     Pass remaining arguments to docker compose up"
  echo "  -h, --help    Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force-gpu) FORCE_MODE="gpu"; shift ;;
    --force-cpu) FORCE_MODE="cpu"; shift ;;
    -h|--help) usage ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
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

# ---------------------------------------------------------------------------
# GPU detection
# ---------------------------------------------------------------------------
has_nvidia_gpu() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

USE_GPU=false

case "${FORCE_MODE}" in
  gpu)
    if ! has_nvidia_gpu; then
      echo "ERROR: --force-gpu specified but nvidia-smi is not available or failing." >&2
      exit 1
    fi
    USE_GPU=true
    ;;
  cpu)
    USE_GPU=false
    ;;
  *)
    if has_nvidia_gpu; then
      USE_GPU=true
    fi
    ;;
esac

# ---------------------------------------------------------------------------
# Build the compose command
# ---------------------------------------------------------------------------
COMPOSE_CMD=(docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_BASE}")

if [[ "${USE_GPU}" == "true" ]]; then
  COMPOSE_CMD+=(-f "${COMPOSE_GPU}")
  echo "==> NVIDIA GPU detected — starting with hardware-transcoding support"
else
  echo "==> No NVIDIA GPU detected — starting with CPU-only transcoding"
fi

"${COMPOSE_CMD[@]}" up -d "${EXTRA_ARGS[@]}"

echo ""
echo "==> Stack is running:"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
