# AGENTS.md

## Cursor Cloud specific instructions

This is a Docker Compose orchestration project (no application source code to build). All services run as pre-built container images.

### Project structure

- `compose_files/docker-compose-nvidia.yaml` — main compose file (all 9 services, requires NVIDIA GPU)
- `compose_files/docker-compose-no-gpu.yaml` — override for Jellyfin/Plex without GPU (for cloud/CI environments)
- `compose_files/.env.example` — template environment config
- `compose_files/.env` — active environment config (not committed)
- `compose_files/validate.sh` — lints the compose config and validates required env vars

### Validation / Lint

```bash
bash compose_files/validate.sh
```

Use `--ci` flag to run without a `.env` file (falls back to `.env.example`).

### Running the stack (no GPU)

The main compose file requires an NVIDIA GPU. In the cloud VM, use the no-GPU override for Jellyfin/Plex:

```bash
# Non-GPU services (start these from docker-compose-nvidia.yaml)
cd compose_files
sudo docker compose -f docker-compose-nvidia.yaml up -d qbittorrent flaresolverr prowlarr jackett sonarr radarr jellyseerr

# Jellyfin without GPU (uses the override file)
sudo docker compose -f docker-compose-no-gpu.yaml --env-file .env up -d jellyfin
```

Plex is optional and can also be started via `docker-compose-no-gpu.yaml` if needed.

### Environment setup

1. Copy `.env.example` to `.env`: `cp compose_files/.env.example compose_files/.env`
2. `COMMON_PATH` defaults to `/srv/media/isyrr` — create it with `sudo mkdir -p /srv/media/isyrr`
3. Create subdirectories: `sudo mkdir -p /srv/media/isyrr/{configs/{qbittorrent,prowlarr,jackett,sonarr,radarr,jellyfin,jellyseerr,plex},qbittorrent/downloads,sonarr/tv,radarr/movies,jellyfin/cache,plex/transcode}`
4. Ensure writable: `sudo chmod -R 777 /srv/media/isyrr`

### Service ports

See `README.md` section "Accessing Applications" for the full port list. Key services: Jellyfin `:8096`, Sonarr `:8989`, Radarr `:7878`, Prowlarr `:9696`, qBittorrent `:8080`.

### Keeping containers up to date

Watchtower runs as part of the stack and automatically pulls and redeploys containers when new images are published (default: every 24 h, configurable via `WATCHTOWER_POLL_INTERVAL` in `.env`). For on-demand updates, use `bash compose_files/update.sh` (see `--help` for options). See the README "Updating Applications" section for full details.

### Gotchas

- Docker must be started manually in DinD environments: `sudo dockerd &>/tmp/dockerd.log &` (wait ~3s before running compose commands).
- qBittorrent generates a temporary password on first start; check `sudo docker compose logs qbittorrent` for the initial credentials.
- There is no automated test suite — validation is via `validate.sh` and manual service health checks (`curl` or browser).
