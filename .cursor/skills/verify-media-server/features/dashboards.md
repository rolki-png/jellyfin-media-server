# Dashboards

Dashboards shows that Panelarr, Homarr, and Seerr each serve their web app on the host ports.

## Sub-features

- `panelarr-open` serves the Panelarr document on port 8000.
- `homarr-open` serves the Homarr shell on port 7575.
- `seerr-open` serves the Seerr shell on port 5055.

## How to get to it (user POV)

- Open Panelarr at `http://127.0.0.1:8000/`. The document title is `Panelarr`.
- Open Homarr at `http://127.0.0.1:7575/`.
- Open Seerr at `http://127.0.0.1:5055/`.

## Driving it with verify-media-server

Preconditions:

- `doctor` prints `DOCTOR_OK`.
- Containers `panelarr`, `homarr`, and `seerr` are running.

- **Open all three.** Run `bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive dashboards`. Exit code `0`. `proof/dashboards/stdout.txt` contains `panelarr_http=200`, `homarr_http=200`, and `seerr_http=200`. `state.txt` contains `panelarr_title=Panelarr`, `homarr_shell=mantine`, and `seerr_shell=next`.

## Gotchas

- Homarr and Seerr set their visible titles in the browser after JavaScript runs. The drive checks the server HTML shell (`data-mantine-color-scheme`, `data-next-head`), which is what curl can see.
- First-run setup wizards can still be the page behind those shells. HTTP 200 plus the shell marker is the proof this drive owns.
- Signing in or creating the admin user is outside this drive.
