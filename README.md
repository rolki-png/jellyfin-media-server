# Media server stack

<div align="center">
  <img src="image/Isyrr.png" alt="Isyrr" width="280">
</div>

Docker Compose stack for a **Plex-first** home media library: acquire with Sonarr/Radarr, request with Seerr, stream with Plex. Hardware transcoding uses an **Intel iGPU** (`/dev/dri`, Quick Sync / VAAPI).

Compose file: [`compose_files/docker-compose.yaml`](compose_files/docker-compose.yaml)

## Services

| Role | Always on | Parked (Compose profile) |
| --- | --- | --- |
| Streamer | [Plex](https://www.plex.tv/) | [Jellyfin](https://jellyfin.org/) (`jellyfin`) |
| Requests | [Seerr](https://docs.seerr.dev/) | — |
| TV / movies | [Sonarr](https://sonarr.tv/), [Radarr](https://radarr.video/) | — |
| Indexers | [Jackett](https://github.com/Jackett/Jackett) | [Prowlarr](https://prowlarr.com/) (`prowlarr`) |
| Downloads | [qBittorrent](https://www.qbittorrent.org/), [Unpackerr](https://unpackerr.zip/) | — |
| Subtitles | [Bazarr](https://www.bazarr.media/) (English SRT sidecars; PGS ignored) | — |
| Watch stats / SIMKL | [Tautulli](https://tautulli.com/) (Plex watched → SIMKL webhook) | — |
| Cloudflare helper | [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) (localhost only) | — |
| Quality profiles | [Recyclarr](https://recyclarr.dev/) (TRaSH Guides, cron) | — |
| Image updates | [Watchtower](https://watchtower.nickfedor.com/) (`nickfedor/watchtower`) | — |

Bring parked services back:

```bash
cd compose_files
COMPOSE_PROFILES=jellyfin docker compose up -d jellyfin
COMPOSE_PROFILES=prowlarr docker compose up -d prowlarr
```

## Prerequisites

- Linux host with [Docker Engine](https://docs.docker.com/engine/install/) and the **Compose v2** plugin (`docker compose`, not `docker-compose`).
- Enough RAM for Plex plus *arr apps (8 GB is a practical minimum).
- For hardware transcoding: Intel iGPU with `/dev/dri` present. The LinuxServer PUID must be able to use the render node (typically the host `render` or `video` group).
- Plex transcode temp must be on **local disk**, not mergerfs/FUSE. Set `PLEX_TRANSCODE_DIR` (default `/var/lib/plex-transcode`).

Install Docker with the official convenience script if needed:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker "$USER"
```

Log out and back in after adding the user to the `docker` group.

## Install

```bash
git clone https://github.com/roland-kiraly/All-jellyfin-media-server.git
cd All-jellyfin-media-server
cp compose_files/.env.example compose_files/.env
```

Edit `compose_files/.env`:

- `COMMON_PATH` — absolute path for configs and media
- `TZ` — IANA timezone
- `PUID` / `PGID` — `id -u` / `id -g` of the host user
- `PLEX_ADVERTISE_IP` — LAN URL clients should use, e.g. `http://192.168.0.236:32400`
- `PLEX_CLAIM` — one-time token from [plex.tv/claim](https://plex.tv/claim) (expires in a few minutes)

```bash
bash compose_files/validate.sh
cd compose_files
docker compose up -d
```

First-run wiring (hardlinks, qBittorrent categories, Recyclarr secrets, Plex notifications) is [`compose_files/scripts/homelab-setup.sh`](compose_files/scripts/homelab-setup.sh) (`--mode=all`, default). Boot only reapplies hardlink + Plex host policy: `--mode=boot` (no qBittorrent restart). See [`compose_files/systemd/README.md`](compose_files/systemd/README.md).

## URLs

Replace the host with your LAN IP if you are not on the server.

| App | URL |
| --- | --- |
| Plex | http://localhost:32400/web |
| Seerr | http://localhost:5055 |
| Sonarr | http://localhost:8989 |
| Radarr | http://localhost:7878 |
| Jackett | http://localhost:9117 |
| qBittorrent | http://localhost:8080 |
| Tautulli | http://localhost:8181 |
| Jellyfin (profile) | http://localhost:8096 |
| Prowlarr (profile) | http://localhost:9696 |

FlareSolverr listens on `127.0.0.1:8191` on the host. Jackett reaches it as `http://flaresolverr:8191` on the Compose network.

qBittorrent no longer ships a fixed default password. Read the generated password from `docker logs qbittorrent` and change it immediately.

## Hardware transcoding

Plex (and Jellyfin, if enabled) mount `/dev/dri`. Enable hardware acceleration in Plex: **Settings → Transcoder → Use hardware acceleration when available**.

Do not point `PLEX_TRANSCODE_DIR` at mergerfs. FUSE is too slow for live transcode.

## Quality profiles (Recyclarr)

Recyclarr uses image tag **`:8`**. Recyclarr no longer publishes `:latest`. The container stays up and syncs on `CRON_SCHEDULE` (default `@daily`). Config: [`compose_files/recyclarr/recyclarr.yml`](compose_files/recyclarr/recyclarr.yml).

Manual sync:

```bash
docker exec recyclarr recyclarr sync
```

## Updating images

Watchtower is [`nickfedor/watchtower`](https://watchtower.nickfedor.com/) (the original `containrrr/watchtower` image is unmaintained and fails on Docker Engine 29+). It polls every 6 hours by default, updates containers labeled `com.centurylinklabs.watchtower.enable=true`, and prunes old images.

- Keep `WATCHTOWER_ROLLING_RESTART` **off**. Rolling restart is incompatible with Compose `depends_on` (Plex/Jellyfin init containers).
- Use `WATCHTOWER_POLL_INTERVAL` **or** `WATCHTOWER_SCHEDULE`, not both.
- In-app “update available” banners in Radarr/Sonarr track the app channel; LinuxServer images can lag that by a few days.

```bash
cd compose_files
docker compose up -d watchtower
docker compose run --rm watchtower --run-once
docker logs -f watchtower
```

Manual pull:

```bash
cd compose_files
docker compose pull
docker compose up -d
```

Do not run `docker compose down` as a routine update: that tears down the stack. Prefer `pull` + `up -d`, or Watchtower.

## SIMKL (Plex watch history)

This stack has no Plex Pass, so Plex cannot call SIMKL’s official webhook itself. [Tautulli](https://tautulli.com/) (`lscr.io/linuxserver/tautulli`) watches Plex sessions and, on **Watched**, POSTs SIMKL’s documented Plex-shaped payload.

One browser step: sign in at [simkl.com/apps/plex](https://simkl.com/apps/plex), copy the unique webhook URL into `compose_files/.env` as `SIMKL_PLEX_WEBHOOK_URL`, then run [`compose_files/scripts/homelab-setup.sh`](compose_files/scripts/homelab-setup.sh). Tautulli is http://localhost:8181.

`SIMKL_CLIENT_ID` / `SIMKL_CLIENT_SECRET` stay in `.env` for the SIMKL app registration. The Tautulli path uses the webhook URL, not those OAuth tokens.

## Layout notes

Radarr and Sonarr mount a single `COMMON_PATH` so imports can **hardlink** from downloads into the library. Separate `/movies` + `/downloads` binds look like different filesystems and force copies.

Health summary: [`compose_files/scripts/health-check.sh`](compose_files/scripts/health-check.sh).

## Disclaimer

This repository is for operating a personal media library. You are responsible for complying with the laws that apply to you.
