# Plex-first streaming stack optimization

Date: 2026-07-17  
Status: Implemented (stream-safe trim + Xbox LAN / Plex polish)

## Goals (equal weight)

1. **Xbox playback:** LAN / Original / Direct Play for 4K HEVC when possible; no surprise quality drops.
2. **Host snappiness:** Library scans / downloads should not fight active Plex streams.
3. **Lower idle footprint:** Fewer always-on containers without deleting configs.

## Constraints

- Plex on Xbox is the primary client (home LAN only).
- Jellyfin kept installable but parked (compose profile), not deleted.
- Jackett stays (Sonarr/Radarr Torznab → Jackett nCore + RoTorrent).
- Seerr + Jellyseerr both left running until a later choice. *(Resolved 2026-08-15: Seerr only.)*
- Do not restart or reconfigure Plex while a session is active.

## Target service map

| Role | Always-on | Parked (profile) |
|---|---|---|
| Streamer | Plex | Jellyfin (`jellyfin`) |
| Indexer | Jackett | Prowlarr (`prowlarr`) — no synced *arr apps |
| Requests | Seerr | — |
| Acquire | Sonarr, Radarr, qBittorrent, FlareSolverr, Unpackerr | — |
| Ops | Watchtower | — |

Bring-back:

```bash
COMPOSE_PROFILES=jellyfin docker compose up -d jellyfin
COMPOSE_PROFILES=prowlarr docker compose up -d prowlarr
```

Configs remain under `${COMMON_PATH}/configs/`.

## Implemented (2026-07-17, stream-safe)

- Added Compose profiles `jellyfin` and `prowlarr` in `compose_files/docker-compose.yaml`.
- Stopped and removed running `jellyfin`, `jellyfin-init`, `prowlarr` containers without touching Plex.
- Updated `compose_files/scripts/health-check.sh` and `.env.example` for the Plex-first default.
- Verified active Xbox Silo session remained `playing` after the park.

## Implemented (2026-07-18, deferred Xbox LAN / Plex polish)

Ran with **no active Plex sessions**.

### Xbox LAN path

- Confirmed `ADVERTISE_IP` / `customConnections` = `http://192.168.0.236:32400` (updated 2026-08-15; host DHCP moved off `.2`).
- Kept `allowedNetworks` covering `192.168.0.0/24` and Docker ranges (dropped ULA `fd00::/8` after disabling IPv6).
- `RelayEnabled=0`, `GdmEnabled=1`.
- Set `EnableIPv6=0` so living-room clients prefer IPv4 LAN instead of plex.tv-over-IPv6 (`location=wan` false positive).

### Playback / host protection

- Transcoder temp remains on local disk (`/transcode` → `PLEX_TRANSCODE_DIR`); Cache/Transcode symlink restored via fixed `plex-init`.
- Raised Plex `mem_limit` from 2g → **3g**.
- Butler window moved to **03:00–06:00** (deep analysis stays Butler-gated).
- Sonarr/Radarr Plex notifications verified (host `plex`, onDownload/onUpgrade).

### Compose hygiene

- Escaped `$cache` / `$prefs` in `plex-init` as `$$…` so Compose no longer empties them (was causing `plex-init` exit 1: `mkdir: can't create directory ''`).

## Success checks

- `docker compose ... config --services` does **not** list jellyfin/prowlarr unless profiles set.
- Idle RAM down ~Jellyfin+Prowlarr (~0.3–0.4 GiB observed).
- `plex-init` exits 0; `/config/.../Cache/Transcode` → `/transcode`.
- After Xbox playback: session should show `location=lan` with Direct Play for typical 4K WEB HEVC (non-DoVi) — confirm on next watch.
- During playback: no forced Plex restart; downloads/scans do not stall the stream.

## Follow-ups (optional later)

- Choose one of Seerr vs Jellyseerr. *(Resolved 2026-08-15: Seerr only.)*
- Decide whether Prowlarr should ever replace Jackett (only after explicit Torznab cutover).
- If Xbox still reports `wan`, set a manual server connection on the Xbox to `http://192.168.0.236:32400`.

## Non-goals

- Deleting Jellyfin/Prowlarr data.
- Migrating indexers off Jackett in this pass.
- Hardware transcoding uses Intel Quick Sync via `/dev/dri`; this stack does not use a discrete GPU runtime.
