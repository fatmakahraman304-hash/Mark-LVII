import json
import unittest
from unittest.mock import MagicMock, patch
from plugins import normal_map as m

class MapTests(unittest.TestCase):
    def setUp(self):
        m._cache.clear()
        m._last_request = 0

    def test_search_coordinates_and_cache(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps([{'lat':'41','lon':'29','display_name':'İstanbul, Türkiye','addresstype':'city'}]).encode()
        with patch.object(m,'urlopen',return_value=response) as get:
            result=m.search('İstanbul')
            self.assertEqual(result[0]['zoom'],12)
            self.assertEqual(result[0]['lat'],41)
            self.assertEqual(m.search('İstanbul'),result)
            self.assertEqual(get.call_count,1)

    def test_invalid_coordinates_not_shown(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=b'[{"lat":"nan","lon":"29","display_name":"bad"}]'
        with patch.object(m,'urlopen',return_value=response):
            self.assertEqual(m.search('bad'),[])

    def test_missing_ui_or_place(self):
        self.assertIn('adını',m.run({}))
        self.assertIn('arayüzü',m.run({'place':'Paris'}))
