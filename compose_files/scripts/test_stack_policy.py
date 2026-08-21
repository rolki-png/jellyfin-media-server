#!/usr/bin/env python3
"""Tests at the stack_policy interface (stdlib unittest)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from stack_policy.arr import (
    custom_script_payload,
    first_download_client_id,
    has_plex_server_notification,
    has_remote_path_mapping,
    has_root_folder,
    ids_needing_profile,
    patch_download_client,
    patch_media_management,
    plex_server_payload,
    quality_profile_id,
    stuck_queue_ids,
)
from stack_policy.bazarr import (
    apikey_from_config,
    apply_direct_play_config,
    apply_english_library,
    english_language_profile,
    titles_needing_english,
)
from stack_policy.playback_compat import (
    HARD_REJECT,
    MIN_FORMAT_SCORE,
    PREFERRED,
    assigned_score,
    score_for,
    score_map,
)
from stack_policy.tautulli import (
    SIMKL_WATCHED_JSON,
    WEBHOOK_AGENT_ID,
    apply_pms_ini,
    ensure_simkl_webhook,
    find_simkl_notifier_id,
    plex_connection_from_prefs,
    tautulli_api_key,
    webhook_notifier_fields,
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


class PlaybackCompatTests(unittest.TestCase):
    """Xbox Series X MKV Direct Play + Samsung U8000F HDMI decode."""

    def test_truehd_and_dts_are_hard_rejects(self) -> None:
        self.assertEqual(score_for("radarr", "496f355514737f7d83bf7aa4d24f8169"), HARD_REJECT)
        self.assertEqual(score_for("radarr", "dcf3ec6938fa32445f590a4da84256cd"), HARD_REJECT)
        self.assertEqual(score_for("sonarr", "0d7824bb924701997f874e7ff7d4844a"), HARD_REJECT)
        self.assertEqual(score_for("sonarr", "c429417a57ea8c41d57e6990a8b0033f"), HARD_REJECT)

    def test_ddplus_and_aac_are_preferred(self) -> None:
        self.assertEqual(score_for("radarr", "185f1dd7264c4562b9022d963ac37424"), PREFERRED)
        self.assertEqual(score_for("radarr", "240770601cc226190c367ef59aba7463"), PREFERRED)
        self.assertEqual(score_for("sonarr", "63487786a8b01b7f20dd2bc90dd4a477"), PREFERRED)

    def test_min_format_score_blocks_only_hard_rejects(self) -> None:
        self.assertEqual(MIN_FORMAT_SCORE, -9999)
        self.assertGreater(MIN_FORMAT_SCORE, HARD_REJECT)

    def test_recyclarr_yaml_applies_every_scored_id(self) -> None:
        yml = (Path(__file__).resolve().parents[1] / "recyclarr" / "recyclarr.yml").read_text(
            encoding="utf-8"
        )
        for app in ("radarr", "sonarr"):
            for tid, score in score_map(app).items():
                self.assertEqual(assigned_score(yml, tid), score, msg=tid)
        self.assertIn(f"min_format_score: {MIN_FORMAT_SCORE}", yml)


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


BAZARR_SAMPLE = """
general:
  use_sonarr: false
  use_radarr: false
  use_embedded_subs: true
  ignore_pgs_subs: false
  ignore_vobsub_subs: false
  ignore_ass_subs: false
  enabled_providers: []
  single_language: false
sonarr:
  ip: 127.0.0.1
  port: 8989
  apikey: old-sonarr
radarr:
  ip: 127.0.0.1
  port: 7878
  apikey: old-radarr
"""


class BazarrCompatTests(unittest.TestCase):
    def test_ignores_image_subs_and_wires_arr(self) -> None:
        out = apply_direct_play_config(
            BAZARR_SAMPLE, sonarr_apikey="sonarr-key", radarr_apikey="radarr-key"
        )
        self.assertRegex(out, r"ignore_pgs_subs:\s*true")
        self.assertRegex(out, r"ignore_vobsub_subs:\s*true")
        self.assertRegex(out, r"ignore_ass_subs:\s*true")
        self.assertRegex(out, r"use_sonarr:\s*true")
        self.assertRegex(out, r"use_radarr:\s*true")
        self.assertIn("sonarr-key", out)
        self.assertIn("radarr-key", out)
        self.assertIn("gestdown", out)
        self.assertRegex(out, r"ip:\s*sonarr")
        self.assertRegex(out, r"ip:\s*radarr")

    def test_rewrites_multiline_providers(self) -> None:
        src = BAZARR_SAMPLE.replace(
            "enabled_providers: []",
            "enabled_providers:\n  - opensubtitlescom\n  - addic7ed",
        )
        out = apply_direct_play_config(
            src, sonarr_apikey="s", radarr_apikey="r"
        )
        self.assertIn("- gestdown", out)
        self.assertNotIn("opensubtitlescom", out)
        self.assertNotIn("addic7ed", out)

    def test_english_profile_is_en_only(self) -> None:
        profile = english_language_profile()
        self.assertEqual(profile["profileId"], 1)
        self.assertEqual(profile["name"], "English")
        self.assertEqual(profile["items"][0]["language"], "en")

    def test_apikey_and_titles_needing_english(self) -> None:
        self.assertEqual(apikey_from_config("auth:\n  apikey: abc\n"), "abc")
        rows = {"data": [{"profileId": 1, "sonarrSeriesId": 9}, {"profileId": 2, "sonarrSeriesId": 8}]}
        self.assertEqual(titles_needing_english(rows, "sonarrSeriesId"), [8])

    def test_apply_english_library_posts_missing_only(self) -> None:
        posted: list[str] = []

        def get(path: str) -> dict:
            if path == "/series":
                return {"data": [{"profileId": 2, "sonarrSeriesId": 11}]}
            return {"data": [{"profileId": 1, "radarrId": 3}]}

        apply_english_library(get, posted.append)
        self.assertEqual(posted, ["/series?seriesid=11&profileid=1"])


class TautulliSimklTests(unittest.TestCase):
    def test_prefs_extract_token_and_machine(self) -> None:
        xml = (
            '<Preferences PlexOnlineToken="tok-1" MachineIdentifier="abc-uuid" '
            'FriendlyName="Isyrr"/>'
        )
        conn = plex_connection_from_prefs(xml)
        self.assertEqual(conn["token"], "tok-1")
        self.assertEqual(conn["identifier"], "abc-uuid")
        self.assertEqual(conn["name"], "Isyrr")

    def test_pms_ini_points_at_compose_plex(self) -> None:
        ini = "[General]\napi_key = secret-key\n\n[PMS]\npms_ip = 127.0.0.1\n"
        out = apply_pms_ini(
            ini, token="tok-1", identifier="abc-uuid", name="Isyrr", host="plex"
        )
        self.assertIn("plex", out)
        self.assertIn("tok-1", out)
        self.assertIn("abc-uuid", out)
        self.assertRegex(out, r"first_run_complete\s*=\s*1")
        self.assertEqual(tautulli_api_key(out), "secret-key")

    def test_webhook_fields_only_watched(self) -> None:
        fields = webhook_notifier_fields("https://api.simkl.com/plex?user_token=x")
        self.assertEqual(fields["agent_id"], str(WEBHOOK_AGENT_ID))
        self.assertEqual(fields["webhook_method"], "POST")
        self.assertEqual(fields["on_watched"], "1")
        self.assertEqual(fields["on_play"], "0")
        self.assertEqual(fields["on_watched_body"], SIMKL_WATCHED_JSON)
        self.assertIn("{themoviedb_id}", fields["on_watched_body"])
        self.assertIn("media.scrobble", fields["on_watched_body"])

    def test_find_simkl_notifier(self) -> None:
        rows = [
            {"id": 1, "agent_id": 13, "friendly_name": "Telegram"},
            {"id": 4, "agent_id": 25, "agent_name": "webhook", "friendly_name": "SIMKL"},
        ]
        self.assertEqual(find_simkl_notifier_id(rows), 4)
        self.assertIsNone(find_simkl_notifier_id([]))

    def test_ensure_simkl_webhook_creates_then_skips(self) -> None:
        store: dict = {"notifiers": [], "hook": ""}

        def call(cmd: str, extra=None):
            extra = extra or {}
            if cmd == "get_notifiers":
                return store["notifiers"]
            if cmd == "add_notifier_config":
                store["notifiers"] = [
                    {"id": 7, "agent_id": WEBHOOK_AGENT_ID, "agent_name": "webhook", "friendly_name": ""}
                ]
                return {}
            if cmd == "get_notifier_config":
                return {"config": {"hook": store["hook"]}}
            if cmd == "set_notifier_config":
                store["hook"] = extra.get("webhook_hook", "")
                store["notifiers"][0]["friendly_name"] = "SIMKL"
                return {}
            raise AssertionError(cmd)

        self.assertEqual(ensure_simkl_webhook(call, "https://api.simkl.com/x?t=1"), "updated")
        self.assertEqual(ensure_simkl_webhook(call, "https://api.simkl.com/x?t=1"), "ok")


class ArrPolicyTests(unittest.TestCase):
    def test_root_remote_queue_plex(self) -> None:
        self.assertTrue(has_root_folder([{"path": "/data/movies/"}], "/data/movies"))
        self.assertTrue(
            has_remote_path_mapping(
                [{"host": "qbittorrent", "remotePath": "/downloads/", "localPath": "/pool/dl/"}],
                host="qbittorrent",
                remote="/downloads",
                local="/pool/dl",
            )
        )
        self.assertEqual(
            stuck_queue_ids({"records": [{"id": 1, "status": "completed"}, {"id": 2, "status": "downloading"}]}),
            [1],
        )
        self.assertTrue(has_plex_server_notification([{"implementation": "PlexServer"}]))
        self.assertFalse(has_plex_server_notification([]))
        self.assertEqual(first_download_client_id([{"id": 4}]), 4)
        body = plex_server_payload(host="plex", token="tok")
        self.assertEqual(body["implementation"], "PlexServer")


if __name__ == "__main__":
    unittest.main()
