# Download client

Download client shows that the qBittorrent WebUI is the page a user opens in the browser.

## Sub-features

- `webui-open` returns the qBittorrent WebUI document on port 8080.

## How to get to it (user POV)

- Open `http://127.0.0.1:8080/` and read the page title `qBittorrent WebUI`.

## Driving it with verify-media-server

Preconditions:

- `doctor` prints `DOCTOR_OK`.

- **Open WebUI.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive download-client`. Exit code `0`. `proof/download-client/stdout.txt` contains `http=200 title=qBittorrent WebUI`. `state.txt` contains `title=qBittorrent WebUI`.

## Gotchas

- The login form is the observable page. Submitting a password or changing share limits is outside this drive.
- A 200 response whose HTML lacks `qBittorrent WebUI` fails the drive.
