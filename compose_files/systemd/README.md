# Boot persistence (media-server.service)

This unit keeps the hardlink-safe stack up across reboot/shutdown:

1. Waits for mergerfs + SSD/HDD mounts (`RequiresMountsFor`).
2. Runs `docker compose -f docker-compose.yaml up -d` from this repo (script + branch mounts).
3. Runs `scripts/boot-ensure-hardlink-policy.sh` → `homelab-setup.sh --mode=boot` (no queue wipes, Recyclarr, or qBittorrent restart):
   - `copyUsingHardlinks`
   - `removeCompletedDownloads=false`
   - root folders + remote path mappings
   - Custom Script Connect (`same-disk-import.sh`)
   - search monitored missing TV/movies from the last 14 days (RSS catch-up after downtime)
4. On stop/shutdown: `docker compose stop` (not `down`), so container definitions stay.

## Install / refresh

From the repo, after `compose_files/.env` exists:

```bash
sudo bash compose_files/systemd/install-media-server-unit.sh
sudo systemctl enable --now media-server.service
```

That renders [`media-server.service.in`](media-server.service.in) with this clone’s path and the mergerfs/branch parents from `.env`. As root it also renders and enables `media-backup.timer` (04:30 nightly restic snapshot) and `media-monitor.timer` (ntfy alert every 5 minutes on a new problem: container down or unhealthy, disk ≥90% or unmounted, backup older than 36h). State lives in `/var/lib/media-server`. Do not copy a unit that still points at another machine’s home directory.

## Host fstab (this machine’s layout; override via `.env`)

- Branches: `/mnt/samsung-media`, `/mnt/4tb-media-2`
- Pool: mergerfs → `/mnt/combined-media` with `category.create=epmfs,minfreespace=40G`
- **Appdata** — `APPDATA_PATH` on the SSD branch (`/mnt/samsung-media/Isyrr/appdata`), bind-mounted directly (not via mergerfs). SQLite on the pool corrupts.
- **Do not** bind-mount downloads onto the SSD only (that line must stay commented).

## HDD spindown (this desktop)

Install [`69-media-hdd-spindown.rules`](69-media-hdd-spindown.rules) so the 4TB media disk parks after 15 minutes idle:

```bash
sudo cp compose_files/systemd/69-media-hdd-spindown.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=block --action=change
```

Serial is this host’s `TOSHIBA_HDWE140_9099K4XPFBRG` (`/dev/sdb`). Do not apply it to the other Toshiba if that disk has no filesystem.
