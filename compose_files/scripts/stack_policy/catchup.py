"""Search recently aired/released missing titles after downtime (RSS-only gap)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

DEFAULT_LOOKBACK_DAYS = 14


def _parse_day(value: object) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _in_lookback(day: date | None, *, today: date, lookback_days: int) -> bool:
    if day is None:
        return False
    if day > today:
        return False
    return day >= today - timedelta(days=lookback_days)


def recent_missing_episode_ids(
    records: list[dict[str, Any]],
    *,
    today: date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[int]:
    out: list[int] = []
    for row in records:
        if not _in_lookback(_parse_day(row.get("airDate")), today=today, lookback_days=lookback_days):
            continue
        raw = row.get("id")
        if raw is not None:
            out.append(int(raw))
    return out


def movie_release_day(row: dict[str, Any]) -> date | None:
    for key in ("digitalRelease", "physicalRelease", "inCinemas"):
        day = _parse_day(row.get(key))
        if day is not None:
            return day
    return None


def recent_missing_movie_ids(
    records: list[dict[str, Any]],
    *,
    today: date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[int]:
    out: list[int] = []
    for row in records:
        if not _in_lookback(movie_release_day(row), today=today, lookback_days=lookback_days):
            continue
        raw = row.get("id")
        if raw is not None:
            out.append(int(raw))
    return out


def episode_search_command(episode_ids: list[int]) -> dict[str, Any] | None:
    if not episode_ids:
        return None
    return {"name": "EpisodeSearch", "episodeIds": episode_ids}


def movies_search_command(movie_ids: list[int]) -> dict[str, Any] | None:
    if not movie_ids:
        return None
    return {"name": "MoviesSearch", "movieIds": movie_ids}
