# -*- coding: utf-8 -*-
"""Sentinel-1 GRD stand-ins for the coherence layer, sampled at the fixed Nebraska cropland pixels.

GRD products carry no phase, so interferometric coherence cannot be computed from them. Two
amplitude-based quantities are sampled instead, for the same 6,017 pixels and 13 weeks as
nebraska_2025_samples.csv:

  g_pipeline  the quantity computed by Till/detectTill.py: weekly mosaics of COPERNICUS/S1_GRD (VV, dB)
              of the previous and the current week, |<a b>| / sqrt(<a^2> <b^2>) in a 7 x 7 window;
  rho         local Pearson correlation of the VV backscatter (linear power, COPERNICUS/S1_GRD_FLOAT)
              between an acquisition of the week and the acquisition 12 days earlier on the same
              relative orbit, 9 x 9 window. For fully developed speckle the intensity correlation
              equals |coherence|^2, so  g_proxy = sqrt(max(rho, 0))  is an amplitude-based estimate
              of the coherence magnitude (biased by texture, e.g. at field edges);
  nc          the non-centred version of rho, for reference.

Output: <out>/s1_grd_samples.csv  (pid, week_end, g_pipeline, rho, nc)
Run   : conda run -n geo python sample_s1_grd.py --out ../output_grd
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import argparse
import datetime
import os
import time

import ee
import pandas as pd

ee.Initialize(project='ee-xwang')
PTS = _os.path.join(_DATA, 'nebraska_points.csv')
geom = ee.FeatureCollection('TIGER/2018/States').filter(ee.Filter.eq('NAME', 'Nebraska')).geometry()
EMPTY = ee.ImageCollection([ee.Image.constant(0).rename('VV').toFloat().updateMask(0)])


def retry(fn, tries=5):
    for k in range(tries):
        try:
            return fn()
        except Exception as e:
            print('   retry %d after: %s' % (k + 1, str(e)[:160]), flush=True)
            time.sleep(10 * (k + 1))
    raise RuntimeError('Earth Engine request failed repeatedly')


def s1(name, start, end):
    return (ee.ImageCollection(name).filterDate(start, end).filterBounds(geom)
            .filter(ee.Filter.eq('instrumentMode', 'IW'))
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')))


def local_mean(img, radius):
    return img.reduceNeighborhood(ee.Reducer.mean(), ee.Kernel.square(radius, 'pixels'))


def pipeline_quantity(start, end):
    prev = start - datetime.timedelta(days=7)
    a = s1('COPERNICUS/S1_GRD', prev.isoformat(), start.isoformat()).sort('system:time_start', False).select('VV').merge(EMPTY).mosaic()
    b = s1('COPERNICUS/S1_GRD', start.isoformat(), end.isoformat()).sort('system:time_start', False).select('VV').merge(EMPTY).mosaic()
    num = local_mean(a.multiply(b), 3).abs()
    den = local_mean(a.pow(2), 3).multiply(local_mean(b.pow(2), 3)).add(1e-10).sqrt()
    return num.divide(den).rename('g_pipeline')


def pair_correlation(start, end):
    early = start - datetime.timedelta(days=14)
    allc = s1('COPERNICUS/S1_GRD_FLOAT', early.isoformat(), end.isoformat())
    week = s1('COPERNICUS/S1_GRD_FLOAT', start.isoformat(), end.isoformat()).sort('system:time_start', False)

    def one(img):
        t = img.date()
        before = (allc.filter(ee.Filter.eq('relativeOrbitNumber_start', img.get('relativeOrbitNumber_start')))
                  .filterDate(t.advance(-12.5, 'day'), t.advance(-11.5, 'day')).filterBounds(img.geometry()).select('VV'))
        a = img.select('VV')
        b = before.merge(EMPTY).mosaic()
        a = a.updateMask(b.mask())
        ma, mb = local_mean(a, 4), local_mean(b, 4)
        mab, maa, mbb = local_mean(a.multiply(b), 4), local_mean(a.pow(2), 4), local_mean(b.pow(2), 4)
        var = maa.subtract(ma.pow(2)).multiply(mbb.subtract(mb.pow(2))).max(1e-30).sqrt()
        rho = mab.subtract(ma.multiply(mb)).divide(var).rename('rho')
        nc = mab.divide(maa.multiply(mbb).max(1e-30).sqrt()).rename('nc')
        return rho.addBands(nc).toFloat()

    empty2 = ee.ImageCollection([ee.Image.constant([0, 0]).rename(['rho', 'nc']).toFloat().updateMask(0)])
    return ee.ImageCollection(week.map(one)).merge(empty2).mosaic()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--weeks', default='', help='comma separated week-ending dates; default all 13')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, 's1_grd_samples.csv')
    pts = pd.read_csv(PTS)
    first_end = datetime.date(2025, 4, 6)
    weeks = [(first_end + datetime.timedelta(days=7 * k - 7), first_end + datetime.timedelta(days=7 * k)) for k in range(13)]
    if a.weeks:
        weeks = [w for w in weeks if w[1].isoformat() in a.weeks.split(',')]
    done = set(pd.read_csv(out, usecols=['week_end'])['week_end'].unique()) if os.path.exists(out) else set()
    for start, end in weeks:
        if end.isoformat() in done:
            continue
        img = pipeline_quantity(start, end).addBands(pair_correlation(start, end)).unmask(-9999)
        rows = []
        for i in range(0, len(pts), 1000):
            sub = pts.iloc[i:i + 1000]
            feats = [ee.Feature(ee.Geometry.Point([float(r.lon), float(r.lat)]), {'pid': int(r.pid)}) for r in sub.itertuples()]
            fc = img.sampleRegions(collection=ee.FeatureCollection(feats), scale=30, geometries=False)
            rows += [f['properties'] for f in retry(lambda: fc.getInfo())['features']]
        df = pd.DataFrame(rows).replace(-9999, float('nan'))
        df['week_end'] = end.isoformat()
        df[['pid', 'week_end', 'g_pipeline', 'rho', 'nc']].to_csv(out, mode='a', index=False, header=not os.path.exists(out))
        print('%s: %d pixels, g_pipeline available %.1f%%, pair available %.1f%%, median g_pipeline %.3f, median rho %.3f'
              % (end, len(df), 100 * df.g_pipeline.notna().mean(), 100 * df.rho.notna().mean(), df.g_pipeline.median(), df.rho.median()), flush=True)
    print('written', out)


if __name__ == '__main__':
    main()
