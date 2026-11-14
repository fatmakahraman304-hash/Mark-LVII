import unittest
from unittest.mock import patch
from plugins import github_develop as g
class PublishGuards(unittest.TestCase):
    def test_secret_and_escape_rejected(self):
        for path in ['config/api_keys.json','../outside.py','.env','token.json']:
            with self.assertRaises(ValueError): g.selected_files([path])
    def test_source_allowed(self):
        self.assertEqual(g.selected_files(['gui/window.py']),['gui/window.py'])
    def test_empty_scope_rejected(self):
        with self.assertRaises(ValueError): g.selected_files([])


class TestOutput(unittest.TestCase):
    def test_failed_suite_reports_filename_and_python_error(self):
        with patch.object(g.subprocess, "run") as run:
            run.return_value = g.subprocess.CompletedProcess(
                [], 1, "", "AssertionError: expected result"
            )
            with self.assertRaisesRegex(g.TestFailure, "test_example.py") as error:
                g.command(["python", "-m", "unittest"], test_name="test_example.py")
        self.assertIn("AssertionError: expected result", str(error.exception))
        self.assertEqual(run.call_args.kwargs["env"]["QT_QPA_PLATFORM"], "offscreen")
