#!/usr/bin/env python3
"""Keep Omarchy stay-awake on while a Plex client is actually watching.

The Plex host is this desktop. Screensaver/lock (and CPU/GPU idle) hitch Xbox
Direct Play. Omarchy's idle monitor honors ~/.local/state/omarchy/indicators/stay-awake.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

PREFS = Path(
    os.environ.get(
        "PLEX_PREFS",
        "/mnt/combined-media/Isyrr/configs/plex/Library/Application Support/"
        "Plex Media Server/Preferences.xml",
    )
)
PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400").rstrip("/")
POLL_SEC = float(os.environ.get("PLEX_IDLE_GUARD_POLL", "10"))
INDICATOR_DIR = Path.home() / ".local/state/omarchy/indicators"
STAY_AWAKE = INDICATOR_DIR / "stay-awake"
OWNED = INDICATOR_DIR / "stay-awake.plex-idle-guard"
ACTIVE_STATES = frozenset({"playing", "buffering", "paused"})


def plex_token() -> str:
    root = ET.parse(PREFS).getroot()
    token = root.attrib.get("PlexOnlineToken", "")
    if not token:
        raise RuntimeError("PlexOnlineToken missing from Preferences.xml")
    return token


def session_active(token: str) -> bool | None:
    req = urllib.request.Request(
        f"{PLEX_URL}/status/sessions",
        headers={"X-Plex-Token": token, "Accept": "application/xml"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            root = ET.parse(resp).getroot()
    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError):
        return None
    for player in root.iter("Player"):
        if player.attrib.get("state", "").lower() in ACTIVE_STATES:
            return True
    return False


def set_stay_awake(enabled: bool) -> None:
    INDICATOR_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        STAY_AWAKE.touch()
        OWNED.touch()
        return
    if OWNED.exists():
        STAY_AWAKE.unlink(missing_ok=True)
        OWNED.unlink(missing_ok=True)


class IdleInhibit:
    def __init__(self) -> None:
        self.proc: subprocess.Popen[bytes] | None = None

    def set(self, enabled: bool) -> None:
        if enabled:
            if self.proc is not None and self.proc.poll() is None:
                return
            self.proc = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--what=idle:sleep",
                    "--who=Plex idle guard",
                    "--why=Active Plex playback on this host",
                    "--mode=block",
                    "sleep",
                    "infinity",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None


def main() -> int:
    inhibit = IdleInhibit()
    holding = OWNED.exists()

    def shutdown(_signum=None, _frame=None) -> None:
        inhibit.set(False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    token = plex_token()
    while True:
        active = session_active(token)
        if active is True and not holding:
            set_stay_awake(True)
            inhibit.set(True)
            holding = True
            print("plex-idle-guard: stay-awake on (active Plex session)", flush=True)
        elif active is False and holding:
            set_stay_awake(False)
            inhibit.set(False)
            holding = False
            print("plex-idle-guard: stay-awake off (no Plex session)", flush=True)
        elif active is True:
            inhibit.set(True)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())
