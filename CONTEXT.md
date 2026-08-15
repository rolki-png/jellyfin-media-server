# Domain language

Terms for this repo. Architecture reviews and scripts should use these names.

**Hardlink-safe layout** — Radarr/Sonarr see library and downloads as one filesystem (`COMMON_PATH`). Split `/movies`+`/downloads` binds are forbidden (EXDEV → copies). Owned by `stack_policy.layout`; compose volumes and `validate.sh` are callers.

**Same-disk import** — On *arr import, keep one inode on the download’s disk; migrate the title folder if it still lives on the other mergerfs branch. Runtime adapter: `same-disk-import.sh` inside Sonarr/Radarr (no Python in those images). Host policy (Connect registration, `copyUsingHardlinks`) is `homelab-setup.sh --mode=boot`.

**Stack policy** — Host-side module (`compose_files/scripts/stack_policy`) for layout checks, *arr JSON transforms, Recyclarr profile names, and Plex Preferences.xml (transcode temp + advertise URL). Stdlib only.

**Plex host readiness** — Transcode on local disk (`/transcode`, not mergerfs); LAN advertise URL from `PLEX_ADVERTISE_IP`. Boot-time adapter: `plex-init.sh` (symlink + prefs before Plex starts). Re-assert adapter: `stack_policy.plex_prefs` from homelab-setup.

**Boot vs all** — `homelab-setup.sh --mode=boot` reapplies hardlink + Plex host policy without queue wipes, qBittorrent restart, Recyclarr sync, or bulk quality-profile edits (those hitch streams). Default `--mode=all` is first-run / manual.
