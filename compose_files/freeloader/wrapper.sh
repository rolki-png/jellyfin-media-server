#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# In-container launcher for Plex Media Server on the LSIO image. The s6
# svc-plex run file execs this via s6-setuidgid abc. Adapted from upstream
# docker/wrapper.sh: preloads the feature-unlock .so. When PLEX_TRAFFIC_LOG is
# set to a writable path, also preloads plexmediaserver_traffic_logger.so for
# hook diagnostics (leave unset on the always-on server).
#
# LD_PRELOAD is exported last, immediately before exec, so the glibc shell
# helpers below (grep/awk/uname/tr) are not preloaded. The .so constructor
# (src/main.cpp) unsets LD_PRELOAD inside the musl PMS process, so PMS's
# helper children are unaffected. exec keeps PMS the s6-supervised process.
set -eu

export PLEX_MEDIA_SERVER_INFO_VENDOR="$(grep ^NAME= /etc/os-release | awk -F= '{print $2}' | tr -d '"')"
export PLEX_MEDIA_SERVER_INFO_MODEL="$(uname -m)"
export PLEX_MEDIA_SERVER_INFO_PLATFORM_VERSION="$(grep ^VERSION= /etc/os-release | awk -F= '{print $2}' | tr -d '"')"

CRACK="/usr/lib/plexmediaserver/lib/plexmediaserver_crack.so"
LOGGER="/usr/lib/plexmediaserver/lib/plexmediaserver_traffic_logger.so"
if [ -n "${PLEX_TRAFFIC_LOG:-}" ]; then
  export LD_PRELOAD="${CRACK}:${LOGGER}"
else
  export LD_PRELOAD="${CRACK}"
fi
exec "/usr/lib/plexmediaserver/Plex Media Server" "$@"
