# TV library

TV library shows the series Sonarr tracks and the matching Plex show section.

## Sub-features

- `sonarr-count` reports how many series Sonarr has and up to five titles.
- `plex-shows` lists Plex sections so the show paths can be checked against that count.

## How to get to it (user POV)

- Open Sonarr at `http://127.0.0.1:8989` and look at Series.
- Open Plex at `http://127.0.0.1:32400` and open the TV library.

## Driving it with verify-media-server

Preconditions:

- `doctor` prints `DOCTOR_OK`.
- Sonarr `config.xml` contains an API key under `APPDATA_PATH`.

- **Sonarr list.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive tv-library`. Exit code `0`. `proof/tv-library/stdout.txt` contains `count=` and, when the count is greater than 0, at least one `title=` line.
- **Plex section.** The same command writes `proof/tv-library/state.txt`. It contains a `section=` line whose `type=show` and a `paths=` value under the media library.

## Gotchas

- The proof stores five titles at most. The count is the full Sonarr list.
- An empty library is `count=0` and no `title=` lines. That still needs a Plex `type=show` section in `state.txt` when the library is configured.
- Searching missing episodes is outside this drive.
