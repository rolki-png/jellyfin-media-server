"""Parse KEY=VAL dotenv lines without shell `source` (keeps `&` in values)."""

from __future__ import annotations

import os
import re

_VAR_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _strip_unquoted_comment(value: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif (
            ch == "#"
            and not in_single
            and not in_double
            and (i == 0 or value[i - 1] in " \t")
        ):
            end = i
            while end > 0 and value[end - 1] in " \t":
                end -= 1
            return value[:end]
    return value


def _expand(value: str, lookup: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return lookup.get(name, os.environ.get(name, ""))

    cur = value
    for _ in range(8):
        nxt = _VAR_REF.sub(repl, cur)
        if nxt == cur:
            return cur
        cur = nxt
    return cur


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
        value = _strip_unquoted_comment(value.strip())
        quote: str | None = None
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            quote = value[0]
            value = value[1:-1]
        if quote != "'":
            value = _expand(value, out)
        out[key] = value
    return out


def load_env_file(path: str) -> dict[str, str]:
    with open(path, encoding="utf-8") as fh:
        return parse_env_text(fh.read())
