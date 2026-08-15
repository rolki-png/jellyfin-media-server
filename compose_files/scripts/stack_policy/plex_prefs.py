"""Plex Preferences.xml mutations for stream-safe host settings."""

from __future__ import annotations

import re

TRANSCODER_TEMP = "/transcode"


def ensure_transcoder_temp(xml: str, target: str = TRANSCODER_TEMP) -> str:
    attr = f'TranscoderTempDirectory="{target}"'
    if re.search(r'TranscoderTempDirectory="[^"]*"', xml):
        return re.sub(r'TranscoderTempDirectory="[^"]*"', attr, xml)
    return xml.replace("<Preferences ", f"<Preferences {attr} ", 1)


def ensure_custom_connections(xml: str, url: str) -> str:
    if not url:
        return xml
    attr = f'customConnections="{url}"'
    if re.search(r'customConnections="[^"]*"', xml):
        return re.sub(r'customConnections="[^"]*"', attr, xml)
    return xml.replace("<Preferences ", f"<Preferences {attr} ", 1)


def apply_host_prefs(xml: str, *, advertise_url: str = "") -> str:
    updated = ensure_transcoder_temp(xml)
    if advertise_url:
        updated = ensure_custom_connections(updated, advertise_url)
    return updated
