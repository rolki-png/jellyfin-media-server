"""Hardlink-safe *arr volume layout.

Radarr/Sonarr must see library + downloads as one filesystem (COMMON_PATH).
Separate /movies, /tv, or /downloads binds cause EXDEV and copies.
"""

from __future__ import annotations

FORBIDDEN_VOLUME_TARGETS = frozenset({"/movies", "/tv", "/downloads"})
SCRIPT_MARKER = "same-disk-import.sh"
ARR_SERVICES = ("radarr", "sonarr")


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


def check_compose_doc(data: dict) -> list[str]:
    """Check rendered compose JSON/YAML mapping for radarr and sonarr."""
    services = data.get("services") or {}
    errors: list[str] = []
    for name in ARR_SERVICES:
        svc = services.get(name) or {}
        errors.extend(check_arr_volumes(name, svc.get("volumes")))
    return errors
