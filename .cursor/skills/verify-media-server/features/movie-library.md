# Movie library

Movie library shows the movies Radarr tracks and the matching Plex movie section.

## Sub-features

- `radarr-count` reports how many movies Radarr has and up to five titles.
- `plex-movies` lists Plex sections so the movie paths can be checked against that count.

## How to get to it (user POV)

- Open Radarr at `http://127.0.0.1:7878` and look at Movies.
- Open Plex at `http://127.0.0.1:32400` and open the movie library.

## Driving it with verify-media-server

Preconditions:

- `doctor` prints `DOCTOR_OK`.
- Radarr `config.xml` contains an API key under `APPDATA_PATH`.

- **Radarr list.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive movie-library`. Exit code `0`. `proof/movie-library/stdout.txt` contains `count=` and, when the count is greater than 0, at least one `title=` line.
- **Plex section.** The same command writes `proof/movie-library/state.txt`. It contains a `section=` line whose `type=movie` and a `paths=` value under the media library.

## Gotchas

- The proof stores five titles at most. The count is the full Radarr list.
- An empty library is `count=0` and no `title=` lines. That still needs a Plex `type=movie` section in `state.txt` when the library is configured.
- Adding or searching movies is outside this drive.
