"""Tautulli ↔ Plex connection and the official SIMKL watched webhook.

Tautulli has no native SIMKL agent. SIMKL's documented no-Plex-Pass path is a
Tautulli Webhook notifier that POSTs a Plex-shaped media.scrobble payload to
the unique URL from https://simkl.com/apps/plex.
"""

from __future__ import annotations

import configparser
import io
import json
import re
from typing import Callable, Mapping

WEBHOOK_AGENT_ID = 25
SIMKL_NOTIFIER_NAME = "SIMKL"
SIMKL_WEBHOOK_PAGE = "https://simkl.com/apps/plex"

# Exact Watched JSON from https://simkl.com/apps/plex (Tautulli path).
# `<episode>` / `<movie>` are Tautulli media tags. `{themoviedb-<themoviedb_id}`
# is Tautulli's prefix form — nested `{themoviedb-{themoviedb_id}` makes it
# drop the body and POST an empty fallback SIMKL ignores.
SIMKL_WATCHED_JSON = (
    '{"event":"media.scrobble","user":"{username}", '
    '"Metadata":{ "title": "<episode>{show_name}</episode><movie>{title}</movie>",'
    '"type":"{media_type}","parentIndex": "{season_num}", '
    '"index": "{episode_num}", "year": "{year}",'
    '"guid":"/{themoviedb-<themoviedb_id}/{imdb-<imdb_id}'
    "<episode>/{thetvdb-<thetvdb_id}</episode>/{anidb-<anidb_id}"
    '/{season_num}/{episode_num}/"} }'
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


def watched_body_from_config(config: Mapping[str, object]) -> str:
    text = config.get("notify_text")
    if not isinstance(text, Mapping):
        return ""
    watched = text.get("on_watched")
    if not isinstance(watched, Mapping):
        return ""
    return str(watched.get("body") or "")


def simkl_notifier_is_current(config: object, webhook: str) -> bool:
    if not isinstance(config, Mapping):
        return False
    inner = config.get("config")
    method = ""
    if isinstance(inner, Mapping):
        method = str(inner.get("method") or "").upper()
    actions = config.get("actions")
    watched = None
    if isinstance(actions, Mapping):
        watched = actions.get("on_watched")
    return (
        webhook_url_from_config(config) == webhook.strip()
        and method == "POST"
        and watched in (1, "1", True)
        and watched_body_from_config(config) == SIMKL_WATCHED_JSON
    )


_MEDIA_TAG_BLOCKS = (
    r"<movie>.*?</movie>|<show>.*?</show>|<season>.*?</season>|"
    r"<episode>.*?</episode>|<artist>.*?</artist>|<album>.*?</album>|<track>.*?</track>"
)
_KEEP_MEDIA_BLOCK = {
    "movie": "<movie>.*?</movie>",
    "show": "<show>.*?</show>",
    "season": "<season>.*?</season>",
    "episode": "<episode>.*?</episode>",
    "artist": "<artist>.*?</artist>",
    "album": "<album>.*?</album>",
    "track": "<track>.*?</track>",
}
_TAUTULLI_FIELD = re.compile(r"\{([^{}]+)\}")


def apply_media_tags(text: str, media_type: str) -> str:
    """Same keep/drop rules Tautulli uses before formatting webhook JSON."""
    keep = _KEEP_MEDIA_BLOCK.get(media_type)
    pattern = (
        _MEDIA_TAG_BLOCKS.replace(keep, f"<{media_type}>|</{media_type}>")
        if keep
        else _MEDIA_TAG_BLOCKS
    )
    return re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)


def format_tautulli_fields(text: str, params: Mapping[str, object]) -> str:
    def repl(match: re.Match[str]) -> str:
        spec = match.group(1)
        prefix = suffix = ""
        name = spec
        if "<" in spec:
            prefix, rest = spec.split("<", 1)
            if ">" in rest:
                name, suffix = rest.split(">", 1)
            else:
                name = rest
        value = str(params.get(name, "") or "")
        if not value:
            return ""
        return f"{prefix}{value}{suffix}"

    return _TAUTULLI_FIELD.sub(repl, text)


def render_simkl_watched_body(params: Mapping[str, object]) -> dict[str, object]:
    media_type = str(params.get("media_type") or "")
    data = json.loads(apply_media_tags(SIMKL_WATCHED_JSON, media_type))

    def walk(node: object) -> object:
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(value) for value in node]
        if isinstance(node, str):
            return format_tautulli_fields(node, params)
        return node

    rendered = walk(data)
    if not isinstance(rendered, dict):
        raise TypeError("SIMKL watched JSON must be an object")
    return rendered


def ids_from_plex_guids(guids: object) -> dict[str, str]:
    out = {"themoviedb_id": "", "imdb_id": "", "thetvdb_id": "", "anidb_id": ""}
    rows = guids if isinstance(guids, list) else []
    for raw in rows:
        value = str(raw)
        if "://" not in value:
            continue
        scheme, ident = value.split("://", 1)
        ident = ident.strip()
        if scheme == "tmdb":
            out["themoviedb_id"] = ident
        elif scheme == "imdb":
            out["imdb_id"] = ident
        elif scheme == "tvdb":
            out["thetvdb_id"] = ident
        elif scheme == "anidb":
            out["anidb_id"] = ident
    return out


def simkl_scrobble_payload(
    *,
    username: str,
    show_name: str,
    title: str,
    media_type: str,
    season_num: str,
    episode_num: str,
    year: str,
    themoviedb_id: str = "",
    imdb_id: str = "",
    thetvdb_id: str = "",
    anidb_id: str = "",
) -> dict[str, object]:
    return render_simkl_watched_body(
        {
            "username": username,
            "show_name": show_name,
            "title": title,
            "media_type": media_type,
            "season_num": season_num,
            "episode_num": episode_num,
            "year": year,
            "themoviedb_id": themoviedb_id,
            "imdb_id": imdb_id,
            "thetvdb_id": thetvdb_id,
            "anidb_id": anidb_id,
        }
    )


def scrobble_from_metadata(meta: Mapping[str, object], *, username: str) -> dict[str, object]:
    media_type = str(meta.get("media_type") or "")
    if media_type == "episode":
        ids = ids_from_plex_guids(meta.get("grandparent_guids") or meta.get("guids"))
        show_name = str(meta.get("grandparent_title") or "")
        season = str(meta.get("parent_media_index") or meta.get("parent_index") or "")
        episode = str(meta.get("media_index") or meta.get("index") or "")
    else:
        ids = ids_from_plex_guids(meta.get("guids"))
        show_name = ""
        season = ""
        episode = ""
    return simkl_scrobble_payload(
        username=username,
        show_name=show_name,
        title=str(meta.get("title") or ""),
        media_type=media_type,
        season_num=season,
        episode_num=episode,
        year=str(meta.get("year") or ""),
        **ids,
    )


def replay_empty_watched_webhooks(call, post: Callable[[str, dict], object], webhook: str) -> int:
    """Re-POST watched events Tautulli sent with an empty body (failed template)."""
    logs = call("get_notification_log", {"length": "1000"}) or {}
    rows = logs.get("data") if isinstance(logs, Mapping) else logs
    sent = 0
    seen: set[object] = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        if row.get("notify_action") != "on_watched":
            continue
        if str(row.get("body_text") or "").strip():
            continue
        rating_key = row.get("rating_key")
        if rating_key in seen:
            continue
        seen.add(rating_key)
        meta = call("get_metadata", {"rating_key": str(rating_key)}) or {}
        if not isinstance(meta, Mapping) or not meta.get("media_type"):
            continue
        post(webhook, scrobble_from_metadata(meta, username=str(row.get("user") or "")))
        sent += 1
    return sent


def new_webhook_notifier_id(notifiers: object) -> int | None:
    """Id of a webhook we just added (empty friendly_name) or the only webhook."""
    rows = [n for n in (notifiers if isinstance(notifiers, list) else []) if isinstance(n, Mapping)]
    webhooks = [
        n
        for n in rows
        if n.get("agent_id") == WEBHOOK_AGENT_ID or n.get("agent_name") == "webhook"
    ]
    if len(webhooks) == 1:
        try:
            return int(webhooks[0]["id"])
        except (KeyError, TypeError, ValueError):
            return None
    unnamed = [n for n in webhooks if not n.get("friendly_name")]
    if len(unnamed) != 1:
        return None
    try:
        return int(unnamed[0]["id"])
    except (KeyError, TypeError, ValueError):
        return None


def ensure_simkl_webhook(call, webhook: str) -> str:
    """Create or update the SIMKL watched notifier. ``call(cmd, extra=None)`` is the Tautulli adapter."""
    webhook = webhook.strip()
    notifiers = call("get_notifiers") or []
    notifier_id = find_simkl_notifier_id(notifiers)
    if notifier_id is None:
        call("add_notifier_config", {"agent_id": str(WEBHOOK_AGENT_ID)})
        notifiers = call("get_notifiers") or []
        notifier_id = find_simkl_notifier_id(notifiers) or new_webhook_notifier_id(notifiers)
        if notifier_id is None:
            raise RuntimeError("could not identify new webhook notifier")
    config = call("get_notifier_config", {"notifier_id": str(notifier_id)}) or {}
    if simkl_notifier_is_current(config, webhook):
        return "ok"
    fields = webhook_notifier_fields(webhook)
    fields["notifier_id"] = str(notifier_id)
    call("set_notifier_config", fields)
    return "updated"


def tautulli_http_call(base_url: str, api_key: str):
    """Production adapter: Tautulli ``/api/v2`` over HTTP."""
    import json
    import urllib.parse
    import urllib.request

    base = base_url.rstrip("/")

    def call(cmd: str, extra: dict | None = None) -> object:
        params = {"apikey": api_key, "cmd": cmd}
        if extra:
            params.update(extra)
        url = base + "/api/v2?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.load(resp)
        if payload.get("response", {}).get("result") != "success":
            raise RuntimeError(payload)
        return payload["response"].get("data")

    return call


def post_json(url: str, payload: dict) -> None:
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()


def _parser(ini_text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.optionxform = str
    if ini_text.strip():
        parser.read_string(ini_text)
    return parser
