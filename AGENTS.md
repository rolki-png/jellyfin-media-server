# Agent bootstrap (fresh Linux)

This file is the procedure. [`CONTEXT.md`](CONTEXT.md) is the glossary. Do not invent a second playback target or a second acquire policy.

**Playback target** — Plex on Xbox Series X, picture on Samsung UE65U8092 (display only, LAN). Prefer **client-compatible** 4K WEB (HEVC HDR10, AAC/DD/DD+, sidecar SRT). Reject Dolby Vision, TrueHD, DTS-HD. **Quick Sync** is the only transcode fallback. Details: [`docs/adr/0001-direct-playable-audio.md`](docs/adr/0001-direct-playable-audio.md), [`docs/adr/0002-sidecar-srt.md`](docs/adr/0002-sidecar-srt.md).

## Automated sequence

Work from the repo root. Do not `docker compose down` as a routine step.

1. Install Docker Engine + Compose v2. Add the human user to `docker` and to `render` (or `video`) so `/dev/dri` works. They must log out/in once.
2. Copy [`compose_files/.env.example`](compose_files/.env.example) → `compose_files/.env`. Set `COMMON_PATH` (absolute), `TZ`, `PUID`/`PGID` (`id -u`/`id -g`), `PLEX_ADVERTISE_IP` (`http://<lan-ip>:32400`), `SAME_DISK_SSD_ROOT`, `SAME_DISK_HDD_ROOT`. Quote `SIMKL_PLEX_WEBHOOK_URL` if present (`&` breaks `source`). Never commit `.env`.
3. Create dirs: `$COMMON_PATH`, library/download trees Radarr/Sonarr/qBittorrent expect, `$PLEX_TRANSCODE_DIR` (local disk, **not** mergerfs).
4. `bash compose_files/validate.sh` (use `--ci` only in GitHub Actions; live hosts need `.env` + mounts).
5. `cd compose_files && docker compose --env-file .env up -d`
6. `bash compose_files/scripts/homelab-setup.sh --mode=all` — waits for *arr `config.xml`, writes Recyclarr/Unpackerr keys, Recyclarr sync (Direct Play scores), Bazarr English SRT policy, Tautulli→Plex, SIMKL webhook if the URL is set.
7. Install boot persistence: `sudo bash compose_files/systemd/install-media-server-unit.sh` then `sudo systemctl enable --now media-server.service`. That regenerates the unit from this clone path and `.env` mounts (the checked-in `.service` is this host’s copy).
8. Verify: `bash compose_files/scripts/health-check.sh` and `PYTHONPATH=compose_files/scripts python3 -m unittest test_stack_policy -v`.

Reboots: `media-server.service` runs `docker compose up -d` then [`scripts/boot-ensure-hardlink-policy.sh`](compose_files/scripts/boot-ensure-hardlink-policy.sh) → `homelab-setup.sh --mode=boot` (no queue wipe, no qBittorrent restart, no Recyclarr).

## Human-only (agent cannot finish these)

- **Disks / mergerfs** — pool at `COMMON_PATH`’s parent, branches at `SAME_DISK_*` parents, `category.create=epmfs`. Do not bind-mount downloads onto the SSD. See [`compose_files/systemd/README.md`](compose_files/systemd/README.md).
- **Plex claim** — `PLEX_CLAIM` from https://plex.tv/claim (expires in minutes); sign-in; enable **Settings → Transcoder → Use hardware acceleration**.
- **SIMKL** — unique webhook from https://simkl.com/apps/plex into quoted `SIMKL_PLEX_WEBHOOK_URL`, then `--mode=boot`.
- **Xbox Plex** — Burn subtitles → **Only image formats**. Quality Original / LAN.
- **qBittorrent** — password is in `docker logs qbittorrent` on first start; change it.
- **Jackett / Seerr** — indexers and Plex request wiring are UI.
- **Omarchy idle hitch** — optional [`compose_files/scripts/plex-idle-guard.py`](compose_files/scripts/plex-idle-guard.py) on this desktop only (screensaver hitchs Xbox Direct Play). Not required on a headless NAS.

## Do not

- Split `/movies`+`/downloads` volume binds (breaks **hardlink-safe layout**).
- Point `PLEX_TRANSCODE_DIR` at mergerfs.
- Prefer UHD remux/TrueHD/DTS/DoVi or PGS as the subtitle plan.
- Enable Jellyfin/Prowlarr unless asked (`COMPOSE_PROFILES`).
- Commit `compose_files/.env`, Recyclarr `secrets.yml`, or API keys.

## Policy owners

| Concern | Owner |
| --- | --- |
| Volume layout | `stack_policy.layout`, `validate.sh` |
| *arr hardlinks / SRT extras | `stack_policy.arr`, `homelab-setup.sh` |
| Direct Play scores | `stack_policy.playback_compat`, `compose_files/recyclarr/recyclarr.yml` |
| Sidecar SRT | `stack_policy.bazarr` |
| SIMKL watched | `stack_policy.tautulli` |
| Plex transcode temp + advertise | `stack_policy.plex_prefs`, `plex-init.sh` |
