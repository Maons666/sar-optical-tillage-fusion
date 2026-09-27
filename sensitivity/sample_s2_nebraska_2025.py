# -*- coding: utf-8 -*-
"""B4, step 1: sample the application domain -- Nebraska corn/soybean cropland, spring 2025.

* points : random 30 m pixels of CDL 2024 corn (1) or soybean (5) inside Nebraska, fixed seeds,
           the same pixels are revisited every week;
* weeks  : the thirteen 7-day windows of the statewide product (2025-03-30 ... 2025-06-29);
* inputs : rebuilt exactly as Till/getStateS12.py does for the statewide maps --
           COPERNICUS/S2_SR_HARMONIZED, filterDate(start, end), sorted newest first, mosaic(),
           bands B2 B3 B4 B8 B11 B12 + SCL, sampled at 30 m (EPSG:4326 grid, as the exports).
Output   : data/nebraska_2025_samples.csv  (one row per pixel and week)

Run:  conda run -n geo python sensitivity/sample_s2_nebraska_2025.py
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import datetime
import os
import time

import ee
import pandas as pd

ee.Initialize(project='ee-xwang')
OUT = _os.path.join(_DATA, 'nebraska_2025_samples.csv')
PTS = _os.path.join(_DATA, 'nebraska_points.csv')

aoi = ee.FeatureCollection('TIGER/2018/States').filter(ee.Filter.eq('NAME', 'Nebraska'))
geom = aoi.geometry()
cdl = ee.Image('USDA/NASS/CDL/2024').select('cropland')
crop = cdl.updateMask(cdl.eq(1).Or(cdl.eq(5)))


def retry(fn, tries=4):
    for k in range(tries):
        try:
            return fn()
        except Exception as e:
            print('   retry %d after: %s' % (k + 1, str(e)[:120]), flush=True)
            time.sleep(8 * (k + 1))
    raise RuntimeError('Earth Engine request failed repeatedly')


# ------------------------------------------------------------------ 1. fixed cropland pixels
if os.path.exists(PTS):
    pts = pd.read_csv(PTS)
else:
    # Random points are drawn locally, uniformly in the equal-area projection EPSG:5070, inside the
    # bounding box of Nebraska; Earth Engine then only has to return the CDL class at each point.
    # (Letting Earth Engine draw the sample over the whole state at 30 m does not finish.)
    import numpy as np
    from pyproj import Transformer
    rng = np.random.RandomState(42)
    to5070 = Transformer.from_crs(4326, 5070, always_xy=True)
    to4326 = Transformer.from_crs(5070, 4326, always_xy=True)
    xs, ys = to5070.transform([-104.06, -95.30, -104.06, -95.30], [39.99, 39.99, 43.01, 43.01])
    px = rng.uniform(min(xs), max(xs), 26000)
    py = rng.uniform(min(ys), max(ys), 26000)
    lon, lat = to4326.transform(px, py)
    rows = []
    for i in range(0, len(lon), 2000):
        feats = [ee.Feature(ee.Geometry.Point([float(x), float(y)])) for x, y in zip(lon[i:i + 2000], lat[i:i + 2000])]
        fc = crop.sampleRegions(collection=ee.FeatureCollection(feats).filterBounds(geom), scale=30, geometries=True)
        info = retry(lambda: fc.getInfo())
        for f in info['features']:
            x, y = f['geometry']['coordinates']
            rows.append({'lon': x, 'lat': y, 'crop': int(f['properties']['cropland'])})
        print('points %d-%d -> %d cropland pixels so far' % (i, i + 2000, len(rows)), flush=True)
    pts = pd.DataFrame(rows).drop_duplicates(['lon', 'lat']).reset_index(drop=True)
    pts.insert(0, 'pid', range(len(pts)))
    pts.to_csv(PTS, index=False)
print('cropland pixels: %d (corn %d, soybean %d)' % (len(pts), (pts.crop == 1).sum(), (pts.crop == 5).sum()), flush=True)

# ------------------------------------------------------------------ 2. weekly inputs
first_end = datetime.date(2025, 4, 6)
weeks = [(first_end + datetime.timedelta(days=7 * k - 7), first_end + datetime.timedelta(days=7 * k)) for k in range(13)]
done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT, usecols=['week_end'])['week_end'].unique())
CHUNK = 1500
for start, end in weeks:
    if end.isoformat() in done:
        continue
    col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(start.isoformat(), end.isoformat())
           .filterBounds(geom).sort('system:time_start', False))
    img = col.mosaic().select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'SCL'])
    rows = []
    for i in range(0, len(pts), CHUNK):
        sub = pts.iloc[i:i + CHUNK]
        feats = [ee.Feature(ee.Geometry.Point([float(r.lon), float(r.lat)]), {'pid': int(r.pid)}) for r in sub.itertuples()]
        fc = img.sampleRegions(collection=ee.FeatureCollection(feats), scale=30, geometries=False)
        info = retry(lambda: fc.getInfo())
        rows += [f['properties'] for f in info['features']]
    df = pd.DataFrame(rows)
    df['week_start'] = start.isoformat()
    df['week_end'] = end.isoformat()
    df = df.merge(pts[['pid', 'crop', 'lon', 'lat']], on='pid', how='left')
    df.to_csv(OUT, mode='a', index=False, header=not os.path.exists(OUT))
    print('%s -> %s : %d pixels with data, cloud (SCL 8-10) %.1f%%'
          % (start, end, len(df), 100.0 * df['SCL'].isin([8, 9, 10]).mean() if len(df) else 0), flush=True)
print('written', OUT)
