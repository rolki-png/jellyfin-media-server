#!/usr/bin/env bash
# Build freeloader-plex:lsio: lscr.io/linuxserver/plex plus the Freeloader
# feature-unlock .so (LD_PRELOAD hook). The Dockerfile builder stage builds
# from compose_files/freeloader/vendor/ (authrequest/Freeloader at
# FREELOADER_COMMIT, currently 6efe3c8be82c0b4a3ac13ebd17a3fe101fc4927c, plus
# a local hook.cpp patch for per-user feature bits / Marker API). Upstream
# GitHub returns HTTP 451, so we do not clone at build time. Zig is fetched
# inside the builder image — no host zig needed.
#
# Plex updates are rebuilds against the version-locked base (PMS build pinned
# in compose_files/freeloader/Dockerfile as PLEX_BASE_IMAGE, matching the hook
# signatures): watchtower is disabled on plex because a pull would replace this
# local image with upstream and silently drop the unlock. Update flow: bump
# both pins once upstream supports a newer PMS, rerun this script, then
# up -d plex (command printed at the end).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
IMAGE="freeloader-plex:lsio"

cd "${COMPOSE_DIR}"
if [[ ! -f .env ]]; then
  echo "ERROR: missing ${COMPOSE_DIR}/.env (copy .env.example and customize)." >&2
  exit 1
fi

docker compose --env-file .env build --pull plex

echo
echo "Built ${IMAGE}:"
docker image inspect "${IMAGE}" --format '  id={{.Id}}'
docker image inspect "${IMAGE}" --format '  base={{index .Config.Labels "plex_patch.base"}}'
docker image inspect "${IMAGE}" --format '  freeloader_commit={{index .Config.Labels "plex_patch.freeloader_commit"}}'

if docker run --rm --entrypoint /bin/sh "${IMAGE}" -c 'test -f /usr/lib/plexmediaserver/TRANSCODE_PATCH_SKIPPED'; then
  echo
  echo "WARNING: transcode session-limit dd patch was SKIPPED (PMS version drift)."
  echo "The feature-unlock .so is installed and is the actual feature. Lifting the"
  echo "session cap needs offsets re-derived for this PMS build."
else
  echo "Transcode session-limit patch: applied."
fi

echo
echo "Apply with: cd ${COMPOSE_DIR} && docker compose --env-file .env up -d plex"
