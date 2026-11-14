import json
import unittest
from unittest.mock import MagicMock, patch
from plugins.map_route import route

class RouteTests(unittest.TestCase):
    def response(self, data):
        r=MagicMock();r.__enter__.return_value.read.return_value=json.dumps(data).encode();return r
    def test_route_geometry_and_metrics(self):
        data={'code':'Ok','routes':[{'geometry':{'coordinates':[[29,41],[30,40]]},'distance':150000,'duration':7200}]}
        p={'lat':41,'lon':29,'name':'A'}
        with patch('plugins.map_route.urlopen',return_value=self.response(data)):
            result=route(p,p)
        self.assertEqual(result['distance'],150000)
        self.assertEqual(len(result['points']),2)
    def test_no_route_is_not_success(self):
        p={'lat':0,'lon':0,'name':'A'}
        with patch('plugins.map_route.urlopen',return_value=self.response({'code':'NoRoute'})):
            with self.assertRaises(ValueError): route(p,p)
