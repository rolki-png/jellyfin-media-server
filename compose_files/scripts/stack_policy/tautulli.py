"""Tautulli ↔ Plex connection and the official SIMKL watched webhook.

Tautulli has no native SIMKL agent. SIMKL's documented no-Plex-Pass path is a
Tautulli Webhook notifier that POSTs a Plex-shaped media.scrobble payload to
the unique URL from https://simkl.com/apps/plex.
"""

from __future__ import annotations

import configparser
import io
import re
from typing import Mapping

WEBHOOK_AGENT_ID = 25
SIMKL_NOTIFIER_NAME = "SIMKL"
SIMKL_WEBHOOK_PAGE = "https://simkl.com/apps/plex"

# Official SIMKL Tautulli JSON (Watched trigger). <<movie>> / <<episode>> are
# Tautulli conditionals. guid is a synthetic Plex-style ID string SIMKL parses.
SIMKL_WATCHED_JSON = (
    '{"event":"media.scrobble","user":"{username}",'
    '"Metadata":{"title":"<<episode>>{show_name}<</episode>><<movie>>{title}<</movie>>",'
    '"type":"{media_type}","parentIndex":"{season_num}","index":"{episode_num}",'
    '"year":"{year}",'
    '"guid":"/{themoviedb-{themoviedb_id}/{imdb-{imdb_id}'
    '<<episode>>/{thetvdb-{thetvdb_id}<</episode>>/{anidb-{anidb_id}/'
    '{season_num}/{episode_num}/"}}'
)

NOTIFY_ACTIONS = (
    "on_play",
    "on_stop",
    "on_pause",
    "on_resume",
    "on_error",
    "on_change",
    "on_intro",
    "on_commercial",
    "on_credits",
    "on_watched",
    "on_buffer",
    "on_concurrent",
    "on_newdevice",
    "on_created",
    "on_intdown",
    "on_intup",
    "on_extdown",
    "on_extup",
    "on_pmsupdate",
    "on_plexpyupdate",
    "on_plexpydbcorrupt",
    "on_tokenexpired",
)


def plex_connection_from_prefs(xml: str) -> dict[str, str]:
    """Token + machine id from Plex Preferences.xml (no HTTP)."""

    def attr(name: str) -> str:
        match = re.search(rf'{re.escape(name)}="([^"]*)"', xml)
        return match.group(1) if match else ""

    return {
        "token": attr("PlexOnlineToken"),
        "identifier": attr("MachineIdentifier"),
        "name": attr("FriendlyName") or "Plex",
    }


def tautulli_api_key(ini_text: str) -> str:
    parser = _parser(ini_text)
    for section in parser.sections():
        if parser.has_option(section, "api_key"):
            return parser.get(section, "api_key").strip()
        if parser.has_option(section, "API_KEY"):
            return parser.get(section, "API_KEY").strip()
    return ""


def apply_pms_ini(
    ini_text: str,
    *,
    token: str,
    identifier: str,
    name: str,
    host: str = "plex",
    port: int = 32400,
) -> str:
    """Point Tautulli at the compose Plex service and skip the setup wizard."""
    if not token or not identifier:
        return ini_text
    parser = _parser(ini_text)
    if not parser.has_section("PMS"):
        parser.add_section("PMS")
    if not parser.has_section("General"):
        parser.add_section("General")
    url = f"http://{host}:{port}"
    wanted = {
        ("PMS", "pms_ip"): host,
        ("PMS", "pms_port"): str(port),
        ("PMS", "pms_ssl"): "0",
        ("PMS", "pms_is_remote"): "0",
        ("PMS", "pms_url"): url,
        ("PMS", "pms_url_manual"): "1",
        ("PMS", "pms_token"): token,
        ("PMS", "pms_identifier"): identifier,
        ("PMS", "pms_name"): name,
        ("General", "first_run_complete"): "1",
    }
    changed = False
    for (section, key), value in wanted.items():
        current = parser.get(section, key, fallback="")
        if current != value:
            parser.set(section, key, value)
            changed = True
    if not changed:
        return ini_text
    buf = io.StringIO()
    parser.write(buf)
    return buf.getvalue()


def webhook_notifier_fields(webhook_url: str) -> dict[str, str]:
    """Query params for Tautulli set_notifier_config (webhook agent)."""
    fields = {
        "agent_id": str(WEBHOOK_AGENT_ID),
        "friendly_name": SIMKL_NOTIFIER_NAME,
        "webhook_hook": webhook_url.strip(),
        "webhook_method": "POST",
    }
    for action in NOTIFY_ACTIONS:
        fields[action] = "1" if action == "on_watched" else "0"
        fields[f"{action}_subject"] = ""
        fields[f"{action}_body"] = SIMKL_WATCHED_JSON if action == "on_watched" else ""
    return fields


def find_simkl_notifier_id(notifiers: object) -> int | None:
    rows = notifiers if isinstance(notifiers, list) else []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("friendly_name") or "")
        agent = row.get("agent_id")
        agent_name = str(row.get("agent_name") or "")
        if name == SIMKL_NOTIFIER_NAME and (
            agent == WEBHOOK_AGENT_ID or agent_name == "webhook"
        ):
            try:
                return int(row["id"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def webhook_url_from_config(config: Mapping[str, object]) -> str:
    inner = config.get("config")
    if isinstance(inner, Mapping):
        return str(inner.get("hook") or "").strip()
    return ""


def _parser(ini_text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    if ini_text.strip():
        parser.read_string(ini_text)
    return parser
