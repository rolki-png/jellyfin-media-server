# freeloader-plex

Builds `freeloader-plex:lsio`: linuxserver/plex plus Freeloader’s LD_PRELOAD
feature-unlock `.so`.

Upstream [authrequest/Freeloader](https://github.com/authrequest/Freeloader) is
pinned in `Dockerfile` as `FREELOADER_COMMIT` and vendored under `vendor/`
(GitHub returns HTTP 451, so the image build does not `git clone`).

## Local patch (Marker / Skip Intro)

Vendored `vendor/src/hook.cpp` adds a hook for PMS 1.43.2’s **per-user**
feature-bit lookup. The global FeatureManager bitset alone is not enough:
intro/credits `Marker` emission still checks that per-user map. Without the
extra hook, `/library/metadata/…?includeMarkers=1` returns no `Marker` nodes
even when tags exist in the library DB and the bitset is all `0xFF`.

## Rebuild

```bash
bash compose_files/scripts/build-freeloader-plex.sh
cd compose_files && docker compose --env-file .env up -d plex
```

Leave `PLEX_TRAFFIC_LOG` unset on the always-on server.
