#!/usr/bin/env python3
"""Alert (ntfy) when the compose stack, its disks, or the appdata backup go wrong.

Run by media-monitor.timer. Restarts a container the first time it turns unhealthy.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stack_policy.monitor import (  # noqa: E402
    Container,
    backup_problems,
    container_problems,
    diff,
    disk_problems,
    restart_targets,
)

PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "compose_files")
STATE_DIR = Path(os.environ.get("STATE_DIRECTORY", "/var/lib/media-server"))
ALERTS = STATE_DIR / "alerts.json"
BACKUP_STAMP = STATE_DIR / "last-backup"


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout


def containers() -> list[Container]:
    ids = docker("ps", "-aq", "--filter", f"label=com.docker.compose.project={PROJECT}").split()
    if not ids:
        return []
    return [Container.from_inspect(row) for row in json.loads(docker("inspect", *ids))]


def disk_usage(paths: list[str]) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for p in paths:
        try:
            u = shutil.disk_usage(p)
            out[p] = round(100 * u.used / u.total)
        except OSError:
            out[p] = None
    return out


def backup_age_hours() -> float | None:
    try:
        return (time.time() - BACKUP_STAMP.stat().st_mtime) / 3600
    except FileNotFoundError:
        return None


def notify(title: str, body: str, priority: str) -> None:
    url = os.environ.get("NTFY_URL", "")
    print(f"[{priority}] {title}: {body}")
    if not url:
        return
    req = urllib.request.Request(
        url, data=body.encode(), headers={"Title": title, "Priority": priority, "Tags": "tv"}
    )
    urllib.request.urlopen(req, timeout=15).read()


def main() -> int:
    paths = [p for p in (os.environ.get("COMMON_PATH"), os.environ.get("APPDATA_PATH"),
                         os.environ.get("PLEX_TRANSCODE_DIR", "/var/lib/plex-transcode")) if p]
    current = {
        **container_problems(containers()),
        **disk_problems(disk_usage(paths)),
        **backup_problems(backup_age_hours()),
    }
    previous = set(json.loads(ALERTS.read_text())) if ALERTS.exists() else set()
    new, resolved = diff(previous, current)

    for name in restart_targets(new):
        docker("restart", name)
        new[f"unhealthy:{name}"] += " (restarted)"

    if new:
        notify("Media server problem", "\n".join(new.values()), "high")
    if resolved:
        notify("Media server recovered", "\n".join(sorted(resolved)), "default")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ALERTS.write_text(json.dumps(sorted(current)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
