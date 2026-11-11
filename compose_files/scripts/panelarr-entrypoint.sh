#!/bin/sh
# Wrap upstream entrypoint with temporary local patches:
# - qBittorrent 5.x login returns HTTP 204 + SID cookie, not body "Ok."
# - Docker file bind-mounts (e.g. this script) appear in psutil partitions; skip
#   non-directory mountpoints so Disk Usage does not list them.
# - Downloads card: count full *arr queue (not only state=downloading)
set -e

python3 <<'PY'
from pathlib import Path

CONFIG = Path("/app/backend/services/config.py")
ARR = Path("/app/backend/services/arr.py")
SYSTEM = Path("/app/backend/routers/system.py")
DOWNLOADS = Path("/app/backend/routers/downloads.py")
DASH_ASSETS = Path("/app/frontend/dist/assets")

OLD_TEST = '''    if resp.text == "Ok.":
        return {"ok": True, "message": "Connected"}
    return {"ok": False, "message": "Authentication failed"}'''

NEW_TEST = '''    text = (resp.text or "").strip()
    if text in ("Ok.", "Ok") or (resp.status_code in (200, 204) and bool(resp.cookies)):
        return {"ok": True, "message": "Connected"}
    return {"ok": False, "message": "Authentication failed"}'''

OLD_ARR = 'if login_resp.text != "Ok.":'
NEW_ARR = (
    'if (login_resp.text or "").strip() not in ("Ok.", "Ok") '
    "and not (login_resp.status_code in (200, 204) and login_resp.cookies):"
)

OLD_DISK = '''        if mp in _SKIP_MOUNTS:
            continue
        if any(mp.startswith(p) for p in _SKIP_PREFIXES):
            continue
        _try_add(mp)'''

NEW_DISK = '''        if mp in _SKIP_MOUNTS:
            continue
        if any(mp.startswith(p) for p in _SKIP_PREFIXES):
            continue
        # File bind-mounts (Docker "mount a file") are partitions but not disks.
        if not Path(mp).is_dir():
            continue
        _try_add(mp)'''

cfg = CONFIG.read_text()
if OLD_TEST in cfg:
    CONFIG.write_text(cfg.replace(OLD_TEST, NEW_TEST, 1))
    print("panelarr: patched qBittorrent test for qBit 5 login response")
elif NEW_TEST in cfg:
    print("panelarr: qBittorrent test already patched")
else:
    print("panelarr: WARNING — qBittorrent test pattern not found; upstream may have changed")

arr = ARR.read_text()
if OLD_ARR in arr:
    ARR.write_text(arr.replace(OLD_ARR, NEW_ARR))
    print("panelarr: patched qBittorrent client auth checks for qBit 5")
elif NEW_ARR in arr:
    print("panelarr: qBittorrent client auth already patched")
else:
    print("panelarr: WARNING — qBittorrent client auth pattern not found")

sys_txt = SYSTEM.read_text()
if "Path(mp).is_dir()" in sys_txt:
    print("panelarr: disk collector already skips non-directory mounts")
elif OLD_DISK in sys_txt:
    if "from pathlib import Path" not in sys_txt:
        sys_txt = sys_txt.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\nfrom pathlib import Path\n",
            1,
        )
    SYSTEM.write_text(sys_txt.replace(OLD_DISK, NEW_DISK, 1))
    print("panelarr: patched disk collector to skip file bind-mounts")
else:
    print("panelarr: WARNING — disk collector pattern not found; upstream may have changed")

# Dashboard "0T / 0N Idle" only counted trackedDownloadState==downloading.
# Stuck importBlocked / warning queue items (common here) were ignored.
OLD_STATS = '''    torrent_active = sum(
        1
        for r in all_records
        if r.get("protocol") == "torrent" and r.get("trackedDownloadState") == "downloading"
    )
    nzb_active = sum(
        1
        for r in all_records
        if r.get("protocol") == "usenet" and r.get("trackedDownloadState") == "downloading"
    )'''

NEW_STATS = '''    torrent_active = sum(1 for r in all_records if r.get("protocol") == "torrent")
    nzb_active = sum(1 for r in all_records if r.get("protocol") == "usenet")
    # Prefer live client downloading count when *arr queue is empty of torrents.
    if isinstance(qbit, dict) and qbit.get("configured"):
        torrent_active = max(torrent_active, int(qbit.get("downloading") or 0))'''

dl_txt = DOWNLOADS.read_text()
if "Prefer live client downloading count" in dl_txt:
    print("panelarr: download stats already count full *arr queue")
elif OLD_STATS in dl_txt:
    DOWNLOADS.write_text(dl_txt.replace(OLD_STATS, NEW_STATS, 1))
    print("panelarr: patched download stats to count all queue torrents/NZBs")
else:
    print("panelarr: WARNING — download stats pattern not found; upstream may have changed")

# Frontend: treat importBlocked/warning as non-idle on the Downloads card.
OLD_IDLE = 'q=(d==null?void 0:d.filter(s=>s.status==="downloading"))??[]'
NEW_IDLE = (
    'q=(d==null?void 0:d.filter(s=>s.status==="downloading"'
    '||s.status==="importBlocked"||s.warning))??[]'
)
patched_dash = False
for asset in DASH_ASSETS.glob("dashboard-*.js"):
    js = asset.read_text()
    if NEW_IDLE in js:
        print(f"panelarr: {asset.name} idle filter already patched")
        patched_dash = True
    elif OLD_IDLE in js:
        asset.write_text(js.replace(OLD_IDLE, NEW_IDLE, 1))
        print(f"panelarr: patched {asset.name} idle filter for importBlocked/warnings")
        patched_dash = True
if not patched_dash:
    print("panelarr: WARNING — dashboard idle filter pattern not found")

# Drop stale bytecode so uvicorn loads the patched sources.
for cache_dir in (
    CONFIG.parent / "__pycache__",
    ARR.parent / "__pycache__",
    SYSTEM.parent / "__pycache__",
    DOWNLOADS.parent / "__pycache__",
):
    if cache_dir.is_dir():
        for pyc in cache_dir.glob("*.pyc"):
            pyc.unlink(missing_ok=True)
PY

exec /entrypoint.sh
