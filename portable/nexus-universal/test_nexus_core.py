import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nexus_core import load_catalog, negotiate

CATALOG = Path(__file__).with_name("capabilities.json")


class CatalogTests(unittest.TestCase):
    def test_catalog_loads_and_has_unique_profiles(self):
        profiles = load_catalog(CATALOG)
        self.assertGreaterEqual(len(profiles), 8)
        self.assertIn("android_tv", profiles)
        self.assertEqual(profiles["tizen"].capabilities, frozenset())

    def test_unknown_platform_fails_closed(self):
        result = negotiate(load_catalog(CATALOG), "unrecognized", {"browser-ui"}, user_authorized=True)
        self.assertFalse(result.available)
        self.assertEqual(result.unavailable, frozenset({"browser-ui"}))

    def test_requires_authorization(self):
        result = negotiate(load_catalog(CATALOG), "windows", {"browser-ui"})
        self.assertFalse(result.available)
        self.assertIn("authorization", result.reason)

    def test_unverified_never_granted(self):
        result = negotiate(load_catalog(CATALOG), "android_tv", {"browser-ui"}, user_authorized=True)
        self.assertFalse(result.available)
        self.assertIn("not verified", result.reason)

    def test_unknown_capability_rejected(self):
        with self.assertRaises(ValueError):
            negotiate(load_catalog(CATALOG), "windows", {"device-takeover"}, user_authorized=True)

    def test_duplicate_catalog_ids_rejected(self):
        with TemporaryDirectory() as directory:
            obj = json.loads(CATALOG.read_text(encoding="utf-8"))
            obj["device_profiles"].append(dict(obj["device_profiles"][0]))
            p = Path(directory) / "bad.json"
            p.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_catalog(p)


if __name__ == "__main__":
    unittest.main()
