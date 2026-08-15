#!/usr/bin/env python3
"""Exit 1 if Plex library media files are missing or unreadable."""
import os
import sqlite3
import sys

DB = (
    "/mnt/samsung-media/Isyrr/configs/plex/Library/Application Support/"
    "Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
)


def host_path(f: str) -> str | None:
    if f.startswith("/data/movies"):
        return "/mnt/combined-media/Isyrr/radarr/movies" + f[len("/data/movies") :]
    if f.startswith("/data/tvshows"):
        return "/mnt/combined-media/Isyrr/sonarr/tv" + f[len("/data/tvshows") :]
    return None


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        """
        SELECT mp.file, md.title, md.year, ls.name
        FROM media_parts mp
        JOIN media_items mi ON mi.id = mp.media_item_id
        JOIN metadata_items md ON md.id = mi.metadata_item_id
        LEFT JOIN library_sections ls ON ls.id = md.library_section_id
        WHERE mp.file LIKE '/data/%'
        """
    ).fetchall()

    bad = []
    for f, title, year, section in rows:
        hp = host_path(f)
        if not hp:
            continue
        if not os.path.isfile(hp):
            alt = hp.replace("/mnt/combined-media", "/mnt/samsung-media", 1)
            if os.path.isfile(alt):
                hp = alt
            else:
                bad.append(("MISSING", section, title, year, f))
                continue
        try:
            with open(hp, "rb") as fh:
                fh.read(1024 * 1024)
        except OSError as e:
            bad.append(("UNREADABLE", section, title, year, f"{f} ({e})"))

    print(f"CHECKED={len(rows)} BAD={len(bad)}")
    for row in bad:
        print("\t".join(map(str, row)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
