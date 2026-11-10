import unittest

from update import preserve_main_pin_pending_link3


class MainPinPolicyTests(unittest.TestCase):
    def test_reported_failed_pin_is_retained_not_called_working(self):
        item = {
            "name": "Duronto TV",
            "last_known_url": "https://example.com/duronto.m3u8",
            "require_link3_confirmation": True,
        }
        result = preserve_main_pin_pending_link3(
            item, "https://new-candidate.example/live.m3u8", set()
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["url"], item["last_known_url"])
        self.assertEqual(result["source"], "last-known-unverified")
        self.assertNotEqual(result["url"], "https://new-candidate.example/live.m3u8")

    def test_does_not_reuse_url_already_assigned_to_another_channel(self):
        item = {
            "name": "Duronto TV",
            "last_known_url": "https://example.com/duronto.m3u8",
            "require_link3_confirmation": True,
        }
        result = preserve_main_pin_pending_link3(
            item, "", {"https://example.com/duronto.m3u8"}
        )
        self.assertIsNone(result)

    def test_policy_does_not_apply_to_other_channels(self):
        item = {
            "name": "ATN Bangla",
            "last_known_url": "https://example.com/atn.m3u8",
            "require_link3_confirmation": False,
        }
        self.assertIsNone(preserve_main_pin_pending_link3(item, "", set()))

    def test_missing_old_pin_does_not_create_fake_url(self):
        item = {"name": "Duronto TV", "require_link3_confirmation": True}
        self.assertIsNone(preserve_main_pin_pending_link3(item, "", set()))


if __name__ == "__main__":
    unittest.main()
