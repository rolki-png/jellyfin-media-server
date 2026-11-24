---
name: verify-media-server
description: "Prove the live Plex media stack from this repo: stack health, movie library, TV library, qBittorrent WebUI, Panelarr/Homarr/Seerr dashboards, and compose layout. Use when a compose, stack_policy, or homelab change needs a read-only check against the running server."
---

# Verify the media server

This host runs one media stack. Ports, `APPDATA_PATH`, and the mergerfs library are shared. Attach to the containers already running. A second `docker compose` project on the same ports and appdata would fight that instance.

The harness is `verify-media-server.sh`. Feature recipes live in [features/README.md](features/README.md).

## Launch

From the repo root:

```bash
bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh doctor
```

Done when stdout contains `DOCTOR_OK` and `started_by_verify=no`.

When doctor reports containers not running, start the existing project and run doctor again:

```bash
cd compose_files && docker compose --env-file .env up -d
```

Ready means `plex`, `radarr`, `sonarr`, and `qbittorrent` are up, Plex `http://127.0.0.1:32400/identity` returns HTTP 200, Radarr `:7878/ping` and Sonarr `:8989/ping` return `"status": "OK"`, and qBittorrent `:8080/` returns HTTP 200. `APPDATA_PATH` is a real disk, not mergerfs.

Leave the stack up when this run did not start it. Teardown of scratch state is [Cleanup](#cleanup).

## Doctor

```bash
bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh doctor
```

Done when the exit code is 0 and stdout contains `DOCTOR_OK`, `appdata_fstype=`, and the four container ids. Run doctor again before a drive whenever those ids or the fstype look wrong.

## Drive

Pick a feature file from [features/README.md](features/README.md). Run that file's commands. One feature per claim.

```bash
bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh drive <feature>
```

`<feature>` is `stack-health`, `movie-library`, `tv-library`, `download-client`, `dashboards`, or `layout`.

Done when the command prints `PROOF <path> exit=0` and that directory contains `action.txt`, `stdout.txt`, `state.txt` or `stderr.txt`, and `exit_code.txt` whose contents are `0`.

## Evidence

Proof is written to `.cursor/skills/verify-media-server/proof/<feature>/`. That directory is gitignored. Cleanup leaves it in place.

Each drive records the command (`action.txt`), the command output (`stdout.txt`), a second read of the resulting state (`state.txt`), and the exit code.

Standards:

- Hit the live service or `validate.sh`. Skip queue searches, grabs, profile writes, and `homelab-setup.sh`.
- Record the command and the state it produced.
- Library proof is a count plus titles or Plex section paths, then the same sections from Plex as the second view.
- `validate.sh` is a dry layout check. `state.txt` records whether it exited 0. It does not publish ports or import files.
- Keep API keys and the Plex token out of proof files. The script sends them as headers and does not write them.

## Cleanup

```bash
bash .cursor/skills/verify-media-server/scripts/verify-media-server.sh cleanup
```

Done when stdout is `CLEANUP_OK`, `.run-stamp` is gone, `/tmp/verify-media-server-*` for that run is gone, `proof/` still holds the feature directory, and `docker inspect` still shows the container ids doctor printed.

Cleanup removes the scratch dir and the stamp. It does not stop containers.

## Helpers

`scripts/verify-media-server.sh` is the only helper. Invoke it with the `bash` lines above. `doctor` checks the singleton. `drive <feature>` writes proof. `cleanup` drops scratch and the stamp.
