"""Desktop idle policy while Plex is the playback target.

Xbox Direct Play hitches if this host locks or drops to power-saver. The
Omarchy stay-awake flag blocks screensaver/lock; DPMS is applied separately so
the PC monitor can blank during remote playback without locking.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

ACTIVE_STATES = frozenset({"playing", "buffering", "paused"})
POWER_SAVER_AFTER_SEC = 15 * 60
POWER_PERFORMANCE = "performance"
POWER_SAVER = "power-saver"
# logind IdleSinceHint is CLOCK_REALTIME µs (~1e15). Monotonic µs is uptime-sized.
_REALTIME_HINT_MIN_US = 10**14


def idle_seconds_from_hint(
    since_us: int, *, now_realtime: float, now_monotonic: float
) -> float:
    if since_us <= 0:
        return 0.0
    if since_us >= _REALTIME_HINT_MIN_US:
        return max(0.0, now_realtime - since_us / 1_000_000)
    return max(0.0, now_monotonic - since_us / 1_000_000)


@dataclass(frozen=True)
class Playback:
    any_active: bool
    local_screen: bool


@dataclass(frozen=True)
class IdlePolicy:
    stay_awake: bool
    dpms_off: bool
    power_profile: str


def playback_from_xml(xml_text: str, host_ips: frozenset[str] | set[str]) -> Playback:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return Playback(any_active=False, local_screen=False)
    hosts = {ip.strip() for ip in host_ips if ip.strip()}
    any_active = False
    local_screen = False
    for player in root.iter("Player"):
        if player.attrib.get("state", "").lower() not in ACTIVE_STATES:
            continue
        any_active = True
        address = player.attrib.get("address", "")
        if address in hosts:
            local_screen = True
    return Playback(any_active=any_active, local_screen=local_screen)


def policy_for(playback: Playback, *, user_idle: bool, idle_seconds: float) -> IdlePolicy:
    if playback.any_active:
        return IdlePolicy(
            stay_awake=True,
            dpms_off=user_idle and not playback.local_screen,
            power_profile=POWER_PERFORMANCE,
        )
    saver = user_idle and idle_seconds >= POWER_SAVER_AFTER_SEC
    return IdlePolicy(
        stay_awake=False,
        dpms_off=False,
        power_profile=POWER_SAVER if saver else POWER_PERFORMANCE,
    )
