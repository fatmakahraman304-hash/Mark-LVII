import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from core import app_updater as u


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'requirements.txt').write_text('test==1\n')
        (self.root / 'update_channel.json').write_text('{"branch":"feature/osiris-world-command"}')
        self.files = {'main.py': b'new', 'requirements.txt': b'test==1\n', 'gui/window.py': b'window'}
        self.sha = 'a' * 40

    def archive(self, extra=None):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for name, data in {**self.files, **(extra or {})}.items():
                z.writestr('repo/' + name, data)
        return buf.getvalue()

    def test_zip_update_then_current(self):
        with patch.object(u, '_get', side_effect=[json.dumps({'sha': self.sha}).encode(), self.archive()]):
            self.assertTrue(u.update(self.root)[0])
        self.assertEqual((self.root / 'main.py').read_bytes(), b'new')
        with patch.object(u, '_get', return_value=json.dumps({'sha': self.sha}).encode()) as get:
            self.assertFalse(u.update(self.root)[0])
            self.assertEqual(get.call_count, 1)
        self.assertFalse((self.root / '.jarvis-update.lock').exists())

    def test_git_fast_forward_and_backup(self):
        import subprocess
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()
        git('init', '-b', 'main')
        git('config', 'user.email', 'tests@example.invalid')
        git('config', 'user.name', 'Updater tests')
        (self.root / 'main.py').write_bytes(b'old')
        git('add', '.')
        git('commit', '-m', 'old')
        old = git('rev-parse', 'HEAD')
        (self.root / 'main.py').write_bytes(b'new')
        git('commit', '-am', 'new')
        new = git('rev-parse', 'HEAD')
        git('reset', '--hard', old)
        real_git = u._git
        def local_fetch(root, *args):
            if args[0] == 'fetch':
                return ''  # target commit already exists in this isolated test repo
            return real_git(root, *args)
        with patch.object(u, '_git', side_effect=local_fetch), patch.object(
                u, '_get', side_effect=[json.dumps({'sha': new}).encode(), self.archive()]):
            self.assertTrue(u.update(self.root)[0])
        self.assertEqual(git('rev-parse', 'HEAD'), new)
        self.assertIn('jarvis-backup/', git('branch', '--list'))
        self.assertEqual((self.root / 'main.py').read_bytes(), b'new')

    def test_git_dirty_code_refused_before_network(self):
        (self.root / '.git').mkdir()
        with patch.object(u, '_git', return_value=' M main.py'), patch.object(u, '_get') as get:
            with self.assertRaisesRegex(RuntimeError, 'Yerel kod'):
                u.update(self.root)
            get.assert_not_called()

    def test_personal_data_untouched(self):
        config = self.root / 'config/api_keys.json'
        config.parent.mkdir()
        config.write_text('private')
        files = u._archive(self.archive({'config/api_keys.json': b'overwrite', 'memory/long_term.json': b'overwrite'}))
        u._apply_zip(self.root, files, self.sha, 'main')
        self.assertEqual(config.read_text(), 'private')
        self.assertNotIn('memory/long_term.json', files)

    def test_path_traversal_rejected(self):
        with self.assertRaises(RuntimeError):
            u._archive(self.archive({'../../outside': b'bad'}))

    def test_local_edit_blocks_second_update(self):
        u._apply_zip(self.root, self.files, self.sha, 'main')
        (self.root / 'main.py').write_text('custom')
        with self.assertRaisesRegex(RuntimeError, 'Yerel değişiklik'):
            u._apply_zip(self.root, self.files, 'b' * 40, 'main')
        self.assertEqual((self.root / 'main.py').read_text(), 'custom')

    def test_removed_tracked_file_deleted_custom_file_kept(self):
        u._apply_zip(self.root, {**self.files, 'obsolete.py': b'old'}, self.sha, 'main')
        (self.root / 'custom.py').write_text('keep')
        u._apply_zip(self.root, self.files, 'b' * 40, 'main')
        self.assertFalse((self.root / 'obsolete.py').exists())
        self.assertTrue((self.root / 'custom.py').exists())

    def test_write_failure_rolls_back(self):
        (self.root / 'main.py').write_bytes(b'original')
        real = u.os.replace
        def fail(source, target):
            if str(target).endswith('main.py'):
                raise OSError('disk failure')
            return real(source, target)
        with patch.object(u.os, 'replace', side_effect=fail):
            with self.assertRaises(OSError):
                u._apply_zip(self.root, self.files, self.sha, 'main')
        self.assertEqual((self.root / 'main.py').read_bytes(), b'original')
        self.assertFalse((self.root / 'gui/window.py').exists())
        self.assertFalse((self.root / '.jarvis-update.json').exists())

    def test_network_failure_unlocks(self):
        with patch.object(u, '_get', side_effect=TimeoutError('offline')):
            with self.assertRaises(TimeoutError):
                u.update(self.root)
        self.assertFalse((self.root / '.jarvis-update.lock').exists())

    def test_dependency_change_does_not_modify_source(self):
        self.files['requirements.txt'] = b'new-dependency==2\n'
        with patch.object(u, '_get', side_effect=[json.dumps({'sha': self.sha}).encode(), self.archive()]):
            with self.assertRaisesRegex(RuntimeError, 'bağımlılıklar'):
                u.update(self.root)
        self.assertFalse((self.root / 'main.py').exists())

    def test_lock_prevents_concurrent_update(self):
        (self.root / '.jarvis-update.lock').touch()
        with self.assertRaisesRegex(RuntimeError, 'Başka bir güncelleme'):
            u.update(self.root)
        self.assertTrue((self.root / '.jarvis-update.lock').exists())

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / 'gui').symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest('symlinks not permitted')
            with self.assertRaises(RuntimeError):
                u._apply_zip(self.root, self.files, self.sha, 'main')
            self.assertFalse((Path(outside) / 'window.py').exists())


if __name__ == '__main__':
    unittest.main()
