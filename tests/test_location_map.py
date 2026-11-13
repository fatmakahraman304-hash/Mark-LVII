"""Offline checks: run with python -m unittest discover -s tests -p test_location_map.py."""
import json
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QNetworkReply
from gui.location_map import LocationPanel, location_from_json, tile_position


class Reply:
    def __init__(self, body=b"", failed=False):
        self.body, self.failed, self.deleted = body, failed, False
    def error(self):
        return QNetworkReply.NetworkError.TimeoutError if self.failed else QNetworkReply.NetworkError.NoError
    def readAll(self):
        return self.body
    def deleteLater(self):
        self.deleted = True


class LocationMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_rejects_failed_or_malformed_locations(self):
        for value in [None, [], {}, {"success": False}, {"success": True, "city": "X", "latitude": 91, "longitude": 0},
                      {"success": True, "city": "X", "latitude": float("nan"), "longitude": 0}]:
            with self.subTest(value=value), self.assertRaises((ValueError, KeyError)):
                location_from_json(json.dumps(value).encode())

    def test_mercator_equator_and_poles(self):
        self.assertEqual(tile_position(0, 0, 11), (1024, 1024))
        x, y = tile_position(90, 180, 11)
        self.assertAlmostEqual(y, 0, places=6)

    def test_location_update_and_failure_keep_last_city(self):
        panel = LocationPanel(auto_start=False)
        with patch.object(panel.map, "load_tiles"):
            for city, lat, lon in [("Gazimağusa", 35.12, 33.94), ("Lefkoşa", 35.18, 33.38)]:
                reply = Reply(json.dumps(dict(success=True, city=city, latitude=lat, longitude=lon)).encode())
                panel._location_ready(reply)
                self.assertEqual(panel.city.text(), city)
                self.assertEqual(panel.map.center, tile_position(lat, lon, 11))
                self.assertTrue(reply.deleted)
            panel._location_ready(Reply(failed=True))
            self.assertEqual(panel.city.text(), "Lefkoşa")
            self.assertIn("Son konum", panel.status.text())
            panel._location_ready(Reply(b"null"))
            self.assertFalse(panel._busy)
        panel.close()

    def test_offline_start_does_not_invent_a_city(self):
        panel = LocationPanel(auto_start=False)
        panel._location_ready(Reply(failed=True))
        self.assertEqual(panel.city.text(), "Konum alınamadı")
        self.assertIsNone(panel.map.center)
        self.assertEqual(panel.timer.interval(), 300000)
        panel.close()


if __name__ == "__main__":
    unittest.main()
