"""Parse KEY=VAL dotenv lines without shell `source` (keeps `&` in values)."""

from __future__ import annotations


def parse_env_text(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        out[key] = value
    return out


def load_env_file(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as fh:
        return parse_env_text(fh.read())
