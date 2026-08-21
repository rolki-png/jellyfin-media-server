"""Bazarr config.yaml patches so Xbox gets sidecar SRT, not PGS burn-in."""

from __future__ import annotations

import json
import re
import urllib.parse

# Providers that work without an API account. OpenSubtitles.com needs a key.
ANON_PROVIDERS = ("gestdown", "podnapisi", "tvsubtitles")

_BOOLS = {
    "use_sonarr": True,
    "use_radarr": True,
    "use_embedded_subs": True,
    "ignore_pgs_subs": True,
    "ignore_vobsub_subs": True,
    "ignore_ass_subs": True,
}


def _bool_lit(value: bool) -> str:
    return "true" if value else "false"


def english_language_profile() -> dict:
    """Languages profile the Bazarr UI/API stores (profileId 1)."""
    return {
        "profileId": 1,
        "name": "English",
        "cutoff": None,
        "originalFormat": None,
        "tag": None,
        "mustContain": [],
        "mustNotContain": [],
        "items": [
            {
                "id": 1,
                "language": "en",
                "forced": "False",
                "hi": "False",
                "audio_exclude": "False",
                "audio_only_include": "False",
            }
        ],
    }


def english_settings_form() -> bytes:
    """Form body for POST /api/system/settings."""
    return urllib.parse.urlencode(
        [
            ("languages-enabled", "en"),
            ("languages-profiles", json.dumps([english_language_profile()])),
            ("settings-general-serie_default_enabled", "true"),
            ("settings-general-movie_default_enabled", "true"),
            ("settings-general-serie_default_profile", "1"),
            ("settings-general-movie_default_profile", "1"),
        ]
    ).encode()


def apikey_from_config(text: str) -> str:
    match = re.search(r"^auth:\n  apikey:\s*(\S+)", text, re.M)
    return match.group(1) if match else ""


def titles_needing_english(rows: object, id_key: str) -> list[int]:
    out: list[int] = []
    data = rows.get("data") if isinstance(rows, dict) else rows
    for row in data or []:
        if not isinstance(row, dict):
            continue
        if row.get("profileId") == 1:
            continue
        raw = row.get(id_key)
        if raw is None:
            continue
        out.append(int(raw))
    return out


def apply_english_library(get, post) -> None:
    """Assign English profile (id 1) to series/movies missing it. get/post are HTTP adapters."""
    for series_id in titles_needing_english(get("/series"), "sonarrSeriesId"):
        post(f"/series?seriesid={series_id}&profileid=1")
    for movie_id in titles_needing_english(get("/movies"), "radarrId"):
        post(f"/movies?radarrid={movie_id}&profileid=1")


def apply_english_over_http(base_url: str, apikey: str) -> None:
    """Production adapter: Bazarr REST + languages form POST."""
    import urllib.request

    base = base_url.rstrip("/")
    headers = {"X-API-KEY": apikey, "Accept": "application/json"}

    req = urllib.request.Request(
        f"{base}/api/system/settings",
        data=english_settings_form(),
        method="POST",
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError("bazarr settings post failed")

    def get(path: str) -> object:
        r = urllib.request.Request(f"{base}/api{path}", headers=headers)
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.load(resp)

    def post(path: str) -> None:
        r = urllib.request.Request(
            f"{base}/api{path}", data=b"", method="POST", headers=headers
        )
        with urllib.request.urlopen(r, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(path)

    apply_english_library(get, post)


def apply_direct_play_config(
    text: str, *, sonarr_apikey: str, radarr_apikey: str
) -> str:
    """Return config.yaml with Direct Play subtitle policy applied."""
    lines = text.splitlines(keepends=True)
    section = ""
    skip_provider_items = False
    out: list[str] = []
    for line in lines:
        if skip_provider_items:
            if re.match(r"^\s+-\s+", line):
                continue
            skip_provider_items = False

        top = re.match(r"^([A-Za-z_][\w]*)\s*:", line)
        if top and not line.startswith((" ", "\t")):
            section = top.group(1)

        replaced = False
        for key, want in _BOOLS.items():
            if re.match(rf"^\s*{re.escape(key)}\s*:", line):
                nl = "\n" if line.endswith("\n") else ""
                indent = re.match(r"^(\s*)", line)
                prefix = indent.group(1) if indent else ""
                out.append(f"{prefix}{key}: {_bool_lit(want)}{nl}")
                replaced = True
                break
        if replaced:
            continue

        if re.match(r"^\s*enabled_providers\s*:", line):
            nl = "\n" if line.endswith("\n") else ""
            indent = re.match(r"^(\s*)", line)
            prefix = indent.group(1) if indent else ""
            items = "".join(f"{prefix}- {name}{nl}" for name in ANON_PROVIDERS)
            out.append(f"{prefix}enabled_providers:{nl}{items}")
            skip_provider_items = True
            continue

        if section in ("sonarr", "radarr") and re.match(r"^\s*ip\s*:", line):
            nl = "\n" if line.endswith("\n") else ""
            indent = re.match(r"^(\s*)", line)
            prefix = indent.group(1) if indent else ""
            out.append(f"{prefix}ip: {section}{nl}")
            continue

        if section == "sonarr" and re.match(r"^\s*apikey\s*:", line):
            nl = "\n" if line.endswith("\n") else ""
            indent = re.match(r"^(\s*)", line)
            prefix = indent.group(1) if indent else ""
            out.append(f"{prefix}apikey: {sonarr_apikey}{nl}")
            continue

        if section == "radarr" and re.match(r"^\s*apikey\s*:", line):
            nl = "\n" if line.endswith("\n") else ""
            indent = re.match(r"^(\s*)", line)
            prefix = indent.group(1) if indent else ""
            out.append(f"{prefix}apikey: {radarr_apikey}{nl}")
            continue

        out.append(line)
    return "".join(out)
