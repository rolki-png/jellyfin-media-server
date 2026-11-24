"""*arr JSON transforms — one implementation for Radarr and Sonarr."""

from __future__ import annotations

from typing import Any


def patch_media_management(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    out["copyUsingHardlinks"] = True
    out["importExtraFiles"] = True
    out["extraFileExtensions"] = "srt"
    out["minimumFreeSpaceWhenImporting"] = 10240
    out["skipFreeSpaceCheckWhenImporting"] = False
    return out


def patch_download_client(client: dict[str, Any]) -> dict[str, Any]:
    out = dict(client)
    out["removeCompletedDownloads"] = False
    out["removeFailedDownloads"] = True
    return out


def quality_profile_id(profiles: list[dict[str, Any]], name: str) -> int | None:
    for row in profiles:
        if row.get("name") == name:
            raw = row.get("id")
            return int(raw) if raw is not None else None
    return None


def editor_payload(kind: str, ids: list[int], profile_id: int) -> dict[str, Any]:
    if kind == "movie":
        return {"movieIds": ids, "qualityProfileId": profile_id}
    if kind == "series":
        return {"seriesIds": ids, "qualityProfileId": profile_id}
    raise ValueError(f"unknown editor kind: {kind}")


def ids_needing_profile(
    items: list[dict[str, Any]], item_id_key: str, profile_id: int
) -> list[int]:
    return [
        int(item[item_id_key])
        for item in items
        if item.get("qualityProfileId") != profile_id
    ]


def custom_script_id(notifications: list[dict[str, Any]], path: str) -> int | None:
    for row in notifications:
        if row.get("implementation") != "CustomScript":
            continue
        fields = {f.get("name"): f.get("value") for f in row.get("fields") or []}
        if fields.get("path") == path:
            raw = row.get("id")
            return int(raw) if raw is not None else None
    return None


def custom_script_payload(app_name: str, path: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "Same-disk hardlink",
        "implementation": "CustomScript",
        "configContract": "CustomScriptSettings",
        "onDownload": True,
        "onUpgrade": True,
        "onRename": False,
        "fields": [{"name": "path", "value": path}],
        "tags": [],
    }
    if app_name == "Sonarr":
        body["onImportComplete"] = True
    return body


def first_download_client_id(clients: list[dict[str, Any]]) -> int:
    return int(clients[0]["id"])


def has_root_folder(roots: list[dict[str, Any]], path: str) -> bool:
    want = path.rstrip("/")
    return any(r.get("path", "").rstrip("/") == want for r in roots)


def has_remote_path_mapping(
    rows: list[dict[str, Any]], *, host: str, remote: str, local: str
) -> bool:
    remote_n = remote.rstrip("/") + "/"
    local_n = local.rstrip("/") + "/"
    return any(
        r.get("host") == host
        and r.get("remotePath", "").rstrip("/") + "/" == remote_n
        and r.get("localPath", "").rstrip("/") + "/" == local_n
        for r in rows
    )


def remote_path_payload(*, host: str, remote: str, local: str) -> dict[str, str]:
    return {"host": host, "remotePath": remote, "localPath": local}


def stuck_queue_ids(queue: dict[str, Any]) -> list[int]:
    return [
        int(r["id"])
        for r in queue.get("records", [])
        if r.get("status") == "completed" or r.get("trackedDownloadStatus") == "warning"
    ]


def has_plex_server_notification(notifications: list[dict[str, Any]]) -> bool:
    return any(n.get("implementation") == "PlexServer" for n in notifications)


def with_any_language(profile: dict[str, Any]) -> dict[str, Any]:
    """Allow HuN/dual-audio packs; nCore titles parse as Hungarian but include English."""
    out = dict(profile)
    out["language"] = {"id": -1, "name": "Any"}
    return out


def allow_named_qualities(profile: dict[str, Any], names: set[str]) -> dict[str, Any]:
    """Stock Any omits WEB-720p; Seerr updates can leave titles on Any."""

    def walk(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in items:
            row = dict(raw)
            label = row.get("name") or (row.get("quality") or {}).get("name")
            if label in names:
                row["allowed"] = True
            if row.get("items"):
                row["items"] = walk(row["items"])
            out.append(row)
        return out

    updated = dict(profile)
    updated["items"] = walk(list(profile.get("items") or []))
    return updated


def plex_server_payload(*, host: str, token: str) -> dict[str, Any]:
    return {
        "name": "Plex",
        "implementation": "PlexServer",
        "configContract": "PlexServerSettings",
        "onDownload": True,
        "onUpgrade": True,
        "onRename": True,
        "fields": [
            {"name": "host", "value": host},
            {"name": "port", "value": 32400},
            {"name": "useSsl", "value": False},
            {"name": "authToken", "value": token},
            {"name": "updateLibrary", "value": True},
        ],
        "tags": [],
    }


# Jackett ncore remaps Newznab IDs: 5030=TV/SD, 5040=TV/HD (5045 is unused).
_TV_CATS = (5000, 5030, 5040, 5050)
_MOVIE_CATS = (2000, 2030, 2040)


def patch_indexer(indexer: dict[str, Any]) -> dict[str, Any]:
    """ncore reports 0 seeders often; still snatch. Include SD/HD cats so 720p is visible."""
    out = dict(indexer)
    fields: list[dict[str, Any]] = []
    for raw in out.get("fields") or []:
        field = dict(raw)
        name = field.get("name")
        if name == "minimumSeeders":
            field["value"] = 0
        elif name == "categories":
            cats = [int(c) for c in (field.get("value") or [])]
            extra = _TV_CATS if any(5000 <= c < 6000 or c == 5045 for c in cats) else (
                _MOVIE_CATS if any(2000 <= c < 3000 for c in cats) else ()
            )
            for cid in extra:
                if cid not in cats:
                    cats.append(cid)
            field["value"] = cats
        fields.append(field)
    out["fields"] = fields
    return out

