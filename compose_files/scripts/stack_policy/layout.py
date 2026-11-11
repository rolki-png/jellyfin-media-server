"""Hardlink-safe *arr volume layout.

Radarr/Sonarr must see library + downloads as one filesystem (COMMON_PATH).
Separate /movies, /tv, or /downloads binds cause EXDEV and copies.
"""

from __future__ import annotations

FORBIDDEN_VOLUME_TARGETS = frozenset({"/movies", "/tv", "/downloads"})
CONFIG_TARGETS = frozenset({"/config", "/app/config"})
SCRIPT_MARKER = "same-disk-import.sh"
WATCHTOWER_LABEL = "com.centurylinklabs.watchtower.enable"
LOCAL_PLEX_IMAGE = "freeloader-plex"
ARR_SERVICES = ("radarr", "sonarr")
SQLITE_CONFIG_SERVICES = (
    "plex",
    "plex-init",
    "sonarr",
    "radarr",
    "tautulli",
    "bazarr",
    "jackett",
    "qbittorrent",
    "seerr",
    "unpackerr",
    "prowlarr",
    "jellyfin",
    "jellyfin-init",
)


def _volume_parts(entry: object) -> tuple[str, str]:
    if isinstance(entry, dict):
        return str(entry.get("source") or ""), str(entry.get("target") or "")
    parts = str(entry).split(":")
    source = parts[0] if parts else ""
    target = parts[1] if len(parts) > 1 else ""
    return source, target


def check_arr_volumes(service: str, volumes: list[object] | None) -> list[str]:
    """Return error strings if *arr volumes break hardlinks."""
    errors: list[str] = []
    vols = volumes or []
    sources: list[str] = []
    targets: list[str] = []
    for entry in vols:
        source, target = _volume_parts(entry)
        sources.append(source)
        targets.append(target)
    bad = FORBIDDEN_VOLUME_TARGETS.intersection(targets)
    if bad:
        errors.append(
            f"{service} must not bind /movies, /tv, or /downloads separately "
            f"(breaks hardlinks). targets={targets}"
        )
    if not any(SCRIPT_MARKER in s or SCRIPT_MARKER in t for s, t in zip(sources, targets)):
        errors.append(f"{service} must mount {SCRIPT_MARKER} under /scripts/")
    return errors


def _pool_prefixes(services: dict) -> list[str]:
    """Identity binds (source == target) are the media pool, not appdata."""
    prefixes: list[str] = []
    for svc in services.values():
        if not isinstance(svc, dict):
            continue
        for entry in svc.get("volumes") or []:
            source, target = _volume_parts(entry)
            if source and source == target:
                prefixes.append(source.rstrip("/"))
    return prefixes


def check_config_off_pool(service: str, volumes: list[object] | None, pool_prefixes: list[str]) -> list[str]:
    """SQLite /config must not live under a pool identity bind's configs/ tree."""
    errors: list[str] = []
    if not pool_prefixes:
        return errors
    for entry in volumes or []:
        source, target = _volume_parts(entry)
        if target not in CONFIG_TARGETS:
            continue
        src = source.rstrip("/")
        for pool in pool_prefixes:
            if src == pool:
                errors.append(
                    f"{service} /config is the media pool root ({source}); "
                    "put APPDATA_PATH on a real local disk, not mergerfs"
                )
                break
            if src.startswith(pool + "/"):
                rel = src[len(pool) + 1 :]
                if rel == "configs" or rel.startswith("configs/"):
                    errors.append(
                        f"{service} /config is on the media pool ({source}); "
                        "put APPDATA_PATH on a real local disk, not mergerfs"
                    )
                    break
    return errors


def check_plex_local_image(service: str, svc: dict) -> list[str]:
    """A locally built plex image must stay off watchtower.

    Watchtower pulls by tag and would replace the Freeloader-patched local
    image with upstream lscr.io/linuxserver/plex, silently dropping the
    feature-unlock .so. Plex updates are rebuilds (build-freeloader-plex.sh).
    """
    svc = svc or {}
    image = str(svc.get("image") or "")
    if not image.startswith(LOCAL_PLEX_IMAGE):
        return []
    labels = svc.get("labels") or {}
    if str(labels.get(WATCHTOWER_LABEL)) == "false":
        return []
    return [
        f"{service} uses local image {image} but {WATCHTOWER_LABEL} is not \"false\"; "
        "watchtower would replace the Freeloader-patched image with upstream"
    ]


def check_compose_doc(data: dict) -> list[str]:
    """Check rendered compose JSON/YAML mapping for radarr and sonarr."""
    services = data.get("services") or {}
    errors: list[str] = []
    pools = _pool_prefixes(services)
    for name in ARR_SERVICES:
        svc = services.get(name) or {}
        errors.extend(check_arr_volumes(name, svc.get("volumes")))
    for name in SQLITE_CONFIG_SERVICES:
        svc = services.get(name) or {}
        if not svc:
            continue
        errors.extend(check_config_off_pool(name, svc.get("volumes"), pools))
    errors.extend(check_plex_local_image("plex", services.get("plex") or {}))
    return errors
