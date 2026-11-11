#!/usr/bin/env python3
"""Seam: stack_policy.plex_idle — Xbox vs this-desktop vs idle power/DPMS."""

from __future__ import annotations

import unittest

from stack_policy.plex_idle import (
    POWER_SAVER_AFTER_SEC,
    idle_seconds_from_hint,
    playback_from_xml,
    policy_for,
)

HOST_IPS = frozenset({"127.0.0.1", "192.168.1.10"})

XBOX = """
<MediaContainer size="1">
  <Video>
    <Player address="192.168.1.50" local="1" product="Plex for Xbox One"
            state="playing" title="Xbox Series X"/>
  </Video>
</MediaContainer>
"""

LOCAL_WEB = """
<MediaContainer size="1">
  <Video>
    <Player address="127.0.0.1" local="1" product="Plex Web"
            state="playing" title="Plex Web (Chrome)"/>
  </Video>
</MediaContainer>
"""

PAUSED_XBOX = """
<MediaContainer size="1">
  <Video>
    <Player address="192.168.1.50" local="1" product="Plex for Xbox One"
            state="paused" title="Xbox Series X"/>
  </Video>
</MediaContainer>
"""

EMPTY = '<MediaContainer size="0"></MediaContainer>'


class IdleHintTests(unittest.TestCase):
    def test_realtime_usec_is_seconds_since_that_wall_clock(self) -> None:
        since = 1_700_000_000_000_000
        self.assertEqual(
            idle_seconds_from_hint(since, now_realtime=1_700_000_000.0 + 90, now_monotonic=12.0),
            90.0,
        )

    def test_monotonic_usec_uses_uptime_clock(self) -> None:
        self.assertEqual(
            idle_seconds_from_hint(5_000_000, now_realtime=1_700_000_000.0, now_monotonic=12.0),
            7.0,
        )


class PlaybackFromXmlTests(unittest.TestCase):
    def test_empty_is_idle(self) -> None:
        p = playback_from_xml(EMPTY, HOST_IPS)
        self.assertFalse(p.any_active)
        self.assertFalse(p.local_screen)

    def test_xbox_is_active_but_not_this_monitor(self) -> None:
        p = playback_from_xml(XBOX, HOST_IPS)
        self.assertTrue(p.any_active)
        self.assertFalse(p.local_screen)

    def test_plex_web_on_this_host_is_local_screen(self) -> None:
        p = playback_from_xml(LOCAL_WEB, HOST_IPS)
        self.assertTrue(p.any_active)
        self.assertTrue(p.local_screen)

    def test_paused_xbox_still_counts_as_active(self) -> None:
        p = playback_from_xml(PAUSED_XBOX, HOST_IPS)
        self.assertTrue(p.any_active)
        self.assertFalse(p.local_screen)


class PolicyTests(unittest.TestCase):
    def test_at_desk_no_plex_is_performance(self) -> None:
        pol = policy_for(playback_from_xml(EMPTY, HOST_IPS), user_idle=False, idle_seconds=0)
        self.assertEqual(pol.power_profile, "performance")
        self.assertFalse(pol.stay_awake)
        self.assertFalse(pol.dpms_off)

    def test_idle_15m_no_plex_is_power_saver(self) -> None:
        pol = policy_for(
            playback_from_xml(EMPTY, HOST_IPS),
            user_idle=True,
            idle_seconds=POWER_SAVER_AFTER_SEC,
        )
        self.assertEqual(pol.power_profile, "power-saver")
        self.assertFalse(pol.stay_awake)
        self.assertFalse(pol.dpms_off)

    def test_idle_under_15m_no_plex_stays_performance(self) -> None:
        pol = policy_for(
            playback_from_xml(EMPTY, HOST_IPS),
            user_idle=True,
            idle_seconds=POWER_SAVER_AFTER_SEC - 1,
        )
        self.assertEqual(pol.power_profile, "performance")

    def test_xbox_idle_blanks_monitor_keeps_cpu_and_no_lock(self) -> None:
        pol = policy_for(
            playback_from_xml(XBOX, HOST_IPS),
            user_idle=True,
            idle_seconds=POWER_SAVER_AFTER_SEC,
        )
        self.assertEqual(pol.power_profile, "performance")
        self.assertTrue(pol.stay_awake)
        self.assertTrue(pol.dpms_off)

    def test_xbox_while_at_desk_leaves_monitor_on(self) -> None:
        pol = policy_for(
            playback_from_xml(XBOX, HOST_IPS),
            user_idle=False,
            idle_seconds=0,
        )
        self.assertTrue(pol.stay_awake)
        self.assertFalse(pol.dpms_off)
        self.assertEqual(pol.power_profile, "performance")

    def test_local_plex_idle_keeps_monitor_on(self) -> None:
        pol = policy_for(
            playback_from_xml(LOCAL_WEB, HOST_IPS),
            user_idle=True,
            idle_seconds=POWER_SAVER_AFTER_SEC,
        )
        self.assertTrue(pol.stay_awake)
        self.assertFalse(pol.dpms_off)
        self.assertEqual(pol.power_profile, "performance")


if __name__ == "__main__":
    unittest.main()
