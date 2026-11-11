# Agent bootstrap (fresh Linux)

This file is the procedure. [`CONTEXT.md`](CONTEXT.md) is the glossary. Do not invent a second playback target or a second acquire policy.

**Playback target** — Plex on Xbox Series X, picture on Samsung UE65U8092 (display only, LAN). Prefer **client-compatible** 4K WEB (HEVC HDR10, AAC/DD/DD+, sidecar SRT). Reject Dolby Vision, TrueHD, DTS-HD. **Quick Sync** is the only transcode fallback. Details: [`docs/adr/0001-direct-playable-audio.md`](docs/adr/0001-direct-playable-audio.md), [`docs/adr/0002-sidecar-srt.md`](docs/adr/0002-sidecar-srt.md).

## Automated sequence

Work from the repo root. Do not `docker compose down` as a routine step.

1. Install Docker Engine + Compose v2. Add the human user to `docker` and to `render` (or `video`) so `/dev/dri` works. They must log out/in once.
2. Copy [`compose_files/.env.example`](compose_files/.env.example) → `compose_files/.env`. Set `COMMON_PATH` (absolute, mergerfs media), `APPDATA_PATH` (absolute **SSD**, not mergerfs), `TZ`, `PUID`/`PGID` (`id -u`/`id -g`), `PLEX_ADVERTISE_IP` (`http://<lan-ip>:32400`), `SAME_DISK_SSD_ROOT`, `SAME_DISK_HDD_ROOT`. Quote `SIMKL_PLEX_WEBHOOK_URL` if present (`&` breaks `source`). Never commit `.env`.
3. Create dirs: `$COMMON_PATH`, library/download trees Radarr/Sonarr/qBittorrent expect, `$APPDATA_PATH`, `$PLEX_TRANSCODE_DIR` (local disk, **not** mergerfs). Existing hosts: stop the stack, `bash compose_files/scripts/migrate-appdata.sh`, then `up -d`.
4. `bash compose_files/validate.sh` (use `--ci` only in GitHub Actions; live hosts need `.env` + mounts).
5. `cd compose_files && docker compose --env-file .env up -d`
6. `bash compose_files/scripts/homelab-setup.sh --mode=all` — waits for *arr `config.xml`, writes Recyclarr/Unpackerr keys, Recyclarr sync (Direct Play scores), Bazarr English SRT policy, Tautulli→Plex, SIMKL webhook if the URL is set.
7. Install boot persistence: `sudo bash compose_files/systemd/install-media-server-unit.sh` then `sudo systemctl enable --now media-server.service`. That regenerates the unit from this clone path and `.env` mounts (the checked-in `.service` is this host’s copy), and installs and enables `media-backup.timer` (nightly restic snapshot of `APPDATA_PATH`, [`scripts/backup-appdata.sh`](compose_files/scripts/backup-appdata.sh)) and `media-monitor.timer` (5-minute ntfy alerts, [`scripts/stack-monitor.py`](compose_files/scripts/stack-monitor.py)). Set `RESTIC_REPOSITORY` (another physical disk), `RESTIC_PASSWORD_FILE` (root-only, created with `openssl rand -base64 32`) and `NTFY_URL` in `.env` first.
8. Verify: `bash compose_files/scripts/health-check.sh` and `PYTHONPATH=compose_files/scripts python3 -m unittest test_stack_policy -v`.

Updates: watchtower is monitor-only and posts new images to `WATCHTOWER_NOTIFICATION_URL`. Update deliberately: `docker compose --env-file .env pull && docker compose --env-file .env up -d`, then `health-check.sh`.

Restore: `restic restore latest --target /tmp/r` with the `.env` repository and password file. Live SQLite files are not in the snapshot; their consistent copies are under `/var/lib/media-server/sqlite-snapshots/<same path below APPDATA_PATH>`. Stop the stack, copy both trees back, delete stale `*.db-wal`/`*.db-shm`, start.

Reboots: `media-server.service` runs `docker compose up -d` then [`scripts/boot-ensure-hardlink-policy.sh`](compose_files/scripts/boot-ensure-hardlink-policy.sh) → `homelab-setup.sh --mode=boot` (no queue wipe, no qBittorrent restart, no Recyclarr). Boot also searches monitored missing TV/movies released in the last 14 days so downtime does not skip RSS-only grabs.

## Plex feature unlock (Freeloader)

The `plex` image is a local build, `freeloader-plex:lsio` ([`compose_files/freeloader/`](compose_files/freeloader/Dockerfile)): `lscr.io/linuxserver/plex` plus the [Freeloader](https://github.com/authrequest/Freeloader) feature-unlock `.so`, LD_PRELOADed by a wrapper the s6 svc-plex run file execs (still `s6-setuidgid abc`). The builder builds from [`compose_files/freeloader/vendor/`](compose_files/freeloader/vendor/) (pinned `FREELOADER_COMMIT` plus a local `hook.cpp` patch) and cross-compiles against musl with zig — upstream GitHub returns HTTP 451, so the image build does not `git clone`. At build time PMS’s bundled musl loader must resolve the `.so` preloaded into the real binary or the build fails.

The base image is version-locked to `lscr.io/linuxserver/plex:1.43.2.10687-563d026ea-ls313`, the PMS build the upstream hook signatures were derived from. On 1.43.4 the `.so` loads but PMS crash-loops within a minute (signatures match wrong sites), so `PLEX_BASE_IMAGE` and `FREELOADER_COMMIT` move together: a Plex update means re-deriving signatures for a newer PMS first. Watchtower is disabled on `plex` only, because a pull would replace the patched image with upstream and silently drop the unlock. `stack_policy.layout` fails validation if the watchtower label is not `"false"` on the local image.

The vendored hook forces the global FeatureManager bitset **and** hooks PMS 1.43.2’s per-user feature-bit lookup. Bitset-only unlock leaves Skip Intro/Credits dead: markers stay in the library DB but `/library/metadata/…?includeMarkers=1` omits `Marker` nodes.

Apply or rebuild: `bash compose_files/scripts/build-freeloader-plex.sh`, then `docker compose --env-file .env up -d plex`. The upstream transcode session-limit `dd` patch applies on the pinned build; on any future drift the build warns loudly, writes `/usr/lib/plexmediaserver/TRANSCODE_PATCH_SKIPPED`, and ships without it (the `.so` unlock is the feature).

## Human-only (agent cannot finish these)

- **Disks / mergerfs** — pool at `COMMON_PATH`’s parent, branches at `SAME_DISK_*` parents, `category.create=epmfs`. Do not bind-mount downloads onto the SSD. See [`compose_files/systemd/README.md`](compose_files/systemd/README.md).
- **Plex claim** — `PLEX_CLAIM` from https://plex.tv/claim (expires in minutes); sign-in; enable **Settings → Transcoder → Use hardware acceleration**.
- **SIMKL** — unique webhook from https://simkl.com/apps/plex into quoted `SIMKL_PLEX_WEBHOOK_URL`, then `--mode=boot`.
- **Xbox Plex** — Burn subtitles → **Only image formats**. Quality Original / LAN.
- **qBittorrent** — password is in `docker logs qbittorrent` on first start; change it.
- **Jackett / Seerr** — indexers and Plex request wiring are UI.
- **Tailscale** — `sudo tailscale up --operator=$USER --hostname=media-server --accept-dns=false` needs a browser login. Put `http://$(tailscale ip -4):32400` into `PLEX_ADVERTISE_IP` after the LAN URL and keep `PLEX_LAN_NETWORKS` listing the home LAN plus `100.64.0.0/10`. Install Tailscale on phones/laptops; every UI is then at `http://media-server.<tailnet>.ts.net:<port>`. Do not port-forward.
- **Alerts** — subscribe to the `NTFY_URL` topic in the ntfy app. Keep a copy of the restic password off this machine, or the backup is unreadable after a host loss.
- **Omarchy idle hitch** — desktop-only [`compose_files/scripts/plex-idle-guard.py`](compose_files/scripts/plex-idle-guard.py): stay-awake while Plex plays (Xbox Direct Play hitchs on lock/power-saver), DPMS off the PC monitor when playback is remote and you are idle, `power-saver` after 15 minutes idle with no Plex. 4TB media HDD spindown: [`systemd/69-media-hdd-spindown.rules`](compose_files/systemd/69-media-hdd-spindown.rules). Not required on a headless NAS.

## Do not

- Split `/movies`+`/downloads` volume binds (breaks **hardlink-safe layout**).
- Point `PLEX_TRANSCODE_DIR` or `APPDATA_PATH` at mergerfs.
- Turn watchtower auto-pull back on (`WATCHTOWER_MONITOR_ONLY=false`) without being asked.
- Let watchtower manage `plex` (a pull replaces the patched local image and silently drops the Freeloader unlock; `stack_policy.layout` enforces).
- Prefer UHD remux/TrueHD/DTS/DoVi or PGS as the subtitle plan.
- Enable Jellyfin/Prowlarr unless asked (`COMPOSE_PROFILES`).
- Commit `compose_files/.env`, Recyclarr `secrets.yml`, or API keys.

## Policy owners

| Concern | Owner |
| --- | --- |
| Volume layout | `stack_policy.layout`, `validate.sh` |
| Appdata on local disk | `APPDATA_PATH` compose binds, `migrate-appdata.sh` |
| *arr hardlinks / SRT extras | `stack_policy.arr`, `homelab-setup.sh` |
| Acquire profile (4K-first, 720p ok, no upgrades) | `stack_policy.arr`, `compose_files/recyclarr/recyclarr.yml` |
| Release language Any (HuN dual-audio OK) | `stack_policy.arr.with_any_language`, `homelab-setup.sh` |
| Recent missing catch-up after downtime | `stack_policy.catchup`, `homelab-setup.sh` (`--mode=boot`) |
| qBittorrent unbounded seeding | `stack_policy.qbittorrent`, `homelab-setup.sh` |
| Direct Play scores | `stack_policy.playback_compat`, `compose_files/recyclarr/recyclarr.yml` |
| Sidecar SRT | `stack_policy.bazarr` |
| SIMKL watched | `stack_policy.tautulli` |
| Plex transcode temp + advertise + LAN networks | `stack_policy.plex_prefs`, `plex-init.sh` |
| Health alerts + unhealthy restart | `stack_policy.monitor`, `stack-monitor.py`, compose `healthcheck` |
| Appdata backup | `backup-appdata.sh`, `media-backup.timer` |
| Plex feature unlock (Freeloader .so) | `compose_files/freeloader/`, `build-freeloader-plex.sh` |
| Paperless-ngx (SQLite on APPDATA_PATH, `:8010`, tailnet `PAPERLESS_URL`, Tika + Gotenberg for Office files, OCR `ron+hun+eng`) | `docker-compose.yaml`, `backup-appdata.sh` (`db.sqlite3` snapshot) |
