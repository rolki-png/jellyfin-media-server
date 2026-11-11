#!/usr/bin/env python3
"""Apply desktop idle policy from Plex sessions (Omarchy stay-awake + DPMS + power profile).

Xbox Direct Play hitches if this host locks or power-saves. Stay-awake blocks
Omarchy lock/screensaver; hyprctl DPMS blanks the PC monitor during remote
playback once you are idle. power-saver only after 15 minutes with no Plex.
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

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from stack_policy.plex_idle import idle_seconds_from_hint, playback_from_xml, policy_for  # noqa: E402

PREFS_CANDIDATES = (
    Path(os.environ["PLEX_PREFS"])
    if os.environ.get("PLEX_PREFS")
    else None,
    Path(os.environ["APPDATA_PATH"]) / "plex/Library/Application Support/Plex Media Server/Preferences.xml"
    if os.environ.get("APPDATA_PATH")
    else None,
    Path(
        "/mnt/samsung-media/Isyrr/appdata/plex/Library/Application Support/"
        "Plex Media Server/Preferences.xml"
    ),
    Path(
        "/mnt/combined-media/Isyrr/configs/plex/Library/Application Support/"
        "Plex Media Server/Preferences.xml"
    ),
)
PREFS = next((p for p in PREFS_CANDIDATES if p is not None and p.is_file()), PREFS_CANDIDATES[-1])
PLEX_URL = os.environ.get("PLEX_URL", "http://127.0.0.1:32400").rstrip("/")
POLL_SEC = float(os.environ.get("PLEX_IDLE_GUARD_POLL", "10"))
INDICATOR_DIR = Path.home() / ".local/state/omarchy/indicators"
STAY_AWAKE = INDICATOR_DIR / "stay-awake"
OWNED = INDICATOR_DIR / "stay-awake.plex-idle-guard"


def plex_token() -> str:
    root = ET.parse(PREFS).getroot()
    token = root.attrib.get("PlexOnlineToken", "")
    if not token:
        raise RuntimeError("PlexOnlineToken missing from Preferences.xml")
    return token


def sessions_xml(token: str) -> str | None:
    req = urllib.request.Request(
        f"{PLEX_URL}/status/sessions",
        headers={"X-Plex-Token": token, "Accept": "application/xml"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def host_ips() -> set[str]:
    ips = {"127.0.0.1", "::1"}
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return ips
    ips.update(out.split())
    return ips


def session_idle() -> tuple[bool, float]:
    sid = os.environ.get("XDG_SESSION_ID")
    cmd = ["loginctl", "show-session"]
    if sid:
        cmd.append(sid)
    cmd.extend(["-p", "IdleHint", "-p", "IdleSinceHint"])
    try:
        out = subprocess.check_output(cmd, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return False, 0.0
    hint = False
    since_us = 0
    for line in out.splitlines():
        key, _, value = line.partition("=")
        if key == "IdleHint":
            hint = value.strip().lower() in {"yes", "1", "true"}
        elif key == "IdleSinceHint":
            try:
                since_us = int(value.strip() or "0")
            except ValueError:
                since_us = 0
    if not hint or since_us <= 0:
        return False, 0.0
    idle_seconds = idle_seconds_from_hint(
        since_us, now_realtime=time.time(), now_monotonic=time.monotonic()
    )
    return True, idle_seconds


def set_stay_awake(enabled: bool) -> None:
    INDICATOR_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        STAY_AWAKE.touch()
        OWNED.touch()
        return
    if OWNED.exists():
        STAY_AWAKE.unlink(missing_ok=True)
        OWNED.unlink(missing_ok=True)


def set_dpms(off: bool, currently_off: bool) -> bool:
    if off == currently_off:
        return currently_off
    arg = "off" if off else "on"
    try:
        subprocess.run(
            ["hyprctl", "dispatch", "dpms", arg],
            check=False,
            timeout=3,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return currently_off
    return off


def set_power_profile(name: str, current: str | None) -> str:
    if current == name:
        return name
    try:
        subprocess.run(
            ["powerprofilesctl", "set", name],
            check=False,
            timeout=5,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return current or name
    return name


class SleepInhibit:
    def __init__(self) -> None:
        self.proc: subprocess.Popen[bytes] | None = None

    def set(self, enabled: bool) -> None:
        if enabled:
            if self.proc is not None and self.proc.poll() is None:
                return
            self.proc = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--what=sleep",
                    "--who=Plex idle guard",
                    "--why=Active Plex playback (Xbox Direct Play)",
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
    inhibit = SleepInhibit()
    dpms_off = False
    profile: str | None = None
    last_key: tuple | None = None

    def shutdown(_signum=None, _frame=None) -> None:
        inhibit.set(False)
        set_stay_awake(False)
        set_dpms(False, dpms_off)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    token = plex_token()
    while True:
        xml_text = sessions_xml(token)
        user_idle, idle_seconds = session_idle()
        if xml_text is None:
            time.sleep(POLL_SEC)
            continue
        playback = playback_from_xml(xml_text, host_ips())
        pol = policy_for(playback, user_idle=user_idle, idle_seconds=idle_seconds)
        key = (pol.stay_awake, pol.dpms_off, pol.power_profile, playback.any_active, playback.local_screen)
        if key != last_key:
            print(
                "plex-idle-guard: "
                f"plex={playback.any_active} local_screen={playback.local_screen} "
                f"idle={user_idle} idle_s={idle_seconds:.0f} "
                f"stay_awake={pol.stay_awake} dpms_off={pol.dpms_off} "
                f"profile={pol.power_profile}",
                flush=True,
            )
            last_key = key
        set_stay_awake(pol.stay_awake)
        inhibit.set(pol.stay_awake)
        dpms_off = set_dpms(pol.dpms_off, dpms_off)
        profile = set_power_profile(pol.power_profile, profile)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())
