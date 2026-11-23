# CityTransit open data feeds (built by us, for places with no downloadable official feed)

GTFS zips made from OpenStreetMap route relations by `tools/osm_to_gtfs.py`.

## What is real and what is approximate
- **Real (from OpenStreetMap):** stop positions and names, route numbers and names, the order of stops on each route.
- **Approximate:** all times. OSM has no timetable. Each route runs every N minutes between 05:00 and 24:00 (`frequencies.txt`; N is the route's `interval` tag when OSM has one, else bus 20, tram and light rail 8, metro 6, ferry 30, train 60). Stop times are estimated from distance at an average speed.
- **Coverage is only as good as OSM:** today Dubai has 52 routes and 652 stops, Abu Dhabi 7 routes and 107 stops (the real networks are bigger). Better data from the agency replaces these files as soon as we get it.
- The agency name of each feed says "OpenStreetMap, approximate times" so the app never presents it as an official timetable.

## Licence
Data (c) OpenStreetMap contributors, Open Database Licence 1.0: https://www.openstreetmap.org/copyright . Our derived feeds must stay under ODbL and show this credit (the app's About/credits screen should name OpenStreetMap). The scripts in `tools/` are ours.

## Hosting (needs a PUBLIC repo)
The app downloads feeds with a plain GET. `ClaudeProjects` is private, so a raw link would answer 404. Create a public repo (for example `CityTransitData`), push the `feeds/` folder to it, and the fetch address is:

`https://raw.githubusercontent.com/<user>/<repo>/main/feeds/<slug>.zip`

Then add an entry to `Transit_Bus_v1/assets/data/agencies.json` with `"static"` set to that address, `"vp"`, `"tu"`, `"sa"` empty and `"bb"`/`"tz"` from `feeds/<slug>.json`. (Hong Kong's official feed uses the same frequencies layout; the app now reads it.)

## Make another city
```
python tools/osm_to_gtfs.py <slug> "<City public transport (OpenStreetMap, approximate times)>" <south> <west> <north> <east> <timezone>
```
Needs the internet (uses Overpass mirrors; overpass.openstreetmap.fr worked best). Takes about a minute. Output: `feeds/<slug>.zip` and `feeds/<slug>.json`. Rebuild every few months (calendar runs 180 days).

## Built so far
| Slug | City | Country | Routes | Stops |
|---|---|---|---|---|
| andorra | Andorra | AD | 47 | 253 |
| abu-dhabi | Abu Dhabi | AE | 7 | 107 |
| dubai | Dubai | AE | 52 | 652 |
| buenos-aires | Buenos Aires | AR | 1114 | 13162 |
| cordoba | Córdoba | AR | 289 | 5871 |
| ouagadougou | Ouagadougou | BF | 59 | 666 |
| bandar-seri-begawan | Bandar Seri Begawan | BN | 7 | 10 |
| athens | Athens | GR | 451 | 8286 |
| thessaloniki | Thessaloniki | GR | 185 | 1960 |
| nairobi | Nairobi | KE | 17 | 118 |
| vaduz | Liechtenstein | LI | 285 | 1042 |
| antananarivo | Antananarivo | MG | 101 | 848 |
| macau | Macau | MO | 368 | 1963 |
| malta | Malta | MT | 317 | 2318 |
| noumea | Nouméa | NC | 36 | 750 |
| managua | Managua | NI | 110 | 1416 |
| panama-city | Panama City | PA | 34 | 436 |
| cebu | Cebu | PH | 89 | 593 |
| manila | Manila | PH | 449 | 3064 |
| san-juan | San Juan | PR | 9 | 94 |
| moscow | Moscow | RU | 1870 | 8122 |
| saint-petersburg | Saint Petersburg | RU | 1011 | 4494 |
| gothenburg | Gothenburg | SE | 283 | 1902 |
| malmo | Malmö | SE | 126 | 898 |
| stockholm | Stockholm | SE | 1027 | 3714 |
| maribor | Maribor | SI | 62 | 482 |
| kaohsiung | Kaohsiung | TW | 363 | 3559 |
| taichung | Taichung | TW | 716 | 5924 |
| taipei | Taipei | TW | 1319 | 6744 |
| tashkent | Tashkent | UZ | 125 | 1866 |
| caracas | Caracas | VE | 63 | 620 |
| hanoi | Hanoi | VN | 344 | 2749 |
| ho-chi-minh | Ho Chi Minh City | VN | 272 | 4263 |

Cities with fewer than 20 usable routes (Bandar Seri Begawan, San Juan, Nairobi) are built but not added to the app. Doha, Riyadh, Jeddah, Muscat, Manama, Paramaribo and Charlotte Amalie had too little OSM data to build. Asuncion and Praia had no usable routes.
