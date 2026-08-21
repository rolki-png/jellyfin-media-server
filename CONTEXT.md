# Domain language

Terms for this repo. Architecture reviews and scripts should use these names.

**Hardlink-safe layout** — Radarr/Sonarr see library and downloads as one filesystem (`COMMON_PATH`). Split `/movies`+`/downloads` binds are forbidden (EXDEV → copies). Owned by `stack_policy.layout`; compose volumes and `validate.sh` are callers.

**Same-disk import** — On *arr import, keep one inode on the download’s disk; migrate the title folder if it still lives on the other mergerfs branch. Runtime adapter: `same-disk-import.sh` inside Sonarr/Radarr (no Python in those images). Host policy (Connect registration, `copyUsingHardlinks`) is `homelab-setup.sh --mode=boot`.

**Stack policy** — Host-side module (`compose_files/scripts/stack_policy`) for layout checks, *arr JSON transforms, Recyclarr profile names, Plex Preferences.xml (transcode temp + advertise URL), and Tautulli’s SIMKL webhook. Stdlib only.

**Plex host readiness** — Transcode on local disk (`/transcode`, not mergerfs); LAN advertise URL from `PLEX_ADVERTISE_IP`. Boot-time adapter: `plex-init.sh` (symlink + prefs before Plex starts). Re-assert adapter: `stack_policy.plex_prefs` from homelab-setup.

**Boot vs all** — `homelab-setup.sh --mode=boot` reapplies hardlink + Plex host policy without queue wipes, qBittorrent restart, Recyclarr sync, or bulk quality-profile edits (those hitch streams). Default `--mode=all` is first-run / manual.

## Playback

**Playback target** — The Xbox Series X running Plex, displayed on a Samsung Crystal UHD (UE65U8092 / U8000F). That panel is 4K HDR10/HDR10+ with no Dolby Vision and 2.0 speakers.
_Avoid_: “the client”, “the TV app” (unless we later name a second streamer)

**Direct Play** — Plex sends the file unchanged: no video transcode, no audio transcode, no subtitle burn-in.
_Avoid_: Direct Stream (audio/container remux while video stays; this hitchs on Xbox)

**Quick Sync transcode** — Hardware transcode on this host’s Intel UHD 770. The only acceptable fallback when Direct Play is impossible.
_Avoid_: CPU transcode (software 4K/HDR/PGS burn-in is not a supported path)

**Client-compatible release** — A file the playback target can Direct Play: 4K (or 1080p fallback) HEVC HDR10/HDR10+, audio AAC or Dolby Digital / DD+ (including DD+ Atmos), text SRT sidecars. TrueHD, DTS-HD, and Dolby Vision are not client-compatible here.

**Watch-history sync** — Copying Plex playback that reached Tautulli’s watched threshold onto SIMKL. Independent of Direct Play.

**Sidecar SRT** — A `.srt` file next to the video that Plex on Xbox overlays without burn-in. PGS, VobSub, and ASS are not sidecar SRT; they force a transcode on this playback target.
