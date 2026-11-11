# Media server verification map

This directory is the maintained source for verifying the live Plex stack. Read the index, then use the matching feature file.

## Baseline preconditions

- One stack is already running from `compose_files/` (`media-server.service` or `docker compose up -d`).
- `compose_files/.env` sets `COMMON_PATH` and `APPDATA_PATH`. `APPDATA_PATH` is a local disk.
- Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh doctor` and require `DOCTOR_OK`.
- Drive that same instance. Doctor's container ids are the ones under test.

## Driving conventions

- Start from the live stack. Commands are read-only GETs plus `health-check.sh` and `validate.sh`.
- Treat every command as literal.
- Run drives through `verify-media-server.sh`.
- Leave proof files in `.cursor/skills/verify-media-server/proof/`. Cleanup removes scratch and `.run-stamp` only.

## Proof and skip reporting

- Capture the command and the resulting state.
- Proof for a drive is `action.txt`, `stdout.txt`, `state.txt` or `stderr.txt`, and `exit_code.txt` containing `0`.
- A library count is confirmed by the Plex section list in `state.txt`.
- Record the feature id with the proof directory name.
- An unreachable path is the command that ran and the `DOCTOR_FAIL` or non-zero exit. A different feature does not cover it.

## Feature entry contract

Each feature file starts with an H1 and one paragraph, then four H2 sections: `Sub-features`, `How to get to it (user POV)`, `Driving it with verify-media-server`, `Gotchas`.

## Features

- [Stack health](./stack-health.md) covers service status, appdata disk, *arr health, Plex libraries listed by `health-check.sh`, and compose layout.
- [Movie library](./movie-library.md) covers Radarr's movie list and the Plex movie section.
- [TV library](./tv-library.md) covers Sonarr's series list and the Plex show section.
- [Download client](./download-client.md) covers the qBittorrent WebUI.
- [Dashboards](./dashboards.md) covers Panelarr, Homarr, and Seerr.
