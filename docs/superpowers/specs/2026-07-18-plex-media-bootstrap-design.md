# Plex media bootstrap (greenfield) — design

Date: 2026-07-18  
Status: Approved (design); awaiting implementation plan  
Implementation method: **TDD required** (see below)

## Summary

Greenfield, free/open-source product: a **Node CLI wizard** that helps first-timers on **Linux + Docker** pick media-stack services, generate Compose, bring the stack up, and **auto-wire** apps together via APIs. Positioned as a focused, free alternative to Deployrr’s paid “pick apps” UX — media-only, not a full homelab OS.

Not a fork of Morzomb/All-jellyfin-media-server (that repo’s stars belong to the original author). This workspace may hold planning artifacts; implementation lands in a **new public repo**.

## Goals

1. First-timer completes setup without editing YAML by hand.
2. User chooses which optional services to include.
3. After `up`, core integrations work (Seerr ↔ *arr ↔ qBittorrent ↔ Prowlarr) without manual UI clicking — with clear fallbacks when auto-wire fails.
4. Generated output remains plain Docker Compose the user can inspect and keep.

## Non-goals (v1)

- Jellyfin
- Traefik / SSO / CrowdSec
- macOS or Windows hosts
- Web UI wizard
- VPN required (optional only)
- Claiming Deployrr-scale “160+ apps”

## Users

Primary: **first-timer** who wants pick apps → running stack, and should not need to touch YAML.

Secondary (natural): Docker-comfortable users who re-run `wire` or edit generated compose later.

## Product shape

### Always-on core

- Plex
- Seerr
- Sonarr
- Radarr
- Prowlarr
- qBittorrent

### Opt-in extras

- Jackett
- FlareSolverr
- Unpackerr
- Bazarr
- Tautulli
- Recyclarr
- Gluetun (VPN wrap for qBittorrent only)

### End-to-end flow

1. Preflight (`doctor`): Docker Engine, Compose v2, ports, disk, PUID/PGID.
2. Wizard prompts: paths, timezone, service checkboxes, optional VPN creds, Plex claim token.
3. Generate `docker-compose.yml` + `.env` + folder skeleton.
4. `docker compose up -d`.
5. Auto-wire via APIs; print ✅/❌ per step; UI fallback for failures.
6. Print service URLs and a short “verify request → download → import” check.

## Architecture

### Repo layout (new greenfield repo)

```
cli/                 # Node wizard + orchestrator
  prompts/
  generate/
  wire/
  doctor/
modules/             # one module per service
templates/           # shared volume/network snippets
docs/
tests/               # TDD home (behavior tests)
```

### Generation model

Each service is a **module** (image, ports, volumes, depends_on, env). The CLI selects modules and merges them into one compose file + `.env`. No proprietary runtime after generate — output is standard Compose.

### Networks

- `media` — Plex, Seerr, *arr, Prowlarr, extras
- `download` — qBittorrent (± Gluetun); Sonarr/Radarr attach to both

### Host filesystem (hardlink-safe)

Single media root (e.g. `/data`):

- `media/movies`, `media/tv`
- `torrents/movies`, `torrents/tv` (or equivalent download categories)
- `configs/<app>`

Aligned with TRaSH hardlink guidance: same container root path across *arr and download client.

### CLI surface

| Command | Purpose |
|---------|---------|
| `init` | Wizard → generate → up → wire |
| `up` / `down` / `update` | Thin compose wrappers |
| `wire` | Re-run auto-wire (idempotent) |
| `wire --retry` | Failed steps only |
| `doctor` | Preflight checks |

### Secrets

Plex claim token, VPN credentials, API keys in `.env` and/or gitignored `state.json`. Never logged.

## Auto-wire

### Order

1. Wait until target containers are healthy.
2. qBittorrent — categories `tv` / `movies`, save paths under torrents tree.
3. Sonarr / Radarr — root folders, download client → qBit (Docker DNS), baseline quality profile (or Recyclarr if opted in).
4. Prowlarr — app sync to Sonarr/Radarr; FlareSolverr if opted in.
5. Jackett (if opted) — surface Torznab URLs; Prowlarr remains primary indexer manager.
6. Seerr — Plex + Sonarr + Radarr.
7. Unpackerr / Bazarr / Tautulli — connect where APIs allow.

### Auth

Bootstrap or read API keys; persist in `.env` / `state.json` so `wire` is idempotent.

### Failure policy

- Steps are isolated; one failure does not abort the rest.
- Print ✅/❌ per step plus exact UI fallback (URL + fields).
- Non-zero exit only if **core** wiring failed (Sonarr/Radarr ↔ qBit, or Seerr ↔ *arr).
- Prefer “ensure setting exists” over blind overwrite.
- Optional: skip Plex restart if an active session is detected.

## Implementation method: TDD (mandatory)

All implementation of this product follows **test-driven development**. Relevant skills: Superpowers `test-driven-development` and local `tdd`.

### Iron rules

- **No production code without a failing test first.**
- **Vertical slices only** — one behavior: RED → GREEN → refactor; never write a bulk suite of tests then implement.
- Tests verify **behavior through public interfaces** (CLI commands, generate output, wire step results), not internal private helpers.
- Prefer integration-style tests of real generate/wire paths; mock only external HTTP boundaries (Sonarr/Radarr/Seerr/qBit APIs) and Docker where needed.
- If code was written before its test: **delete it** and re-implement from the test.

### TDD scope for v1

| Area | Test approach |
|------|----------------|
| `doctor` | Behavior tests against mocked/fake host checks |
| `generate` | Snapshot / assert compose + `.env` for core, core+VPN, core+extras |
| `compose config` | Generated files must pass `docker compose config` |
| `wire` steps | Unit/integration with mocked HTTP APIs; assert idempotency (second run adds no duplicates) |
| CLI `init` happy path | Orchestration test with fakes for Docker + APIs |

### Planning gate before coding each slice

Per `tdd` skill: confirm public interface and which behaviors to test with the human, then tracer-bullet the first RED→GREEN path.

## Testing & success criteria

### Automated

- Compose generation snapshots (core / +VPN / +all extras)
- `docker compose config` on generated output
- Wire step tests with mocked APIs
- Idempotent double-`wire`
- `doctor` dry-run

### Manual acceptance (v1 done)

1. Fresh Linux VM, Docker only → `init` completes without editing YAML.
2. Seerr request → *arr → qBit → import into `/data/media/...` via hardlink.
3. Opt-in VPN: qBit traffic via Gluetun; *arr still reach qBit.
4. Forced failure (e.g. Seerr down) → clear ❌ + fallback; other steps still ✅.
5. `wire --retry` repairs after recovery.

## Decisions log

| Decision | Choice |
|----------|--------|
| Repo strategy | Greenfield (not Morzomb fork) |
| Audience | First-timer |
| Interface | Node CLI wizard |
| Post-up wiring | Auto-wire via APIs (+ UI fallback) |
| Service menu | Core + opt-in extras (no Jellyfin in v1) |
| VPN | Optional Gluetun for qBit |
| Host | Linux + Docker Engine only |
| Architecture | Node CLI renders compose from modules |
| Quality bar | TDD vertical slices for all features |

## Open items (resolve at plan / first implement)

- Final public repo name and npm package name
- Node major version pin
- Exact image tags (linuxserver vs official) per module
- Whether Recyclarr runs as one-shot or scheduled container in v1
