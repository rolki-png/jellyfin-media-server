#!/usr/bin/env python3
"""Guards the vendored Freeloader Marker / Skip Intro unlock."""

from __future__ import annotations

import unittest
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "freeloader" / "vendor"

# PMS 1.43.2 per-user feature-bit lookup prologue. Bitset-only Freeloader
# leaves intro/credits Marker emission gated on this function.
MODERN_USER_FEATURE_SIG = (
    "55 48 89 E5 48 8B 07 4C 8B 08 4C 8B 40 08 4C 89 C7 4C 29 CF 74 37"
)


class FreeloaderVendorTests(unittest.TestCase):
    def test_vendor_pins_known_freeloader_commit(self) -> None:
        version = (VENDOR / "VERSION").read_text(encoding="utf-8")
        self.assertIn("6efe3c8be82c0b4a3ac13ebd17a3fe101fc4927c", version)

    def test_hook_installs_modern_per_user_feature_check(self) -> None:
        hook = (VENDOR / "src" / "hook.cpp").read_text(encoding="utf-8")
        self.assertIn(MODERN_USER_FEATURE_SIG, hook)
        self.assertIn("Do NOT return here", hook)
        self.assertIn("return true;", hook)

    def test_zydis_is_vendored_compressed(self) -> None:
        self.assertTrue((VENDOR / "third_party" / "zydis" / "Zydis.c.xz").is_file())
        self.assertTrue((VENDOR / "third_party" / "zydis" / "Zydis.h").is_file())


if __name__ == "__main__":
    unittest.main()
