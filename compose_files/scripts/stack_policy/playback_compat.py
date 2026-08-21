"""Direct Play policy for the playback target (Xbox Series X → Samsung U8000F).

Plex-on-Xbox MKV Direct Play audio is AAC/AC3/E-AC3 (and a few lossless
PCM-family codecs). The 65U8092 HDMI path decodes DD+ / DD+ Atmos and does
not decode TrueHD or DTS-HD. Hard-reject those so *arr never prefers a
remux that forces Xbox Direct Stream / transcode.
"""

from __future__ import annotations

import re

HARD_REJECT = -10000
PREFERRED = 100
# Untagged 4K WEB often scores ~0; only -10000 rejects must miss the cutoff.
MIN_FORMAT_SCORE = -9999

# TRaSH Guides trash_ids (Radarr vs Sonarr catalogs differ).
_RADARR = {
    "TrueHD ATMOS": "496f355514737f7d83bf7aa4d24f8169",
    "TrueHD": "3cafb66171b47f226146a0770576870f",
    "DTS X": "2f22d89048b01681dde8afe203bf2e95",
    "DTS-HD MA": "dcf3ec6938fa32445f590a4da84256cd",
    "DTS-HD HRA": "8e109e50e0a0b83a5098b056e13bf6db",
    "DTS": "1c1a4c5e823891c75bc50380a6866f73",
    "DD+ ATMOS": "1af239278386be2919e1bcee0bde047e",
    "DD+": "185f1dd7264c4562b9022d963ac37424",
    "AAC": "240770601cc226190c367ef59aba7463",
}
_SONARR = {
    "TrueHD ATMOS": "0d7824bb924701997f874e7ff7d4844a",
    "TrueHD": "1808e4b9cee74e064dfae3f1db99dbfe",
    "DTS X": "9d00418ba386a083fbf4d58235fc37ef",
    "DTS-HD MA": "c429417a57ea8c41d57e6990a8b0033f",
    "DTS-HD HRA": "cfa5fbd8f02a86fc55d8d223d06a5e1f",
    "DTS": "5964f2a8b3be407d083498e4459d05d0",
    "DD+ ATMOS": "4232a509ce60c4e208d13825b7c06264",
    "DD+": "63487786a8b01b7f20dd2bc90dd4a477",
    "AAC": "a50b8a0c62274a7c38b09a9619ba9d86",
}

_REJECT_NAMES = ("TrueHD ATMOS", "TrueHD", "DTS X", "DTS-HD MA", "DTS-HD HRA", "DTS")
_PREFER_NAMES = ("DD+ ATMOS", "DD+", "AAC")


def _catalog(app: str) -> dict[str, str]:
    if app == "radarr":
        return _RADARR
    if app == "sonarr":
        return _SONARR
    raise ValueError(f"unknown app: {app}")


def score_for(app: str, trash_id: str) -> int:
    catalog = _catalog(app)
    name = next((n for n, tid in catalog.items() if tid == trash_id), None)
    if name is None:
        raise KeyError(trash_id)
    if name in _REJECT_NAMES:
        return HARD_REJECT
    if name in _PREFER_NAMES:
        return PREFERRED
    raise KeyError(trash_id)


def assigned_score(yml: str, trash_id: str) -> int:
    idx = yml.index(trash_id)
    match = re.search(r"score:\s*(-?\d+)", yml[idx : idx + 1200])
    if match is None:
        raise ValueError(f"no score after {trash_id}")
    return int(match.group(1))
