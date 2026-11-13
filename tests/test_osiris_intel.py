"""Offline contract tests for read-only OSIRIS public-data summaries."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from plugins import osiris_intel as intel


class StubUI:
    def __init__(self):
        self.results = []

    def show_content(self, heading, body):
        self.results.append((heading, body))


class OsirisIntelTests(unittest.TestCase):
    def setUp(self):
        intel._cache.clear()

    @patch("plugins.osiris_intel._fetch_json")
    def test_stats_show_timestamp_and_source(self, fetch):
        fetch.return_value = {
            "stats": {"flights": 50, "sats": 20, "cctv": 15,
                      "weather": 2, "incidents": 1},
            "timestamp": "2026-11-13T11:20:30Z",
        }
        ui = StubUI()
        spoken = intel.run({"mode": "stats"}, player=ui)
        self.assertIn("Uçuş kayıtları: 50", spoken)
        self.assertIn("13.11.2026 11:20 UTC", ui.results[0][1])
        self.assertIn("https://osirisai.live/api/stats", ui.results[0][1])
        self.assertIn("eksik olabilir", ui.results[0][1])
        self.assertEqual(fetch.call_count, 1)

    @patch("plugins.osiris_intel._fetch_json")
    def test_cached_api_results_do_not_poll_again(self, fetch):
        fetch.return_value = {
            "stats": {"flights": 12}, "timestamp": "2026-11-13T11:20:30Z"
        }
        intel.run({"mode": "stats"})
        intel.run({"mode": "stats"})
        self.assertEqual(fetch.call_count, 1)

    @patch("plugins.osiris_intel._fetch_json")
    def test_earthquake_magnitude_and_freshness(self, fetch):
        fetch.return_value = {
            "total": 3,
            "timestamp": "2026-11-13T11:00:00Z",
            "earthquakes": [
                {"magnitude": 3.3, "time": 1700000000000, "place": "A"},
                {"magnitude": 5.5, "time": 1700000001000, "place": "B"},
                {"magnitude": 4.0, "time": 1700000002000, "place": "C"},
            ],
        }
        ui = StubUI()
        spoken = intel.run(
            {"mode": "earthquakes", "sort": "strongest", "limit": 2},
            player=ui,
        )
        self.assertIn("Toplam kayıt: 3", spoken)
        text = ui.results[0][1]
        self.assertLess(text.index("M 5.5"), text.index("M 4.0"))
        self.assertNotIn("M 3.3", text)
        self.assertIn("USGS", text)
        self.assertIn("Bu bir afet alarmı", text)

    @patch("plugins.osiris_intel._fetch_json")
    def test_api_error_does_not_create_fake_events(self, fetch):
        fetch.return_value = {
            "earthquakes": [], "error": "USGS unavailable"
        }
        ui = StubUI()
        spoken = intel.run({"mode": "earthquakes"}, player=ui)
        self.assertIn("doğrulanamadı", spoken)
        self.assertEqual(ui.results, [])

    @patch("plugins.osiris_intel._fetch_json")
    def test_unknown_mode_never_fetches(self, fetch):
        message = intel.run({"mode": "scanner"})
        self.assertIn("stats", message)
        fetch.assert_not_called()
        message = intel.run({"mode": "earthquakes", "limit": 99999})
        self.assertIn("1 ile 8", message)
        fetch.assert_not_called()

    def test_only_read_endpoints_allowed(self):
        with self.assertRaises(ValueError):
            intel._endpoint("/api/scanner")
        with self.assertRaises(ValueError):
            intel._endpoint("//other.host/api/stats")

    def test_invalid_timestamp_and_counts_marked_unknown(self):
        spoken, report = intel._stats({
            "stats": {"flights": -1, "sats": "oops", "cctv": 4},
            "timestamp": "tomorrow",
        })
        self.assertIn("Uçuş kayıtları: veri yok", spoken)
        self.assertIn("API zaman damgası: belirtilmedi", report)

    @patch("plugins.osiris_intel._fetch_json", side_effect=OSError("offline"))
    def test_network_failure_returns_honest_message(self, fetch):
        reply = intel.run({"mode": "stats"})
        self.assertIn("doğrulanamadı", reply)


if __name__ == "__main__":
    unittest.main()
