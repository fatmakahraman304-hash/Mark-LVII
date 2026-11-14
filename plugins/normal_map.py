"""User-initiated place search for JARVIS's native, pannable street map."""
import json
import math
import os
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PLUGIN = {
    'name': 'normal_map',
    'description': 'Open a requested city, country, street, landmark or address in the normal 2D street map INSIDE JARVIS. Use for all ordinary haritada aç/göster, orası nerede, go to place requests. Prefer this over OSIRIS or a browser unless the user explicitly asks for OSIRIS, globe, flights or special layers. Include known country/city context in place; never invent coordinates.',
    'parameters': {'type':'OBJECT', 'properties': {'place': {'type':'STRING', 'description':'Place or full address, with city/country when provided.'}}, 'required':['place']}}
_lock = threading.Lock()
_cache = {}
_last_request = 0.0


def search(place):
    global _last_request
    with _lock:
        key = place.casefold()
        if key in _cache:
            return _cache[key]
        time.sleep(max(0, 1.1 - (time.monotonic() - _last_request)))
        _last_request = time.monotonic()
        endpoint = os.environ.get('JARVIS_GEOCODER_URL', 'https://nominatim.openstreetmap.org/search')
        request = Request(endpoint + '?' + urlencode({'q':place, 'format':'jsonv2', 'limit':5, 'accept-language':'tr'}),
            headers={'User-Agent':'JarvisPersonalMap/1.0 (https://github.com/fatmakahraman304-hash/Mark-LVII)'})
        with urlopen(request, timeout=12) as response:
            values = json.loads(response.read(200000))
        results = []
        for item in values:
            lat, lon = float(item['lat']), float(item['lon'])
            if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            kind = item.get('addresstype', '')
            zoom = 5 if kind == 'country' else 10 if kind in {'state','province'} else 12 if kind in {'city','town','village'} else 16
            results.append({'name':str(item['display_name']), 'lat':lat, 'lon':lon, 'zoom':zoom})
        _cache[key] = results
        return results


def run(parameters, player=None, session_memory=None):
    place = str(parameters.get('place', '')).strip()
    if not place or len(place)>500:
        return 'Haritada açılacak yerin adını söyleyin.'
    if player is None or not callable(getattr(player, 'show_map_places', None)):
        return 'Normal harita için JARVIS arayüzü açık olmalı.'
    def work():
        try:
            results = search(place)
            if results:
                player.show_map_places(results)
            else:
                player.write_log('HARİTA: Yer bulunamadı. Şehir veya ülkeyi de belirtin.')
        except Exception:
            player.write_log('HARİTA: Yer arama servisine ulaşılamadı. Mevcut harita korundu; tekrar deneyin.')
    threading.Thread(target=work, daemon=True, name='jarvis-map-search').start()
    return 'Yer normal haritada aranıyor; birden fazla eşleşme varsa seçim gösterilecek.'
