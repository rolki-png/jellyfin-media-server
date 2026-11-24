"""qBittorrent WebUI prefs — ncore-style private trackers need unbounded seeding.

``-1`` is qBittorrent's unlimited sentinel. Queueing with MaxActiveTorrents=20
parks completed torrents as queuedUP and they stop seeding.
"""

from __future__ import annotations

from typing import Any

# Pause at share limit instead of Remove — global ratio/time stay disabled,
# but a later UI toggle must not delete the torrent from the client.
_PAUSE_TORRENT = 0


def seed_unlimited_preferences() -> dict[str, Any]:
    return {
        "queueing_enabled": False,
        "max_active_torrents": -1,
        "max_active_uploads": -1,
        "max_ratio_enabled": False,
        "max_ratio": -1,
        "max_seeding_time_enabled": False,
        "max_seeding_time": -1,
        "max_inactive_seeding_time_enabled": False,
        "max_inactive_seeding_time": -1,
        "max_ratio_act": _PAUSE_TORRENT,
    }
