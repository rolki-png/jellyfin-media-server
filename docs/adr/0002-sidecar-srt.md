# Sidecar SRT instead of image subtitles

Xbox Plex cannot overlay PGS/VobSub and burns them into 4K HEVC, which hitchs on this host. Bazarr is wired to Sonarr/Radarr, ignores embedded PGS/VobSub/ASS, and fetches text SRT sidecars so subtitle playback stays Direct Play.
