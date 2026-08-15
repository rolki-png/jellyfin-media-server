#!/usr/bin/env python3
"""Tests at the stack_policy interface (stdlib unittest)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from stack_policy.arr import (
    custom_script_payload,
    ids_needing_profile,
    patch_download_client,
    patch_media_management,
    quality_profile_id,
)
from stack_policy.layout import check_arr_volumes, check_compose_doc
from stack_policy.plex_prefs import apply_host_prefs, ensure_transcoder_temp
from stack_policy.profiles import RADARR_QUALITY_PROFILE, SONARR_QUALITY_PROFILE


class LayoutTests(unittest.TestCase):
    def test_split_binds_are_rejected(self) -> None:
        errors = check_arr_volumes(
            "radarr",
            ["/data/movies:/movies", "/data/dl:/downloads", "./scripts/same-disk-import.sh:/scripts/same-disk-import.sh"],
        )
        self.assertTrue(any("hardlinks" in e for e in errors))

    def test_common_path_plus_script_is_ok(self) -> None:
        errors = check_arr_volumes(
            "sonarr",
            [
                {"source": "/mnt/pool/Isyrr", "target": "/mnt/pool/Isyrr"},
                {"source": "./scripts/same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
            ],
        )
        self.assertEqual(errors, [])

    def test_missing_script_is_rejected(self) -> None:
        errors = check_arr_volumes("radarr", [{"source": "/data", "target": "/data"}])
        self.assertTrue(any("same-disk-import.sh" in e for e in errors))

    def test_compose_doc_checks_both_apps(self) -> None:
        errors = check_compose_doc({"services": {"radarr": {"volumes": []}, "sonarr": {"volumes": []}}})
        self.assertEqual(len(errors), 2)


class ArrPayloadTests(unittest.TestCase):
    def test_media_management_enables_hardlinks(self) -> None:
        out = patch_media_management({"copyUsingHardlinks": False, "id": 1})
        self.assertTrue(out["copyUsingHardlinks"])
        self.assertEqual(out["extraFileExtensions"], "srt")
        self.assertFalse(out["skipFreeSpaceCheckWhenImporting"])

    def test_download_client_keeps_completed_for_seed(self) -> None:
        out = patch_download_client({"removeCompletedDownloads": True, "id": 4})
        self.assertFalse(out["removeCompletedDownloads"])
        self.assertTrue(out["removeFailedDownloads"])

    def test_profile_id_and_bulk_ids(self) -> None:
        self.assertEqual(
            quality_profile_id([{"name": RADARR_QUALITY_PROFILE, "id": 8}], RADARR_QUALITY_PROFILE),
            8,
        )
        self.assertEqual(
            ids_needing_profile(
                [{"id": 1, "qualityProfileId": 8}, {"id": 2, "qualityProfileId": 3}],
                "id",
                8,
            ),
            [2],
        )

    def test_editor_payload_wraps_ids(self) -> None:
        from stack_policy.arr import editor_payload

        self.assertEqual(
            editor_payload("movie", [1, 2], 8),
            {"movieIds": [1, 2], "qualityProfileId": 8},
        )

    def test_sonarr_custom_script_includes_import_complete(self) -> None:
        sonarr = custom_script_payload("Sonarr", "/scripts/same-disk-import.sh")
        radarr = custom_script_payload("Radarr", "/scripts/same-disk-import.sh")
        self.assertTrue(sonarr.get("onImportComplete"))
        self.assertNotIn("onImportComplete", radarr)


class PlexPrefsTests(unittest.TestCase):
    def test_inserts_transcoder_when_missing(self) -> None:
        xml = '<Preferences Foo="1"/>'
        out = ensure_transcoder_temp(xml)
        self.assertIn('TranscoderTempDirectory="/transcode"', out)

    def test_replaces_existing_transcoder_and_advertise(self) -> None:
        xml = '<Preferences TranscoderTempDirectory="/config/Cache" customConnections="http://192.168.0.2:32400"/>'
        out = apply_host_prefs(xml, advertise_url="http://192.168.0.236:32400")
        self.assertIn('TranscoderTempDirectory="/transcode"', out)
        self.assertIn("192.168.0.236:32400", out)
        self.assertNotIn("192.168.0.2:32400", out)


class ProfileNameTests(unittest.TestCase):
    def test_names_match_recyclarr_titles(self) -> None:
        root = Path(__file__).resolve().parents[1]
        yml = (root / "recyclarr" / "recyclarr.yml").read_text(encoding="utf-8")
        self.assertIn(RADARR_QUALITY_PROFILE, yml)
        self.assertIn(SONARR_QUALITY_PROFILE, yml)


class MainCliTests(unittest.TestCase):
    def test_check_compose_json_file(self) -> None:
        from stack_policy.__main__ import main

        doc = {
            "services": {
                "radarr": {
                    "volumes": [
                        {"source": "/data", "target": "/data"},
                        {"source": "same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                    ]
                },
                "sonarr": {
                    "volumes": [
                        {"source": "/data", "target": "/data"},
                        {"source": "same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                    ]
                },
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
            path = fh.name
        self.assertEqual(main(["check-compose", path]), 0)


if __name__ == "__main__":
    unittest.main()
