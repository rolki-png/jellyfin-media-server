"""CLI for bash callers. Stdin/stdout JSON or files. No third-party deps."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from stack_policy.arr import (
    custom_script_id,
    custom_script_payload,
    editor_payload,
    ids_needing_profile,
    patch_download_client,
    patch_media_management,
    quality_profile_id,
)
from stack_policy.bazarr import apply_direct_play_config
from stack_policy.layout import check_compose_doc
from stack_policy.plex_prefs import apply_host_prefs
from stack_policy.profiles import RADARR_QUALITY_PROFILE, SONARR_QUALITY_PROFILE


def _load_json() -> object:
    return json.load(sys.stdin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stack_policy")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compose = sub.add_parser("check-compose")
    p_compose.add_argument("path")

    sub.add_parser("patch-media-mgmt")
    sub.add_parser("patch-download-client")

    p_prof = sub.add_parser("profile-name")
    p_prof.add_argument("app", choices=("radarr", "sonarr"))

    p_pid = sub.add_parser("profile-id")
    p_pid.add_argument("name")

    p_ids = sub.add_parser("ids-needing-profile")
    p_ids.add_argument("id_key")
    p_ids.add_argument("profile_id", type=int)

    p_edit = sub.add_parser("editor-payload")
    p_edit.add_argument("kind", choices=("movie", "series"))
    p_edit.add_argument("profile_id", type=int)

    p_script = sub.add_parser("custom-script-id")
    p_script.add_argument("path")

    p_payload = sub.add_parser("custom-script-payload")
    p_payload.add_argument("app")
    p_payload.add_argument("path")

    p_plex = sub.add_parser("apply-plex-prefs")
    p_plex.add_argument("prefs_path")
    p_plex.add_argument("--advertise", default="")

    p_bazarr = sub.add_parser("apply-bazarr-config")
    p_bazarr.add_argument("config_path")
    p_bazarr.add_argument("--sonarr-key", required=True)
    p_bazarr.add_argument("--radarr-key", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "check-compose":
        raw = Path(args.path).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            try:
                import yaml  # type: ignore

                data = yaml.safe_load(raw)
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: cannot parse compose config: {exc}", file=sys.stderr)
                return 1
        errors = check_compose_doc(data)
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1 if errors else 0

    if args.cmd == "patch-media-mgmt":
        print(json.dumps(patch_media_management(_load_json())))  # type: ignore[arg-type]
        return 0

    if args.cmd == "patch-download-client":
        rows = _load_json()
        client = rows[0] if isinstance(rows, list) else rows
        print(json.dumps(patch_download_client(client)))  # type: ignore[arg-type]
        return 0

    if args.cmd == "profile-name":
        print(RADARR_QUALITY_PROFILE if args.app == "radarr" else SONARR_QUALITY_PROFILE)
        return 0

    if args.cmd == "profile-id":
        pid = quality_profile_id(_load_json(), args.name)  # type: ignore[arg-type]
        if pid is None:
            return 1
        print(pid)
        return 0

    if args.cmd == "ids-needing-profile":
        ids = ids_needing_profile(_load_json(), args.id_key, args.profile_id)  # type: ignore[arg-type]
        print(json.dumps(ids))
        return 0

    if args.cmd == "editor-payload":
        ids = ids_needing_profile(_load_json(), "id", args.profile_id)  # type: ignore[arg-type]
        print(json.dumps(editor_payload(args.kind, ids, args.profile_id)))
        return 0

    if args.cmd == "custom-script-id":
        found = custom_script_id(_load_json(), args.path)  # type: ignore[arg-type]
        if found is not None:
            print(found)
        return 0

    if args.cmd == "custom-script-payload":
        print(json.dumps(custom_script_payload(args.app, args.path)))
        return 0

    if args.cmd == "apply-plex-prefs":
        path = Path(args.prefs_path)
        xml = path.read_text(encoding="utf-8")
        updated = apply_host_prefs(xml, advertise_url=args.advertise)
        if updated != xml:
            path.write_text(updated, encoding="utf-8")
        return 0

    if args.cmd == "apply-bazarr-config":
        path = Path(args.config_path)
        if not path.is_file():
            print(f"ERROR: missing {path}", file=sys.stderr)
            return 1
        original = path.read_text(encoding="utf-8")
        updated = apply_direct_play_config(
            original, sonarr_apikey=args.sonarr_key, radarr_apikey=args.radarr_key
        )
        if updated != original:
            path.write_text(updated, encoding="utf-8")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
