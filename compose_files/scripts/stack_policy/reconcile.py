"""Side effects allowed for each homelab-setup mode.

Boot must re-apply hardlinks, catch up RSS gaps, and sync Recyclarr scores.
Boot must never wipe the download queue or restart qBittorrent (a5fca47).
"""

from __future__ import annotations

from typing import Final

APPLY_HARDLINK = "apply_hardlink_policy"
CATCHUP = "trigger_recent_missing_search"
RECYCLARR = "run_recyclarr_sync"
CLEAR_QUEUE = "clear_stuck_queue"
RESTART_QBIT = "restart_qbittorrent"
DOWNLOAD_SCAN = "trigger_download_scan"
PLEX_SCAN = "trigger_plex_library_scan"

BOOT_EFFECTS: Final[frozenset[str]] = frozenset(
    {APPLY_HARDLINK, CATCHUP, RECYCLARR}
)
ALL_ONLY_EFFECTS: Final[frozenset[str]] = frozenset(
    {CLEAR_QUEUE, RESTART_QBIT, DOWNLOAD_SCAN, PLEX_SCAN}
)


def effects_for(mode: str) -> frozenset[str]:
    if mode == "boot":
        return BOOT_EFFECTS
    if mode == "all":
        return BOOT_EFFECTS | ALL_ONLY_EFFECTS
    raise ValueError(f"unknown mode: {mode}")


def boot_forbids(effect: str) -> bool:
    return effect in ALL_ONLY_EFFECTS
