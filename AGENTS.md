# AGENTS.md

## Cursor Cloud specific instructions

This is a Docker Compose orchestration project (no application source code to build). All services run as pre-built container images.

### Project structure

- `compose_files/docker-compose.yaml` — base compose file (all services, CPU-only transcoding)
- `compose_files/docker-compose.gpu.yaml` — GPU overlay (adds NVIDIA hardware transcoding to Jellyfin/Plex)
- `compose_files/start.sh` — auto-detects GPU and starts the stack with the right compose files
- `compose_files/update.sh` — pulls latest images and recreates containers (also auto-detects GPU)
- `compose_files/validate.sh` — lints both compose files and validates required env vars
- `compose_files/.env.example` — template environment config
- `compose_files/.env` — active environment config (not committed)

### Validation / Lint

```bash
bash compose_files/validate.sh
```

Use `--ci` flag to run without a `.env` file (falls back to `.env.example`).

### Running the stack

GPU detection is automatic. A single command starts everything:

```bash
bash compose_files/start.sh
```

On a machine with an NVIDIA GPU + nvidia-container-toolkit, Jellyfin and Plex get GPU-accelerated transcoding. Without a GPU, they fall back to CPU — no manual flags needed. The cloud VM has no GPU, so the stack always starts in CPU mode here.

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
