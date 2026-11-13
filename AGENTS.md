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


## Plex feature unlock (Freeloader)

The `plex` image is a local build, `freeloader-plex:lsio` ([`compose_files/freeloader/`](compose_files/freeloader/Dockerfile)): `lscr.io/linuxserver/plex` plus the [Freeloader](https://github.com/authrequest/Freeloader) feature-unlock `.so`, LD_PRELOADed by a wrapper the s6 svc-plex run file execs (still `s6-setuidgid abc`). The builder builds from [`compose_files/freeloader/vendor/`](compose_files/freeloader/vendor/) (pinned `FREELOADER_COMMIT` plus a local `hook.cpp` patch) and cross-compiles against musl with zig — upstream GitHub returns HTTP 451, so the image build does not `git clone`. At build time PMS’s bundled musl loader must resolve the `.so` preloaded into the real binary or the build fails.

The base image is version-locked to `lscr.io/linuxserver/plex:1.43.2.10687-563d026ea-ls313`, the PMS build the upstream hook signatures were derived from. On 1.43.4 the `.so` loads but PMS crash-loops within a minute (signatures match wrong sites), so `PLEX_BASE_IMAGE` and `FREELOADER_COMMIT` move together: a Plex update means re-deriving signatures for a newer PMS first. Watchtower is disabled on `plex` only, because a pull would replace the patched image with upstream and silently drop the unlock.

The vendored hook forces the global FeatureManager bitset **and** hooks PMS 1.43.2’s per-user feature-bit lookup. Bitset-only unlock leaves Skip Intro/Credits dead: markers stay in the library DB but `/library/metadata/…?includeMarkers=1` omits `Marker` nodes.

Apply or rebuild: `bash compose_files/scripts/build-freeloader-plex.sh`, then `docker compose --env-file .env up -d plex`. The upstream transcode session-limit `dd` patch applies on the pinned build; on any future drift the build warns loudly, writes `/usr/lib/plexmediaserver/TRANSCODE_PATCH_SKIPPED`, and ships without it (the `.so` unlock is the feature).

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
- Let watchtower manage `plex` (a pull replaces the patched local image and silently drops the Freeloader unlock).
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
| Plex feature unlock (Freeloader .so) | `compose_files/freeloader/`, `build-freeloader-plex.sh` |
