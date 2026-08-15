#!/bin/sh
# Runs inside plex-init (Alpine). Sets transcode off mergerfs before Plex starts.
# Host re-assert of Preferences.xml is stack_policy.plex_prefs (homelab-setup).
set -e
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
chown -R "${PUID}:${PGID}" /config /transcode
cache="/config/Library/Application Support/Plex Media Server/Cache"
mkdir -p "${cache}"
rm -rf "${cache}/Transcode"
ln -sf /transcode "${cache}/Transcode"
prefs="${cache}/../Preferences.xml"
if [ -f "${prefs}" ]; then
  if grep -q 'TranscoderTempDirectory="' "${prefs}"; then
    sed -i 's/TranscoderTempDirectory="[^"]*"/TranscoderTempDirectory="\/transcode"/' "${prefs}"
  else
    sed -i 's/<Preferences /<Preferences TranscoderTempDirectory="\/transcode" /' "${prefs}"
  fi
fi
echo "plex-init: transcode cache -> /transcode, chowned to ${PUID}:${PGID}"
