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
