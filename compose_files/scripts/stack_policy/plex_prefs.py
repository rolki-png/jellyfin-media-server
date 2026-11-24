"""Plex Preferences.xml mutations for stream-safe host settings."""

from __future__ import annotations

import re

TRANSCODER_TEMP = "/transcode"


def ensure_pref(xml: str, name: str, value: str) -> str:
    attr = f'{name}="{value}"'
    pattern = rf'\b{name}="[^"]*"'
    if re.search(pattern, xml):
        return re.sub(pattern, attr, xml)
    return xml.replace("<Preferences ", f"<Preferences {attr} ", 1)


def ensure_transcoder_temp(xml: str, target: str = TRANSCODER_TEMP) -> str:
    return ensure_pref(xml, "TranscoderTempDirectory", target)


def apply_host_prefs(xml: str, *, advertise_url: str = "", lan_networks: str = "") -> str:
    """advertise_url → customConnections; lan_networks → LanNetworksBandwidth.

    LanNetworksBandwidth replaces Plex's subnet auto-detection, so it must list the
    home LAN as well as the tailnet (100.64.0.0/10) or local clients turn "remote".
    """
    updated = ensure_transcoder_temp(xml)
    if advertise_url:
        updated = ensure_pref(updated, "customConnections", advertise_url)
    if lan_networks:
        updated = ensure_pref(updated, "LanNetworksBandwidth", lan_networks)
    return updated
