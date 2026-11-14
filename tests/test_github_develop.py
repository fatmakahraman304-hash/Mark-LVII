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
