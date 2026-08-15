# Boot persistence (media-server.service)

This unit keeps the hardlink-safe stack up across reboot/shutdown:

1. Waits for mergerfs + SSD/HDD mounts (`RequiresMountsFor`).
2. Runs `docker compose -f docker-compose.yaml up -d` from this repo (script + branch mounts).
3. Runs `scripts/boot-ensure-hardlink-policy.sh` → `homelab-setup.sh --mode=boot` (no queue wipes, Recyclarr, or qBittorrent restart):
   - `copyUsingHardlinks`
   - `removeCompletedDownloads=false`
   - root folders + remote path mappings
   - Custom Script Connect (`same-disk-import.sh`)
4. On stop/shutdown: `docker compose stop` (not `down`), so container definitions stay.

## Install / refresh

```bash
sudo cp compose_files/systemd/media-server.service /etc/systemd/system/media-server.service
sudo systemctl daemon-reload
sudo systemctl enable --now media-server.service
```

## Host fstab (already on this machine)

- Branches: `/mnt/samsung-media`, `/mnt/4tb-media-2`
- Pool: mergerfs → `/mnt/combined-media` with `category.create=epmfs,minfreespace=40G`
- **Do not** bind-mount downloads onto the SSD only (that line must stay commented).
