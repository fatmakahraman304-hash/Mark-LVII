"""Offline tests; never reach a real ComfyUI server or paid Gemini API."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from core import local_image
from plugins import generate_image as plugin


class ImageTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self._env = patch.dict(os.environ, {
            "JARVIS_ALLOW_PAID_IMAGES": "0",
            "JARVIS_COMFY_URL": "http://127.0.0.1:8188/",
        })
        self._env.start()
        self.addCleanup(self._env.stop)
        plugin._last_image = None

    def test_url_is_loopback_only(self):
        self.assertEqual(local_image.base_url(), "http://127.0.0.1:8188")
        for url in (
            "https://some-server.example/",
            "http://192.168.0.21:8188/",
            "http://user:pass@127.0.0.1:8188/",
            "http://localhost:8188/admin",
            "http://127.0.0.1:8188/?key=secret",
        ):
            os.environ["JARVIS_COMFY_URL"] = url
            with self.assertRaises(local_image.LocalImageError, msg=url):
                local_image.base_url()
        os.environ["JARVIS_COMFY_URL"] = "http://localhost:8189/"
        self.assertEqual(local_image.base_url(), "http://127.0.0.1:8189")

    def test_workflow_for_creation_has_valid_standard_nodes(self):
        nodes = local_image.make_workflow("modern house", "sdxl.safetensors")
        self.assertEqual(nodes["4"]["inputs"]["ckpt_name"], "sdxl.safetensors")
        self.assertEqual(nodes["6"]["inputs"]["text"], "modern house")
        self.assertEqual(nodes["3"]["inputs"]["latent_image"], ["5", 0])
        self.assertEqual(nodes["9"]["class_type"], "SaveImage")

    def test_editing_uses_uploaded_input_and_lower_denoise(self):
        nodes = local_image.make_workflow(
            "change roof colour", "sdxl.safetensors", image="example.png"
        )
        self.assertEqual(nodes["10"]["inputs"]["image"], "example.png")
        self.assertEqual(nodes["11"]["class_type"], "VAEEncode")
        self.assertEqual(nodes["3"]["inputs"]["latent_image"], ["11", 0])
        self.assertLess(nodes["3"]["inputs"]["denoise"], 1)

    def test_model_selection_avoids_incompatible_architecture(self):
        self.assertEqual(
            local_image._checkpoint(["flux1.safetensors", "my_sdxl.safetensors"]),
            "my_sdxl.safetensors",
        )
        with self.assertRaises(local_image.LocalImageError):
            local_image._checkpoint(["flux1.safetensors"])

    @patch("core.local_image._json")
    def test_local_probe_requires_a_model(self, query):
        query.return_value = []
        self.assertEqual(local_image.ready()[0], False)
        query.return_value = ["sdxl.safetensors"]
        self.assertTrue(local_image.ready()[0])

    @patch("core.local_image._read")
    @patch("core.local_image._json")
    @patch("core.local_image._checkpoints", return_value=["sdxl.safetensors"])
    def test_full_generate_contract_without_network(self, _models, query, read):
        job = "12345678-1234-1234-1234-123456789abc"
        def fake_json(path, **kw):
            if path == "/prompt":
                self.assertEqual(kw["body"]["prompt"]["4"]["inputs"]["ckpt_name"],
                                 "sdxl.safetensors")
                return {"prompt_id": job}
            if path == "/history/" + job:
                return {job: {"outputs": {"9": {"images": [
                    {"filename": "result.png", "subfolder": "", "type": "output"}
                ]}}}}
            raise AssertionError(path)
        query.side_effect = fake_json
        png = b"\x89PNG\r\n\x1a\n" + b"pixels"
        read.return_value = (png, "image/png")
        self.assertEqual(local_image.generate("futuristic seaside house"),
                         (png, "image/png"))
        read.assert_called_once()
        self.assertIn("/view?", read.call_args.args[0])

    @patch("plugins.generate_image.gemini.generate_picture")
    @patch("plugins.generate_image.local_image.ready", return_value=(False, "ComfyUI yok."))
    def test_free_default_does_not_use_paid_api(self, _ready, cloud):
        class Player:
            def show_image(self, *_):
                pass
        answer = plugin.run({"prompt": "beautiful landscape"}, player=Player())
        self.assertIn("ücretli API çağrısı otomatik yapılmadı", answer)
        cloud.assert_not_called()
        self.assertFalse(plugin._lock.locked())

    def test_paid_cloud_requires_external_explicit_opt_in(self):
        backend, message = plugin._backend("gemini")
        self.assertIsNone(backend)
        self.assertIn("ücretlidir", message)
        os.environ["JARVIS_ALLOW_PAID_IMAGES"] = "1"
        self.assertEqual(plugin._backend("gemini")[0], "gemini")

    def test_editing_accepts_only_user_selected_or_previous_file(self):
        class Player:
            current_file = None
        with self.assertRaises(ValueError):
            plugin._selected_source({"image_path": "/some/private/file.png"}, Player())
        image = Path(self.temp.name) / "picture.png"
        image.write_bytes(b"hello")
        Player.current_file = str(image)
        self.assertEqual(plugin._selected_source({}, Player()), image.resolve())
        with self.assertRaises(ValueError):
            plugin._selected_source({"image_path": "/another/file"}, Player())

    @patch("plugins.generate_image.local_image.generate",
           return_value=(b"\x89PNG\r\n\x1a\n" + b"pixels", "image/png"))
    def test_completed_image_appears_and_saves_locally(self, generate):
        class Player:
            def __init__(self):
                self.images = []
                self.messages = []
            def show_image(self, path, title):
                self.images.append((path, title))
            def write_log(self, message):
                self.messages.append(message)
        player = Player()
        with patch("plugins.generate_image.gemini._BASE", Path(self.temp.name)):
            plugin._lock.acquire()
            plugin._work("a house", None, player, "local")
        self.assertFalse(plugin._lock.locked())
        self.assertEqual(len(player.images), 1)
        self.assertTrue(Path(player.images[0][0]).is_file())
        self.assertIn("Oluşturuldu", player.messages[-1])


if __name__ == "__main__":
    unittest.main()
