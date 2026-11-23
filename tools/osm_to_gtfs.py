# -*- coding: utf-8 -*-
"""Builds a GTFS zip for a city from OpenStreetMap public transport routes (Overpass API).

Use it where no official GTFS file can be fetched. What is REAL: stops, their names and places, route
numbers, route names, the order of stops. What is APPROXIMATE: times. OSM has no timetable, so every route
gets frequencies.txt (a vehicle every N minutes between the first and last hour) and stop times estimated
from distance and an average speed. The 'interval' tag of a route is used when OSM has it.

Usage: python osm_to_gtfs.py <slug> "<agency name>" <south> <west> <north> <east> <timezone> [<out dir>]
Example: python osm_to_gtfs.py dubai "Dubai public transport (OpenStreetMap)" 24.75 54.9 25.45 55.7 Asia/Dubai
Data: (c) OpenStreetMap contributors, ODbL 1.0 https://www.openstreetmap.org/copyright
"""
import csv
import io
import json
import math
import os
import re
import sys
import time
import zipfile

import requests

ENDPOINTS = ['https://overpass.openstreetmap.fr/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
UA = {'User-Agent': 'TransitBusTrainTime-datatool/1.0'}
# route_type, average km/h (including stops), default minutes between vehicles when OSM has no 'interval'
MODES = {'bus': (3, 20, 20), 'trolleybus': (3, 20, 20), 'minibus': (3, 20, 20), 'share_taxi': (3, 20, 20), 'tram': (0, 20, 8), 'light_rail': (0, 30, 8), 'subway': (1, 35, 6), 'monorail': (1, 35, 8),
         'train': (2, 50, 60), 'ferry': (4, 15, 30), 'funicular': (7, 15, 15)}
FIRST, LAST = '05:00:00', '24:00:00'


def overpass(query):
    last = ''
    for attempt in range(6):
        for ep in ENDPOINTS:
            try:
                r = requests.post(ep, data={'data': query}, headers=UA, timeout=200)
                if r.status_code == 200 and r.text.lstrip().startswith('{'):
                    return r.json()
                last = '%s %s' % (ep, r.status_code)
            except Exception as e:
                last = '%s %s' % (ep, str(e)[:60])
        time.sleep(20)
    raise RuntimeError('Overpass failed: ' + last)


def haversine(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(h)))


def minutes(tag):
    """OSM interval: '10', '00:10', '00:10:00', '5-10' -> minutes (int) or None."""
    if not tag:
        return None
    t = tag.strip()
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::\d{2})?', t)
    if m:
        v = int(m.group(1)) * 60 + int(m.group(2))
    else:
        nums = re.findall(r'\d+', t)
        if not nums:
            return None
        v = int(nums[0])
    return v if 1 <= v <= 240 else None


def hms(sec):
    sec = int(round(sec))
    return '%02d:%02d:%02d' % (sec // 3600, sec % 3600 // 60, sec % 60)


def build(slug, agency_name, bbox, tz, out_dir):
    s, w, n, e = bbox
    area = '(%s,%s,%s,%s)' % (s, w, n, e)
    modes = '|'.join(MODES)
    rels = overpass('[out:json][timeout:180];rel["type"="route"]["route"~"^(%s)$"]%s;out body;' % (modes, area))['elements']
    nodes_raw = overpass('[out:json][timeout:180];rel["type"="route"]["route"~"^(%s)$"]%s;node(r);out;' % (modes, area))['elements']
    nodes = {x['id']: x for x in nodes_raw if x['type'] == 'node' and s <= x['lat'] <= n and w <= x['lon'] <= e}
    print('relations', len(rels), 'nodes', len(nodes))

    stops, routes, trips, stop_times, freqs = {}, [], [], [], []
    used = set()
    for rel in rels:
        t = rel.get('tags', {})
        mode = t.get('route')
        rtype, speed, default_iv = MODES[mode]
        seq = []
        for m in rel.get('members', []):
            if m['type'] != 'node' or m['ref'] not in nodes:
                continue
            if not (m.get('role', '').startswith('stop') or m.get('role', '').startswith('platform')):
                continue
            if seq and seq[-1] == m['ref']:
                continue
            seq.append(m['ref'])
        # a stop and its platform are often both listed: keep the first of every close pair
        ordered = []
        for nid in seq:
            pt = (nodes[nid]['lat'], nodes[nid]['lon'])
            if ordered and haversine(pt, (nodes[ordered[-1]]['lat'], nodes[ordered[-1]]['lon'])) < 25:
                continue
            ordered.append(nid)
        if len(ordered) < 2:
            continue
        rid = 'osm%d' % rel['id']
        ref = t.get('ref', '')
        frm, to = t.get('from', ''), t.get('to', '')
        name = t.get('name') or ('%s - %s' % (frm, to) if frm and to else ref or rid)
        colour = (t.get('colour') or t.get('color') or '').lstrip('#')
        colour = colour.upper() if re.fullmatch(r'[0-9A-Fa-f]{6}', colour) else ''
        routes.append([rid, ref, name, rtype, colour])
        head = to or (name.split('-')[-1].strip() if '-' in name else name)
        trips.append([rid, 'ALL', rid + 't', head, 0])
        t0, prev = 0.0, None
        for i, nid in enumerate(ordered, 1):
            nd = nodes[nid]
            pt = (nd['lat'], nd['lon'])
            if prev is not None:
                t0 += haversine(prev, pt) * 1.3 / (speed * 1000 / 3600.0) + 20
            prev = pt
            sid = 'n%d' % nid
            if sid not in stops:
                tags = nd.get('tags', {})
                stops[sid] = [sid, tags.get('name') or tags.get('name:en') or tags.get('ref') or 'Stop %d' % nid, round(nd['lat'], 6), round(nd['lon'], 6)]
            used.add(sid)
            stop_times.append([rid + 't', hms(t0), hms(t0), sid, i])
        iv = minutes(t.get('interval')) or default_iv
        freqs.append([rid + 't', FIRST, LAST, iv * 60, 0])
    print('routes', len(routes), 'stops', len(used))
    if not routes:
        raise RuntimeError('no routes found in the area')

    def csvtext(header, rows):
        b = io.StringIO()
        wr = csv.writer(b, lineterminator='\n')
        wr.writerow(header)
        wr.writerows(rows)
        return b.getvalue()

    today = time.strftime('%Y%m%d')
    end = time.strftime('%Y%m%d', time.localtime(time.time() + 180 * 86400))
    files = {
        'agency.txt': csvtext(['agency_id', 'agency_name', 'agency_url', 'agency_timezone'], [['osm', agency_name, 'https://www.openstreetmap.org/copyright', tz]]),
        'stops.txt': csvtext(['stop_id', 'stop_name', 'stop_lat', 'stop_lon'], [v for k, v in stops.items() if k in used]),
        'routes.txt': csvtext(['route_id', 'agency_id', 'route_short_name', 'route_long_name', 'route_type', 'route_color'], [[r[0], 'osm', r[1], r[2], r[3], r[4]] for r in routes]),
        'trips.txt': csvtext(['route_id', 'service_id', 'trip_id', 'trip_headsign', 'direction_id'], trips),
        'stop_times.txt': csvtext(['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'], stop_times),
        'frequencies.txt': csvtext(['trip_id', 'start_time', 'end_time', 'headway_secs', 'exact_times'], freqs),
        'calendar.txt': csvtext(['service_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_date', 'end_date'], [['ALL', 1, 1, 1, 1, 1, 1, 1, today, end]]),
        'feed_info.txt': csvtext(['feed_publisher_name', 'feed_publisher_url', 'feed_lang', 'feed_version'], [['OpenStreetMap contributors (ODbL), times approximate', 'https://www.openstreetmap.org/copyright', 'en', today]]),
    }
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug + '.zip')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text)
    lats = sorted(v[2] for k, v in stops.items() if k in used)
    lons = sorted(v[3] for k, v in stops.items() if k in used)
    info = {'slug': slug, 'agency': agency_name, 'tz': tz, 'routes': len(routes), 'stops': len(used), 'bb': [lats[0], lats[-1], lons[0], lons[-1]], 'built': today, 'valid_until': end}
    json.dump(info, open(os.path.join(out_dir, slug + '.json'), 'w', encoding='utf-8'), indent=1)
    print(info)
    return info


if __name__ == '__main__':
    a = sys.argv
    out = a[8] if len(a) > 8 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'feeds')
    build(a[1], a[2], [float(x) for x in a[3:7]], a[7], out)
