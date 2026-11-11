#!/usr/bin/env python3
"""Tests at the stack_policy interface (stdlib unittest)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from stack_policy.arr import (
    allow_named_qualities,
    with_any_language,
    custom_script_payload,
    first_download_client_id,
    has_plex_server_notification,
    has_remote_path_mapping,
    has_root_folder,
    ids_needing_profile,
    patch_download_client,
    patch_indexer,
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
    apply_media_tags,
    ensure_simkl_webhook,
    find_simkl_notifier_id,
    ids_from_plex_guids,
    plex_connection_from_prefs,
    replay_empty_watched_webhooks,
    scrobble_from_metadata,
    tautulli_api_key,
    webhook_notifier_fields,
)
from stack_policy.catchup import (
    episode_search_command,
    movies_search_command,
    recent_missing_episode_ids,
    recent_missing_movie_ids,
)
from stack_policy.layout import check_arr_volumes, check_compose_doc, check_plex_local_image
from stack_policy.qbittorrent import seed_unlimited_preferences
from stack_policy.monitor import (
    Container,
    backup_problems,
    container_problems,
    diff,
    disk_problems,
    restart_targets,
)
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

    def test_freeloader_plex_with_watchtower_on_is_rejected(self) -> None:
        errors = check_compose_doc(
            {
                "services": {
                    "plex": {
                        "image": "freeloader-plex:lsio",
                        "labels": {"com.centurylinklabs.watchtower.enable": "true"},
                    }
                }
            }
        )
        self.assertTrue(any("plex" in e and "watchtower" in e for e in errors))

    def test_freeloader_plex_with_watchtower_off_is_ok(self) -> None:
        errors = check_plex_local_image(
            "plex",
            {"image": "freeloader-plex:lsio", "labels": {"com.centurylinklabs.watchtower.enable": "false"}},
        )
        self.assertEqual(errors, [])

    def test_freeloader_vendor_hooks_modern_per_user_feature_bits(self) -> None:
        """Bitset-only Freeloader leaves Marker/Skip Intro gated on PMS 1.43.2.

        The vendored hook.cpp must also sig-scan the modern per-user feature
        lookup (and must not return early right after installing bitset_init).
        """
        vendor = Path(__file__).resolve().parents[1] / "freeloader" / "vendor"
        hook = (vendor / "src" / "hook.cpp").read_text(encoding="utf-8")
        version = (vendor / "VERSION").read_text(encoding="utf-8")
        self.assertIn("6efe3c8be82c0b4a3ac13ebd17a3fe101fc4927c", version)
        self.assertIn(
            "55 48 89 E5 48 8B 07 4C 8B 08 4C 8B 40 08 4C 89 C7 4C 29 CF 74 37",
            hook,
        )
        self.assertIn("Do NOT return here", hook)
        self.assertTrue((vendor / "third_party" / "zydis" / "Zydis.c.xz").is_file())

    def test_upstream_plex_image_may_use_watchtower(self) -> None:
        errors = check_plex_local_image(
            "plex",
            {"image": "lscr.io/linuxserver/plex:latest", "labels": {"com.centurylinklabs.watchtower.enable": "true"}},
        )
        self.assertEqual(errors, [])

    def test_config_on_media_pool_is_rejected(self) -> None:
        errors = check_compose_doc(
            {
                "services": {
                    "radarr": {
                        "volumes": [
                            {"source": "/mnt/pool/Isyrr", "target": "/mnt/pool/Isyrr"},
                            {"source": "/mnt/pool/Isyrr/configs/radarr", "target": "/config"},
                            {"source": "./scripts/same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                        ]
                    },
                    "sonarr": {
                        "volumes": [
                            {"source": "/mnt/pool/Isyrr", "target": "/mnt/pool/Isyrr"},
                            {"source": "/mnt/ssd/appdata/sonarr", "target": "/config"},
                            {"source": "./scripts/same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                        ]
                    },
                }
            }
        )
        self.assertTrue(any("radarr" in e and "media pool" in e for e in errors))
        self.assertFalse(any("sonarr" in e and "media pool" in e for e in errors))

    def test_appdata_on_ssd_identity_bind_is_ok(self) -> None:
        errors = check_compose_doc(
            {
                "services": {
                    "radarr": {
                        "volumes": [
                            {"source": "/mnt/pool/Isyrr", "target": "/mnt/pool/Isyrr"},
                            {"source": "/mnt/ssd/Isyrr", "target": "/mnt/ssd/Isyrr"},
                            {"source": "/mnt/ssd/Isyrr/appdata/radarr", "target": "/config"},
                            {"source": "./scripts/same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                        ]
                    },
                    "sonarr": {
                        "volumes": [
                            {"source": "/mnt/pool/Isyrr", "target": "/mnt/pool/Isyrr"},
                            {"source": "/mnt/ssd/Isyrr", "target": "/mnt/ssd/Isyrr"},
                            {"source": "/mnt/ssd/Isyrr/appdata/sonarr", "target": "/config"},
                            {"source": "./scripts/same-disk-import.sh", "target": "/scripts/same-disk-import.sh"},
                        ]
                    },
                }
            }
        )
        self.assertEqual(errors, [])


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

    def test_quality_profile_language_any_allows_hun_dual_audio(self) -> None:
        out = with_any_language({"id": 7, "name": "UHD Bluray + WEB", "language": {"id": -2, "name": "Original"}})
        self.assertEqual(out["language"], {"id": -1, "name": "Any"})

    def test_any_profile_can_allow_web_720p(self) -> None:
        out = allow_named_qualities(
            {
                "name": "Any",
                "items": [
                    {"name": "WEB 720p", "allowed": False, "items": []},
                    {"quality": {"name": "HDTV-720p"}, "allowed": False},
                    {"name": "WEB 1080p", "allowed": True, "items": []},
                ],
            },
            {"WEB 720p", "HDTV-720p"},
        )
        self.assertTrue(out["items"][0]["allowed"])
        self.assertTrue(out["items"][1]["allowed"])
        self.assertTrue(out["items"][2]["allowed"])

    def test_indexer_allows_zero_seeders_and_ncore_tv_cats(self) -> None:
        out = patch_indexer(
            {
                "id": 1,
                "fields": [
                    {"name": "minimumSeeders", "value": 1},
                    {"name": "categories", "value": [5040, 5045]},
                ],
            }
        )
        fields = {f["name"]: f["value"] for f in out["fields"]}
        self.assertEqual(fields["minimumSeeders"], 0)
        self.assertIn(5030, fields["categories"])
        self.assertIn(5040, fields["categories"])

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

    def test_lan_networks_set_and_replaced(self) -> None:
        xml = '<Preferences LanNetworksBandwidth="10.0.0.0/8" ManualPortMappingMode="1"/>'
        out = apply_host_prefs(xml, lan_networks="192.168.0.0/24,100.64.0.0/10")
        self.assertIn('LanNetworksBandwidth="192.168.0.0/24,100.64.0.0/10"', out)
        self.assertNotIn("10.0.0.0/8", out)
        self.assertIn('ManualPortMappingMode="1"', out)

    def test_lan_networks_left_alone_when_unset(self) -> None:
        xml = '<Preferences LanNetworksBandwidth="10.0.0.0/8"/>'
        self.assertIn("10.0.0.0/8", apply_host_prefs(xml))


def _inspect(name: str, status: str, health: str = "", exit_code: int = 0, restart: str = "unless-stopped") -> Container:
    row = {
        "Name": f"/{name}",
        "State": {"Status": status, "ExitCode": exit_code, **({"Health": {"Status": health}} if health else {})},
        "HostConfig": {"RestartPolicy": {"Name": restart}},
    }
    return Container.from_inspect(row)


class MonitorTests(unittest.TestCase):
    def test_init_container_exiting_cleanly_is_fine(self) -> None:
        ok = _inspect("plex-init", "exited", restart="no")
        bad = _inspect("plex-init", "exited", exit_code=1, restart="no")
        self.assertEqual(container_problems([ok]), {})
        self.assertIn("failed:plex-init", container_problems([bad]))

    def test_down_and_unhealthy_services_are_problems(self) -> None:
        problems = container_problems([
            _inspect("sonarr", "exited", exit_code=137),
            _inspect("radarr", "running", "unhealthy"),
            _inspect("plex", "running", "healthy"),
        ])
        self.assertEqual(set(problems), {"down:sonarr", "unhealthy:radarr"})

    def test_alerts_fire_once_per_transition(self) -> None:
        current = {"unhealthy:radarr": "radarr is unhealthy", "full:/x": "/x is 95% full"}
        new, resolved = diff({"full:/x", "down:sonarr"}, current)
        self.assertEqual(set(new), {"unhealthy:radarr"})
        self.assertEqual(resolved, {"down:sonarr"})
        self.assertEqual(restart_targets(new), ["radarr"])
        self.assertEqual(diff(set(current), current), ({}, set()))

    def test_disk_and_backup_thresholds(self) -> None:
        self.assertEqual(set(disk_problems({"/a": 95, "/b": 40, "/c": None})), {"full:/a", "missing:/c"})
        self.assertEqual(backup_problems(10), {})
        self.assertIn("backup:stale", backup_problems(48))
        self.assertIn("backup:never", backup_problems(None))


class ProfileNameTests(unittest.TestCase):
    def test_names_match_recyclarr_titles(self) -> None:
        root = Path(__file__).resolve().parents[1]
        yml = (root / "recyclarr" / "recyclarr.yml").read_text(encoding="utf-8")
        self.assertIn(RADARR_QUALITY_PROFILE, yml)
        self.assertIn(SONARR_QUALITY_PROFILE, yml)
        self.assertEqual(yml.count("allowed: false"), 2)
        self.assertNotIn("allowed: true", yml)
        self.assertIn("WEB 720p", yml)
        self.assertIn("HDTV-720p", yml)


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
        self.assertIn("media.scrobble", fields["on_watched_body"])
        self.assertIn("<episode>{show_name}</episode>", fields["on_watched_body"])
        self.assertIn("<movie>{title}</movie>", fields["on_watched_body"])
        self.assertIn("{themoviedb-<themoviedb_id}", fields["on_watched_body"])
        self.assertIn("<episode>/{thetvdb-<thetvdb_id}</episode>", fields["on_watched_body"])
        self.assertNotIn("{themoviedb-{themoviedb_id}", fields["on_watched_body"])
        json.loads(SIMKL_WATCHED_JSON)
        json.loads(apply_media_tags(SIMKL_WATCHED_JSON, "episode"))
        json.loads(apply_media_tags(SIMKL_WATCHED_JSON, "movie"))

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
                return {
                    "config": {"hook": store["hook"], "method": store.get("method", "")},
                    "actions": {"on_watched": store.get("on_watched", 0)},
                    "notify_text": {"on_watched": {"body": store.get("body", "")}},
                }
            if cmd == "set_notifier_config":
                store["hook"] = extra.get("webhook_hook", "")
                store["method"] = extra.get("webhook_method", "")
                store["on_watched"] = extra.get("on_watched", "0")
                store["body"] = extra.get("on_watched_body", "")
                store["notifiers"][0]["friendly_name"] = "SIMKL"
                return {}
            raise AssertionError(cmd)

        self.assertEqual(ensure_simkl_webhook(call, "https://api.simkl.com/x?t=1"), "updated")
        self.assertEqual(ensure_simkl_webhook(call, "https://api.simkl.com/x?t=1"), "ok")
        store["body"] = '{"event":"media.scrobble","guid":"/{themoviedb-{themoviedb_id}/"}'
        self.assertEqual(ensure_simkl_webhook(call, "https://api.simkl.com/x?t=1"), "updated")
        self.assertEqual(store["body"], SIMKL_WATCHED_JSON)

    def test_scrobble_from_episode_metadata_uses_show_ids(self) -> None:
        ids = ids_from_plex_guids(["imdb://tt19231492", "tmdb://196322", "tvdb://393159"])
        self.assertEqual(ids["themoviedb_id"], "196322")
        self.assertEqual(ids["imdb_id"], "tt19231492")
        self.assertEqual(ids["thetvdb_id"], "393159")
        payload = scrobble_from_metadata(
            {
                "media_type": "episode",
                "title": "Entanglement",
                "grandparent_title": "Dark Matter",
                "year": "2024",
                "parent_media_index": 1,
                "media_index": 9,
                "grandparent_guids": ["imdb://tt19231492", "tmdb://196322", "tvdb://393159"],
                "guids": ["tmdb://5127547"],
            },
            username="Local",
        )
        self.assertEqual(payload["event"], "media.scrobble")
        self.assertEqual(payload["Metadata"]["type"], "episode")
        self.assertEqual(payload["Metadata"]["title"], "Dark Matter")
        self.assertEqual(
            payload["Metadata"]["guid"],
            "/themoviedb-196322/imdb-tt19231492/thetvdb-393159//1/9/",
        )
        self.assertNotIn("5127547", payload["Metadata"]["guid"])

    def test_replay_empty_watched_bodies(self) -> None:
        posted: list = []

        def call(cmd: str, extra=None):
            extra = extra or {}
            if cmd == "get_notification_log":
                return {
                    "data": [
                        {
                            "notify_action": "on_watched",
                            "body_text": "",
                            "rating_key": 345,
                            "user": "Local",
                        },
                        {
                            "notify_action": "on_watched",
                            "body_text": '{"event":"media.scrobble"}',
                            "rating_key": 999,
                            "user": "Local",
                        },
                    ]
                }
            if cmd == "get_metadata":
                return {
                    "media_type": "episode",
                    "title": "Love",
                    "grandparent_title": "Babies",
                    "year": "2020",
                    "parent_media_index": 1,
                    "media_index": 1,
                    "grandparent_guids": ["tmdb://99103", "tvdb://376756"],
                }
            raise AssertionError(cmd)

        count = replay_empty_watched_webhooks(
            call, lambda url, body: posted.append((url, body)), "https://api.simkl.com/x"
        )
        self.assertEqual(count, 1)
        self.assertEqual(posted[0][0], "https://api.simkl.com/x")
        self.assertEqual(posted[0][1]["Metadata"]["title"], "Babies")


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

    def test_qbit_seed_prefs_are_unlimited(self) -> None:
        prefs = seed_unlimited_preferences()
        self.assertFalse(prefs["queueing_enabled"])
        self.assertEqual(prefs["max_active_torrents"], -1)
        self.assertEqual(prefs["max_active_uploads"], -1)
        self.assertFalse(prefs["max_ratio_enabled"])
        self.assertFalse(prefs["max_seeding_time_enabled"])
        self.assertEqual(prefs["max_ratio_act"], 0)


class CatchupTests(unittest.TestCase):
    def test_recent_missing_episodes_respect_lookback(self) -> None:
        today = date(2026, 9, 6)
        records = [
            {"id": 1, "airDate": "2026-09-04"},  # 2d ago
            {"id": 2, "airDate": "2026-08-20"},  # 17d ago
            {"id": 3, "airDate": "2026-09-11"},  # future
            {"id": 4, "airDate": None},
            {"id": 5, "airDate": "2026-08-24"},  # exactly 13d
        ]
        self.assertEqual(
            recent_missing_episode_ids(records, today=today, lookback_days=14),
            [1, 5],
        )

    def test_recent_missing_movies_prefer_digital_then_physical(self) -> None:
        today = date(2026, 9, 6)
        records = [
            {
                "id": 10,
                "digitalRelease": "2026-09-01T00:00:00Z",
                "inCinemas": "2025-01-01T00:00:00Z",
            },
            {
                "id": 11,
                "digitalRelease": None,
                "physicalRelease": "2026-09-05T00:00:00Z",
            },
            {
                "id": 12,
                "digitalRelease": None,
                "physicalRelease": None,
                "inCinemas": "2026-08-01T00:00:00Z",
            },
            {"id": 13, "digitalRelease": "2025-01-01T00:00:00Z"},
        ]
        self.assertEqual(
            recent_missing_movie_ids(records, today=today, lookback_days=14),
            [10, 11],
        )

    def test_search_commands_omit_empty(self) -> None:
        self.assertIsNone(episode_search_command([]))
        self.assertIsNone(movies_search_command([]))
        self.assertEqual(
            episode_search_command([2587, 3206]),
            {"name": "EpisodeSearch", "episodeIds": [2587, 3206]},
        )
        self.assertEqual(
            movies_search_command([19]),
            {"name": "MoviesSearch", "movieIds": [19]},
        )


if __name__ == "__main__":
    unittest.main()
