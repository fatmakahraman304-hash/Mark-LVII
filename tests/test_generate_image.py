import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from plugins import generate_image as g

class ImageTests(unittest.TestCase):
    def test_background_display_and_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            player = Mock(current_file=None)
            done = threading.Event()
            player.show_image.side_effect = lambda *a: done.set()
            with patch.object(g, '_paid_allowed', return_value=True), patch.object(g.gemini, '_BASE', Path(tmp)), patch.object(g.gemini, 'generate_picture', return_value=(b'image', 'image/png')) as generate:
                self.assertIn('arka planda', g.run({'prompt':'deniz', 'provider':'gemini'}, player))
                self.assertTrue(done.wait(3))
                # Wait for worker to release the operation lock.
                with g._lock:
                    pass
                path = Path(player.show_image.call_args.args[0])
                self.assertEqual(path.read_bytes(), b'image')
                done.clear()
                g.run({'prompt':'mavi yap', 'mode':'edit', 'provider':'gemini'}, player)
                self.assertTrue(done.wait(3))
                with g._lock:
                    pass
                self.assertEqual(generate.call_args.args[1], path)

    def test_failure_does_not_show_image(self):
        player = Mock()
        g._lock.acquire()
        with patch.object(g.gemini, 'generate_picture', side_effect=RuntimeError('private request')):
            g._work('test', None, player, 'gemini')
        player.show_image.assert_not_called()
        self.assertNotIn('private request', player.write_log.call_args.args[0])
        self.assertFalse(g._lock.locked())

    def test_busy(self):
        g._lock.acquire()
        try:
            self.assertIn('hâlâ', g.run({'prompt':'test'}, Mock()))
        finally:
            g._lock.release()
