"""Stack problems as stable keys, so alerts fire on change instead of every tick."""

from __future__ import annotations

from dataclasses import dataclass

DISK_FULL_PERCENT = 90
BACKUP_MAX_AGE_HOURS = 36


@dataclass(frozen=True)
class Container:
    name: str
    status: str
    health: str
    exit_code: int
    restart_policy: str

    @classmethod
    def from_inspect(cls, row: dict) -> "Container":
        state = row.get("State") or {}
        return cls(
            name=row.get("Name", "").lstrip("/"),
            status=state.get("Status", ""),
            health=(state.get("Health") or {}).get("Status", ""),
            exit_code=int(state.get("ExitCode", 0)),
            restart_policy=((row.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name", ""),
        )

    @property
    def is_one_shot(self) -> bool:
        return self.restart_policy in ("", "no")


def container_problems(containers: list[Container]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in containers:
        if c.is_one_shot:
            if c.status == "exited" and c.exit_code != 0:
                out[f"failed:{c.name}"] = f"{c.name} init exited with code {c.exit_code}"
            continue
        if c.status != "running":
            out[f"down:{c.name}"] = f"{c.name} is {c.status}"
        elif c.health == "unhealthy":
            out[f"unhealthy:{c.name}"] = f"{c.name} is unhealthy"
    return out


def disk_problems(usage: dict[str, int | None]) -> dict[str, str]:
    """usage maps a path to its filesystem's used percent, or None when it is missing."""
    out: dict[str, str] = {}
    for path, percent in usage.items():
        if percent is None:
            out[f"missing:{path}"] = f"{path} is not mounted or missing"
        elif percent >= DISK_FULL_PERCENT:
            out[f"full:{path}"] = f"{path} is {percent}% full"
    return out


def backup_problems(age_hours: float | None) -> dict[str, str]:
    if age_hours is None:
        return {"backup:never": "appdata backup has never succeeded"}
    if age_hours > BACKUP_MAX_AGE_HOURS:
        return {"backup:stale": f"last appdata backup was {age_hours:.0f}h ago"}
    return {}


def diff(previous: set[str], current: dict[str, str]) -> tuple[dict[str, str], set[str]]:
    new = {k: v for k, v in current.items() if k not in previous}
    resolved = previous - current.keys()
    return new, resolved


def restart_targets(new: dict[str, str]) -> list[str]:
    """Docker only reports unhealthy; restart once per transition, not every tick."""
    return sorted(k.split(":", 1)[1] for k in new if k.startswith("unhealthy:"))
