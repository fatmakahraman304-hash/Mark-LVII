"""Dependency-free tests for the OSIRIS voice bridge."""
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from plugins import osiris_world as plugin


class OsirisPluginTests(unittest.TestCase):
    def setUp(self):
        plugin._selected_layers = set(plugin.DEFAULT_LAYERS)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("JARVIS_OSIRIS_URL", None)

    def tearDown(self):
        self.env.stop()
        plugin._selected_layers = set(plugin.DEFAULT_LAYERS)

    def test_layer_aliases_and_validation(self):
        self.assertEqual(
            plugin.parse_layers("Uçaklar ve depremler, gemiler"),
            {"flights", "earthquakes", "maritime"},
        )
        with self.assertRaises(ValueError):
            plugin.parse_layers("flights, bilinmeyen")
        with self.assertRaises(ValueError):
            plugin.parse_layers("")

    def test_build_url_matches_documented_osiris_query(self):
        url = plugin.build_url({"earthquakes", "cctv"})
        parts = urlsplit(url)
        self.assertEqual(parts.hostname, "osirisai.live")
        self.assertEqual(parts.scheme, "https")
        self.assertEqual(
            parse_qs(parts.query)["layers"], ["cctv,earthquakes"]
        )

    def test_clear_uses_nonempty_sentinel(self):
        self.assertEqual(
            parse_qs(urlsplit(plugin.build_url(set())).query)["layers"],
            ["none"],
        )

    def test_url_override_is_loopback_only(self):
        os.environ["JARVIS_OSIRIS_URL"] = "http://127.0.0.1:3005/"
        self.assertEqual(
            urlsplit(plugin.build_url({"flights"})).netloc,
            "127.0.0.1:3005",
        )
        for url in ("https://untrusted.example/", "http://10.0.0.2:3000",
                    "https://osirisai.live/evil",
                    "https://osirisai.live/?redirect=evil"):
            os.environ["JARVIS_OSIRIS_URL"] = url
            with self.assertRaises(ValueError, msg=url):
                plugin.build_url({"flights"})

    @patch("plugins.osiris_world.webbrowser.open", return_value=True)
    def test_run_show_hide_and_preset(self, browser):
        first = plugin.run({"mode": "focus", "layers": "uçaklar"})
        self.assertIn("Seçili katman sayısı: 1", first)
        self.assertEqual(plugin._selected_layers, {"flights"})
        plugin.run({"mode": "show", "layers": "depremler"})
        self.assertEqual(plugin._selected_layers, {"flights", "earthquakes"})
        plugin.run({"mode": "hide", "layers": "uçak"})
        self.assertEqual(plugin._selected_layers, {"earthquakes"})
        plugin.run({"mode": "preset", "preset": "kameralar"})
        self.assertEqual(plugin._selected_layers,
                         {"cctv", "cctv_previews", "day_night"})
        self.assertEqual(browser.call_count, 4)

    @patch("plugins.osiris_world.webbrowser.open", return_value=True)
    def test_invalid_layer_never_opens_browser(self, browser):
        reply = plugin.run({"mode": "show", "layers": "https://evil.test"})
        self.assertIn("Tanınmayan", reply)
        browser.assert_not_called()

    @patch("plugins.osiris_world.webbrowser.open", return_value=False)
    def test_browser_refusal_keeps_selection(self, browser):
        before = set(plugin._selected_layers)
        reply = plugin.run({"mode": "focus", "layers": "earthquakes"})
        self.assertIn("kabul edilmedi", reply)
        self.assertEqual(plugin._selected_layers, before)

    @patch("plugins.osiris_world.webbrowser.open", return_value=True)
    def test_reset_and_clear(self, browser):
        plugin.run({"mode": "clear"})
        self.assertEqual(plugin._selected_layers, set())
        plugin.run({"mode": "reset"})
        self.assertEqual(plugin._selected_layers, set(plugin.DEFAULT_LAYERS))
        self.assertEqual(browser.call_count, 2)

    @patch("plugins.osiris_world.webbrowser.open", side_effect=RuntimeError("test"))
    def test_browser_error_is_reported_not_raised(self, browser):
        result = plugin.run({"mode": "open"})
        self.assertIn("çalışmadı", result)
        browser.assert_called_once()


if __name__ == "__main__":
    unittest.main()
