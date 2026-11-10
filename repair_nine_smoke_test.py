#!/usr/bin/env python3
"""Offline safety checks: preserve manual TEST IDs while rescanning nine channels."""
import json
import unittest
from pathlib import Path

import repair_probe


ROOT = Path(__file__).resolve().parent


class RepairNineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test = (ROOT / "three_channel_test.m3u").read_text(encoding="utf-8")
        cls.main = (ROOT / "playlist.m3u").read_text(encoding="utf-8")
        cls.catalog = json.loads((ROOT / "channels.json").read_text(encoding="utf-8"))

    def test_all_nine_have_existing_test_candidates(self):
        grouped = repair_probe.existing_nine_test_candidates(self.test)
        self.assertEqual(len(grouped), 9)
        for channel in repair_probe.REMAINING_TARGETS:
            with self.subTest(channel=channel):
                self.assertTrue(grouped[channel], "No existing published TEST entries")
                self.assertTrue(all("test_id" in c for c in grouped[channel]))

    def test_manual_test_entries_never_deleted(self):
        original = self.test
        simulated = original + (
            "\n" + repair_probe.NEW_GENERATED_MARKER + "\n"
            '#EXTINF:-1 tvg-name="Generated RECHECK",Generated RECHECK\n'
            "https://example.org/generated.m3u8\n"
        )
        cleaned = repair_probe.remove_old_repair_entries(simulated)
        self.assertEqual(cleaned.rstrip(), original.rstrip())
        self.assertIn("Duronto TV REPAIR TEST 01", cleaned)
        self.assertIn("Independent TV REPAIR TEST 01", cleaned)
        self.assertIn("ATN Bangla AUTO TEST 01", cleaned)
        self.assertIn("Channel 24 AUTO TEST 03", cleaned)
        self.assertIn("Somoy TV AUTO TEST 02", cleaned)

    def test_five_user_confirmed_main_urls_are_catalog_pins(self):
        main_urls = {}
        lines = self.main.splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("#EXTINF:"):
                continue
            label = line.rsplit(",", 1)[-1].strip()
            if label not in (
                "ATN Bangla", "Channel 24", "Somoy TV",
                "Zee Bangla", "Cartoon Network",
            ):
                continue
            next_lines = []
            for item in lines[i + 1 :]:
                if item.startswith("#EXTINF:"):
                    break
                if item.startswith(("https://", "http://")):
                    next_lines.append(item.strip())
            self.assertEqual(len(next_lines), 1)
            main_urls[label] = next_lines[0]
        for name, url in main_urls.items():
            row = next(x for x in self.catalog if x.get("name") == name)
            with self.subTest(channel=name):
                self.assertTrue(row.get("locked"))
                self.assertTrue(row.get("user_verified_link3"))
                self.assertEqual(row.get("last_known_url"), url)
        self.assertEqual(len(main_urls), 5)


if __name__ == "__main__":
    unittest.main()
