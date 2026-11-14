"""Driving routes drawn on the native map; no live traffic claims."""
import json
import math
import os
import threading
from urllib.request import Request, urlopen
from plugins.normal_map import search

PLUGIN = {'name':'map_route', 'description':'Draw a driving route between two explicit places on the normal map INSIDE JARVIS. Ask for origin when missing; never use approximate IP location as a precise start. Not live traffic or turn-by-turn navigation. Use for rota oluştur/yol tarifi.', 'parameters':{'type':'OBJECT','properties':{'origin':{'type':'STRING'},'destination':{'type':'STRING'}},'required':['origin','destination']}}


def route(start, end):
    coords = f"{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
    endpoint = os.environ.get('JARVIS_ROUTER_URL', 'https://router.project-osrm.org').rstrip('/')
    req = Request(endpoint+'/route/v1/driving/'+coords+'?overview=full&geometries=geojson', headers={'User-Agent':'JarvisPersonalMap/1.0'})
    with urlopen(req, timeout=20) as response:
        data=json.loads(response.read(4000000))
    if data.get('code') != 'Ok' or not data.get('routes'):
        raise ValueError('Bu iki yer arasında araç rotası bulunamadı.')
    result=data['routes'][0]
    points=result['geometry']['coordinates']
    if not 2 <= len(points) <= 100000:
        raise ValueError('Rota geometrisi geçersiz.')
    for lon, lat in points:
        if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('Rota koordinatları geçersiz.')
    distance,duration=float(result['distance']),float(result['duration'])
    if not all(math.isfinite(v) and v>=0 for v in (distance,duration)):
        raise ValueError('Rota ölçüleri geçersiz.')
    return {'points':points,'distance':distance,'duration':duration,'title':start['name']+' → '+end['name']}


def run(parameters, player=None, session_memory=None):
    origin=str(parameters.get('origin','')).strip()
    destination=str(parameters.get('destination','')).strip()
    if not origin or not destination or max(len(origin),len(destination))>500:
        return 'Başlangıç ve varış yerini şehir/ülke bilgisiyle söyleyin.'
    if not callable(getattr(player,'show_route_choices',None)):
        return 'Rota için JARVIS arayüzü açık olmalı.'
    def work():
        try:
            start,end=search(origin),search(destination)
            if not start or not end:
                player.write_log('ROTA: Başlangıç veya varış bulunamadı. Adresi netleştirin.')
                return
            player.show_route_choices({'start':start,'end':end})
        except Exception:
            player.write_log('ROTA: Yer araması başarısız; bağlantıyı kontrol edin.')
    threading.Thread(target=work,daemon=True).start()
    return 'Başlangıç ve varış aranıyor; rota normal haritada gösterilecek. Süre canlı trafik içermez.'
