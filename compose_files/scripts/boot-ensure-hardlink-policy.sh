#!/usr/bin/env bash
# Called from media-server.service ExecStartPost.
# Waits for Radarr/Sonarr, then re-applies hardlink/seeding/Connect settings so
# policy survives reboot, docker restart, and accidental UI drift.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${COMPOSE_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

COMMON_PATH="${COMMON_PATH:-/mnt/combined-media/Isyrr}"
RADARR_CONFIG="${COMMON_PATH}/configs/radarr/config.xml"
SONARR_CONFIG="${COMMON_PATH}/configs/sonarr/config.xml"

log() { echo "boot-ensure-hardlink-policy: $*" >&2; }

# Disk / mergerfs sanity (fail loud so journald shows why policy could not apply).
for p in "${COMMON_PATH}" \
         "${SAME_DISK_SSD_ROOT:-/mnt/samsung-media/Isyrr}" \
         "${SAME_DISK_HDD_ROOT:-/mnt/4tb-media-2/Isyrr}"; do
  if [[ ! -d "${p}" ]]; then
    log "ERROR: missing path ${p}"
    exit 1
  fi
done

# Downloads must NOT be a separate bind mount (SSD pin breaks HDD-first + hardlinks).
if findmnt -n "${COMMON_PATH}/qbittorrent/downloads" >/dev/null 2>&1; then
  src="$(findmnt -n -o SOURCE "${COMMON_PATH}/qbittorrent/downloads" || true)"
  log "ERROR: ${COMMON_PATH}/qbittorrent/downloads is a separate mount (${src})"
  log "Comment out the SSD downloads bind in /etc/fstab, then: sudo umount '${COMMON_PATH}/qbittorrent/downloads'"
  exit 1
fi

if [[ ! -f "${RADARR_CONFIG}" || ! -f "${SONARR_CONFIG}" ]]; then
  log "ERROR: missing *arr config.xml under ${COMMON_PATH}/configs"
  exit 1
fi

log "waiting for Radarr/Sonarr APIs"
ok=0
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null http://127.0.0.1:7878/ping \
    && curl -sf -o /dev/null http://127.0.0.1:8989/ping; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "${ok}" -ne 1 ]]; then
  log "ERROR: Radarr/Sonarr did not become ready in time"
  exit 1
fi

log "re-applying hardlink policy via homelab-setup.sh --mode=boot"
exec "${SCRIPT_DIR}/homelab-setup.sh" --mode=boot
