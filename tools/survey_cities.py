# -*- coding: utf-8 -*-
"""Counts OSM public transport route relations around candidate cities, to see where osm_to_gtfs.py is worth running.
Writes ../survey.json (city -> routes, with stops) and prints a table."""
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_to_gtfs import ENDPOINTS, MODES, UA  # noqa: E402

CITIES = [
    ('SE', 'stockholm', 'Stockholm', 59.33, 18.07, 'Europe/Stockholm'), ('SE', 'gothenburg', 'Gothenburg', 57.71, 11.97, 'Europe/Stockholm'), ('SE', 'malmo', 'Malmö', 55.6, 13.0, 'Europe/Stockholm'),
    ('GR', 'athens', 'Athens', 37.98, 23.73, 'Europe/Athens'), ('GR', 'thessaloniki', 'Thessaloniki', 40.64, 22.94, 'Europe/Athens'),
    ('MT', 'malta', 'Malta', 35.95, 14.4, 'Europe/Malta'), ('QA', 'doha', 'Doha', 25.29, 51.53, 'Asia/Qatar'),
    ('SA', 'riyadh', 'Riyadh', 24.7, 46.7, 'Asia/Riyadh'), ('SA', 'jeddah', 'Jeddah', 21.5, 39.2, 'Asia/Riyadh'),
    ('VN', 'hanoi', 'Hanoi', 21.03, 105.85, 'Asia/Ho_Chi_Minh'), ('VN', 'ho-chi-minh', 'Ho Chi Minh City', 10.78, 106.7, 'Asia/Ho_Chi_Minh'), ('VN', 'da-nang', 'Da Nang', 16.05, 108.2, 'Asia/Ho_Chi_Minh'),
    ('PH', 'manila', 'Manila', 14.6, 121.0, 'Asia/Manila'), ('PH', 'cebu', 'Cebu', 10.3, 123.9, 'Asia/Manila'),
    ('TW', 'taipei', 'Taipei', 25.04, 121.55, 'Asia/Taipei'), ('TW', 'kaohsiung', 'Kaohsiung', 22.63, 120.3, 'Asia/Taipei'), ('TW', 'taichung', 'Taichung', 24.15, 120.67, 'Asia/Taipei'),
    ('AR', 'buenos-aires', 'Buenos Aires', -34.6, -58.45, 'America/Argentina/Buenos_Aires'), ('AR', 'cordoba', 'Córdoba', -31.4, -64.2, 'America/Argentina/Cordoba'),
    ('RU', 'moscow', 'Moscow', 55.75, 37.6, 'Europe/Moscow'), ('RU', 'saint-petersburg', 'Saint Petersburg', 59.93, 30.3, 'Europe/Moscow'),
    ('KE', 'nairobi', 'Nairobi', -1.29, 36.82, 'Africa/Nairobi'), ('DO', 'santo-domingo', 'Santo Domingo', 18.48, -69.9, 'America/Santo_Domingo'),
    ('GT', 'guatemala-city', 'Guatemala City', 14.63, -90.5, 'America/Guatemala'), ('SV', 'san-salvador', 'San Salvador', 13.69, -89.19, 'America/El_Salvador'),
    ('PA', 'panama-city', 'Panama City', 8.98, -79.52, 'America/Panama'), ('PY', 'asuncion', 'Asunción', -25.28, -57.63, 'America/Asuncion'),
    ('VE', 'caracas', 'Caracas', 10.5, -66.9, 'America/Caracas'), ('NI', 'managua', 'Managua', 12.13, -86.27, 'America/Managua'),
    ('SN', 'dakar', 'Dakar', 14.7, -17.45, 'Africa/Dakar'), ('MG', 'antananarivo', 'Antananarivo', -18.9, 47.5, 'Indian/Antananarivo'),
    ('CD', 'kinshasa', 'Kinshasa', -4.32, 15.31, 'Africa/Kinshasa'), ('BF', 'ouagadougou', 'Ouagadougou', 12.37, -1.52, 'Africa/Ouagadougou'),
    ('CV', 'praia', 'Praia', 14.93, -23.51, 'Atlantic/Cape_Verde'), ('UZ', 'tashkent', 'Tashkent', 41.3, 69.27, 'Asia/Tashkent'),
    ('BH', 'manama', 'Manama', 26.22, 50.58, 'Asia/Bahrain'), ('OM', 'muscat', 'Muscat', 23.59, 58.4, 'Asia/Muscat'),
    ('AD', 'andorra', 'Andorra', 42.5, 1.52, 'Europe/Andorra'), ('LI', 'vaduz', 'Liechtenstein', 47.14, 9.52, 'Europe/Vaduz'),
    ('MO', 'macau', 'Macau', 22.2, 113.55, 'Asia/Macau'), ('BN', 'bandar-seri-begawan', 'Bandar Seri Begawan', 4.9, 114.93, 'Asia/Brunei'),
    ('BB', 'barbados', 'Barbados', 13.1, -59.6, 'America/Barbados'), ('SR', 'paramaribo', 'Paramaribo', 5.85, -55.2, 'America/Paramaribo'),
    ('PR', 'san-juan', 'San Juan', 18.45, -66.1, 'America/Puerto_Rico'), ('GF', 'cayenne', 'Cayenne', 4.93, -52.33, 'America/Cayenne'),
    ('NC', 'noumea', 'Nouméa', -22.27, 166.45, 'Pacific/Noumea'), ('VI', 'charlotte-amalie', 'Charlotte Amalie', 18.34, -64.93, 'America/St_Thomas'),
    ('SI', 'maribor', 'Maribor', 46.55, 15.65, 'Europe/Ljubljana'), ('AE', 'sharjah', 'Sharjah', 25.35, 55.4, 'Asia/Dubai'),
    ('IL', 'tel-aviv', 'Tel Aviv', 32.08, 34.78, 'Asia/Jerusalem'), ('HK', 'hong-kong', 'Hong Kong', 22.3, 114.17, 'Asia/Hong_Kong'),
]
H = 0.15


def count(lat, lon):
    modes = '|'.join(MODES)
    q = '[out:json][timeout:90];rel["type"="route"]["route"~"^(%s)$"](%s,%s,%s,%s);out count;' % (modes, lat - H, lon - H, lat + H, lon + H)
    for ep in ENDPOINTS[:2]:
        try:
            r = requests.post(ep, data={'data': q}, headers=UA, timeout=100)
            if r.status_code == 200 and r.text.lstrip().startswith('{'):
                return int(r.json()['elements'][0]['tags']['relations'])
        except Exception:
            pass
        time.sleep(3)
    return -1


if __name__ == '__main__':
    out = {}
    for cc, slug, name, lat, lon, tz in CITIES:
        n = count(lat, lon)
        out[slug] = {'cc': cc, 'name': name, 'lat': lat, 'lon': lon, 'tz': tz, 'routes': n}
        print('%s %-20s %d' % (cc, name, n), flush=True)
        time.sleep(1.5)
    json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'survey.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('SURVEY DONE', flush=True)
