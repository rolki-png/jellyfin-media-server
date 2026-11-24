# Domain language

Terms for this repo. Architecture reviews and scripts should use these names.

**Hardlink-safe layout** — Radarr/Sonarr see library and downloads as one filesystem (`COMMON_PATH`). Split `/movies`+`/downloads` binds are forbidden (EXDEV → copies). Owned by `stack_policy.layout`; compose volumes and `validate.sh` are callers.

**Appdata on local disk** — SQLite `/config` for Plex/*arr/qBittorrent lives on `APPDATA_PATH` (real SSD), never on the mergerfs media pool. Owned by `stack_policy.layout`; compose `/config` binds and `migrate-appdata.sh` are callers.

**Same-disk import** — On *arr import, keep one inode on the download’s disk; migrate the title folder if it still lives on the other mergerfs branch. Runtime adapter: `same-disk-import.sh` inside Sonarr/Radarr (no Python in those images). Host policy (Connect registration, `copyUsingHardlinks`) is `homelab-setup.sh --mode=boot`.

**Stack policy** — Host-side module (`compose_files/scripts/stack_policy`) for layout checks, *arr JSON transforms, Recyclarr profile names, Plex Preferences.xml, Bazarr sidecar SRT, and Tautulli SIMKL. Bash (`homelab-setup.sh`) is the docker/curl adapter; tests hit the Python interface. Stdlib only.

**Plex host readiness** — Transcode on local disk (`/transcode`, not mergerfs); LAN advertise URL from `PLEX_ADVERTISE_IP`. Boot-time adapter: `plex-init.sh` (symlink + prefs before Plex starts). Re-assert adapter: `stack_policy.plex_prefs` from homelab-setup.

**Boot vs all** — `homelab-setup.sh --mode=boot` reapplies hardlink + Plex host policy + default quality profiles (720p allowed, no upgrades) and searches recent missing TV/movies (14-day lookback) without queue wipes, qBittorrent restart, or Recyclarr sync. Default `--mode=all` is first-run / manual.

**Freeloader unlock** — LD_PRELOAD library (authrequest/Freeloader, musl build) that flips Plex’s paid-feature bits on inside the `plex` container. The plex image is a local build (`freeloader-plex:lsio`) on a version-locked base (PMS 1.43.2.10687, the build the hook signatures match); Plex updates wait for upstream signature support, then `PLEX_BASE_IMAGE` + `FREELOADER_COMMIT` bump together and `build-freeloader-plex.sh` rebuilds. Watchtower is disabled on plex (a pull would replace the patched image with upstream). Owned by `compose_files/freeloader/` + `build-freeloader-plex.sh`; `stack_policy.layout` forbids the watchtower label on that image.

## Playback

**Desktop idle policy** — While Plex is playing (including paused) on the playback target, this desktop must not lock or drop to power-saver. The PC monitor may DPMS off if the player is not this machine. After 15 minutes with no input and no Plex, use power-saver. Owned by `stack_policy.plex_idle`; `plex-idle-guard.py` is the Omarchy adapter.

**Direct Play** — Plex sends the file unchanged: no video transcode, no audio transcode, no subtitle burn-in.
_Avoid_: Direct Stream (audio/container remux while video stays; this hitchs on Xbox)

**Quick Sync transcode** — Hardware transcode on this host’s Intel UHD 770. The only acceptable fallback when Direct Play is impossible.
_Avoid_: CPU transcode (software 4K/HDR/PGS burn-in is not a supported path)

**Client-compatible release** — A file the playback target can Direct Play: 4K (or 1080p fallback) HEVC HDR10/HDR10+, audio AAC or Dolby Digital / DD+ (including DD+ Atmos), text SRT sidecars. TrueHD, DTS-HD, and Dolby Vision are not client-compatible here.

**Watch-history sync** — Copying Plex playback that reached Tautulli’s watched threshold onto SIMKL. Independent of Direct Play.

**Sidecar SRT** — A `.srt` file next to the video that Plex on Xbox overlays without burn-in. PGS, VobSub, and ASS are not sidecar SRT; they force a transcode on this playback target.
