# Stack health

Stack health shows whether the media server is up, appdata sits on a local disk, Radarr and Sonarr answer, and Plex has libraries.

## Sub-features

- `services-up` lists core containers as running.
- `appdata-disk` reports `APPDATA_PATH` filesystem type.
- `arr-health` shows Radarr and Sonarr health plus queue depth.
- `plex-libraries` lists Plex library sections.
- `layout-validate` checks compose binds for the hardlink-safe layout.

## How to get to it (user POV)

- Run `bash compose_files/scripts/health-check.sh` on the host.
- Open Radarr at `http://127.0.0.1:7878`, Sonarr at `http://127.0.0.1:8989`, and Plex at `http://127.0.0.1:32400`.
- Run `bash compose_files/validate.sh` before trusting a compose edit.

## Driving it with verify-media-server

Preconditions:

- `doctor` prints `DOCTOR_OK`.
- `compose_files/.env` exists.

- **Health report.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive stack-health`. Exit code `0`. `proof/stack-health/stdout.txt` contains `=== Media Server Health ===`, `[OK] plex`, `[OK] radarr`, `[OK] sonarr`, and `sections` with a count greater than 0. `state.txt` contains `plex_identity_http=200` and Radarr and Sonarr ping bodies with `"status": "OK"`.
- **Layout.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive layout`. Exit code `0`. `proof/layout/stdout.txt` ends in a successful validate run and `state.txt` contains `validate=ok`.

## Gotchas

- Jellyfin and Prowlarr print as parked unless `COMPOSE_PROFILES` enables them. Parked is the expected line.
- `health-check.sh` reads API keys from appdata and does not print them. Proof that contains an API key or `X-Plex-Token` is invalid.
- `validate.sh` without `.env` is the CI path (`--ci`). On this host the live command omits `--ci`.
- Queue depth is informational. A non-empty queue still passes when the health commands exit 0.
