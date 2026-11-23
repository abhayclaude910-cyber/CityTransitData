# -*- coding: utf-8 -*-
"""Builds an OSM feed for every surveyed city with enough routes. Run after survey_cities.py."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from osm_to_gtfs import build  # noqa: E402

ROOT = os.path.dirname(HERE)
survey = json.load(open(os.path.join(ROOT, 'survey.json'), encoding='utf-8'))
SKIP = {'hong-kong', 'tel-aviv', 'sharjah', 'doha', 'riyadh', 'jeddah', 'manama', 'paramaribo', 'charlotte-amalie', 'muscat'}
CUSTOM = {'malta': (35.78, 14.15, 36.1, 14.6)}
MIN = 40
H = 0.15
done, failed = [], []
for slug, c in survey.items():
    if slug in SKIP or c['routes'] < MIN:
        continue
    out = os.path.join(ROOT, 'feeds')
    if os.path.exists(os.path.join(out, slug + '.zip')):
        continue
    bbox = CUSTOM.get(slug) or (c['lat'] - H, c['lon'] - H, c['lat'] + H, c['lon'] + H)
    try:
        info = build(slug, '%s public transport (OpenStreetMap, approximate times)' % c['name'], bbox, c['tz'], out)
        info['cc'] = c['cc']
        info['city'] = c['name']
        json.dump(info, open(os.path.join(out, slug + '.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        done.append(slug)
    except Exception as e:
        print('FAILED', slug, str(e)[:100], flush=True)
        failed.append(slug)
    time.sleep(5)
print('BUILD DONE', len(done), 'built', len(failed), 'failed', flush=True)
