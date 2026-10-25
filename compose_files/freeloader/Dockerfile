# syntax=docker/dockerfile:1.7
#
# lscr.io/linuxserver/plex + Freeloader feature-unlock (LD_PRELOAD .so).
# Built by compose_files/scripts/build-freeloader-plex.sh -> freeloader-plex:lsio.
# Adapted from upstream docker/Dockerfile.linuxserver (authrequest/Freeloader).
#
# Stage 1 clones the pinned Freeloader commit and cross-compiles
# plexmediaserver_crack.so against musl with zig. The musl build is mandatory:
# Plex bundles its own musl libc and a glibc-built .so exits PMS 127.
# Stage 2 layers onto the LSIO image: copies the .so + wrapper, points the s6
# svc-plex run file at the wrapper (keeps s6-setuidgid abc), then tries the
# upstream transcode session-limit dd patch. Those offsets are pinned to one
# PMS build, so byte mismatches warn loudly and skip instead of failing the
# build. The .so unlock is the feature; the dd patch only lifts session caps.

# Pinned to the PMS build the upstream hook signatures and dd offsets were
# derived from: 1.43.2.10687-563d026ea, the LSIO :latest of early June 2026
# when the pinned Freeloader commit landed (upstream docs example pins the
# plexinc image; the same build line applies here). On PMS 1.43.4.10903 the
# pinned commit's .so loads but PMS crash-loops within a minute, because the
# byte-pattern signatures match wrong sites. A "Plex update" means upstream
# re-deriving signatures for a newer PMS, then bumping both pins.
ARG PLEX_BASE_IMAGE=lscr.io/linuxserver/plex:1.43.2.10687-563d026ea-ls313
# Vendored authrequest/Freeloader at this commit (plus local hook.cpp patch).
# GitHub returns HTTP 451 for the upstream repo, so we build from vendor/.
ARG FREELOADER_COMMIT=6efe3c8be82c0b4a3ac13ebd17a3fe101fc4927c

# ── Stage 1: vendored Freeloader, build the musl .so with zig ─────────────
FROM debian:bookworm-slim AS builder

ARG FREELOADER_COMMIT
ARG ZIG_VERSION=0.13.0
ARG DEBIAN_FRONTEND=noninteractive
# binutils gives build.sh a real readelf so its glibc-symbol ABI gate cannot
# silently no-op (bookworm-slim ships without it). xz-utils unpacks Zydis.c.xz.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        binutils ca-certificates curl xz-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN mkdir -p /src/toolchain \
 && curl -fsSL \
      "https://ziglang.org/download/${ZIG_VERSION}/zig-linux-x86_64-${ZIG_VERSION}.tar.xz" \
      -o /tmp/zig.tar.xz \
 && tar -C /src/toolchain --strip-components=1 -xf /tmp/zig.tar.xz \
 && rm /tmp/zig.tar.xz
ENV PATH="/src/toolchain:${PATH}"

# vendor/ is Freeloader ${FREELOADER_COMMIT} with a local hook.cpp patch that
# also hooks the modern per-user feature-bit lookup (Marker / Skip Intro).
COPY vendor/ /src/freeloader/
RUN test -f /src/freeloader/VERSION \
 && grep -q "${FREELOADER_COMMIT}" /src/freeloader/VERSION \
 && xz -d /src/freeloader/third_party/zydis/Zydis.c.xz \
 && cd /src/freeloader \
 && bash build.sh \
 && test -s build/plexmediaserver_crack.so \
 && test -s build/plexmediaserver_traffic_logger.so

# ── Stage 2: patch the LSIO plex image ─────────────────────────────────────
FROM ${PLEX_BASE_IMAGE} AS runtime

ARG PLEX_BASE_IMAGE
ARG FREELOADER_COMMIT
LABEL org.opencontainers.image.title="freeloader-plex" \
      org.opencontainers.image.source="https://github.com/authrequest/Freeloader" \
      plex_patch.base="${PLEX_BASE_IMAGE}" \
      plex_patch.freeloader_commit="${FREELOADER_COMMIT}"

# Fail loud on an unfamiliar LSIO layout (upstream sanity checks, kept fatal).
RUN set -eux; \
    PMS="/usr/lib/plexmediaserver/Plex Media Server"; \
    PMS_LIB="/usr/lib/plexmediaserver/lib"; \
    RUN_SCRIPT="/etc/s6-overlay/s6-rc.d/svc-plex/run"; \
    [ -x "${PMS}" ]        || { echo "patcher: missing ${PMS} in ${PLEX_BASE_IMAGE}"; exit 1; }; \
    [ -d "${PMS_LIB}" ]    || { echo "patcher: missing ${PMS_LIB}/ in ${PLEX_BASE_IMAGE}"; exit 1; }; \
    [ -f "${RUN_SCRIPT}" ] || { echo "patcher: missing ${RUN_SCRIPT} in ${PLEX_BASE_IMAGE}"; exit 1; }

COPY --from=builder /src/freeloader/build/plexmediaserver_crack.so \
                    /usr/lib/plexmediaserver/lib/plexmediaserver_crack.so
COPY --from=builder /src/freeloader/build/plexmediaserver_traffic_logger.so \
                    /usr/lib/plexmediaserver/lib/plexmediaserver_traffic_logger.so
COPY wrapper.sh /usr/lib/plexmediaserver/plex-crack-wrapper.sh

# ABI gate: load the PMS binary under its bundled musl loader with the .so
# preloaded, the same scope the real exec gets. The .so leaves operator
# new/delete undefined on purpose (PMS's bundled libc++ provides them), so a
# standalone --list of the .so fails by design. Keeps s6-setuidgid abc so PMS
# still runs as the LSIO abc user, not root.
RUN set -eux; \
    chmod 0755 /usr/lib/plexmediaserver/plex-crack-wrapper.sh; \
    LD_PRELOAD=/usr/lib/plexmediaserver/lib/plexmediaserver_crack.so \
        /usr/lib/plexmediaserver/lib/ld-musl-x86_64.so.1 --list \
        "/usr/lib/plexmediaserver/Plex Media Server" >/dev/null; \
    RUN_SCRIPT="/etc/s6-overlay/s6-rc.d/svc-plex/run"; \
    cp "${RUN_SCRIPT}" "${RUN_SCRIPT}.orig"; \
    printf '#!/usr/bin/with-contenv bash\nexec s6-setuidgid abc /usr/lib/plexmediaserver/plex-crack-wrapper.sh\n' \
        > "${RUN_SCRIPT}"; \
    chmod 0755 "${RUN_SCRIPT}"; \
    grep -q plex-crack-wrapper "${RUN_SCRIPT}"

# Best-effort: upstream's in-place dd patch disabling transcode session limits.
# Offsets were derived from one specific PMS build; on any byte mismatch warn
# loudly, leave a marker the build script reports, and ship without the patch.
RUN set -eu; \
    PMS="/usr/lib/plexmediaserver/Plex Media Server"; \
    MARKER=/usr/lib/plexmediaserver/TRANSCODE_PATCH_SKIPPED; \
    rm -f "${MARKER}"; \
    rd() { dd if="${PMS}" bs=1 skip="$1" count="$2" 2>/dev/null | od -A n -t x1 | tr -d ' \n'; }; \
    ok=1; \
    for spec in "18624607 2 7e0c" "18624781 2 7e08" "18624793 2 7e08" \
                "18624674 6 0f8fc2f6ffff" "18624682 6 0f8f1ef7ffff" "18624630 6 0f8f9f000000"; do \
      set -- ${spec}; \
      [ "$(rd "$1" "$2")" = "$3" ] || { echo "transcode-patch: byte mismatch at offset $1 (want $3)"; ok=0; }; \
    done; \
    if [ "${ok}" = "1" ]; then \
      printf '\353\014' | dd of="${PMS}" bs=1 seek=18624607 conv=notrunc 2>/dev/null; \
      printf '\353\010' | dd of="${PMS}" bs=1 seek=18624781 conv=notrunc 2>/dev/null; \
      printf '\353\010' | dd of="${PMS}" bs=1 seek=18624793 conv=notrunc 2>/dev/null; \
      printf '\220\220\220\220\220\220' | dd of="${PMS}" bs=1 seek=18624674 conv=notrunc 2>/dev/null; \
      printf '\220\220\220\220\220\220' | dd of="${PMS}" bs=1 seek=18624682 conv=notrunc 2>/dev/null; \
      printf '\220\220\220\220\220\220' | dd of="${PMS}" bs=1 seek=18624630 conv=notrunc 2>/dev/null; \
      echo "transcode-patch: applied (session limits disabled)"; \
    else \
      echo "============================================================"; \
      echo "WARNING: transcode session-limit dd patch SKIPPED."; \
      echo "PMS bytes do not match the pinned offsets (version drift)."; \
      echo "The feature-unlock .so is installed and is the actual feature."; \
      echo "============================================================"; \
      { echo "Transcode session-limit patch skipped: patch-site bytes did not match."; \
        echo "PMS version: $("${PMS}" --version 2>/dev/null || echo unknown)"; \
        echo "The feature-unlock LD_PRELOAD hook is installed; only the session-cap lift is missing."; \
      } > "${MARKER}"; \
    fi
