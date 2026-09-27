"""
B3 — Sentinel-2 / Sentinel-1 weekly cropland coverage over Nebraska, aligned to
the USDA NASS reporting week (Monday–Sunday), 31 Mar – 29 Jun 2025 (13 weeks).

Same definitions as gee_coverage_analysis.js (§4.5):
  * cropland = CDL 2024 corn (1) + soybean (5)
  * S2 usable  = at least one SCL-clear (4,5,6,7,11) observation in the week
  * S1 present = at least one IW/VV GRD acquisition in the week (proxy for SAR availability)
  * fused      = S2 usable OR S1 present
  * '.unmask(0)' so that pixels with no observation count as 0, not as masked

Extra: for two 14-day windows in the second half of May, the share of cropland
with 0 / exactly 1 / >= 2 clear Sentinel-2 observations.

Run (needs the geo env for the EE credentials):
"""
import csv, datetime, os, sys, time
import ee

ee.Initialize(project='ee-xwang')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'data', 'B3_gee_weekly_coverage_nass_aligned.csv')
OUT2 = os.path.join(ROOT, 'data', 'B3_gee_clear_obs_histogram.csv')

aoi = ee.FeatureCollection('TIGER/2018/States').filter(ee.Filter.eq('NAME', 'Nebraska'))
geom = aoi.geometry()
cdl = ee.Image('USDA/NASS/CDL/2024').select('cropland')
crop = cdl.eq(1).Or(cdl.eq(5)).selfMask()

RED = dict(reducer=ee.Reducer.mean(), geometry=geom, scale=500, tileScale=8, maxPixels=1e10, bestEffort=True)


def s2_clear(start, end):
    def m(img):
        scl = img.select('SCL')
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7)).Or(scl.eq(11))
        return img.updateMask(clear).select('B4').copyProperties(img, ['system:time_start'])
    col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(geom)
           .filterDate(start, end).map(m))
    # a fully masked dummy guarantees count() has a 'B4' band even for an empty week
    dummy = ee.ImageCollection([ee.Image(0).uint16().selfMask().rename('B4')])
    return col.merge(dummy)


def s1_any(start, end):
    col = (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(geom).filterDate(start, end)
           .filter(ee.Filter.eq('instrumentMode', 'IW'))
           .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')).select('VV'))
    dummy = ee.ImageCollection([ee.Image(0).float().selfMask().rename('VV')])
    return col.merge(dummy)


def week_stats(start, end):
    s2cnt = s2_clear(start, end).count().unmask(0).rename('s2_clear_count')
    s2has = s2cnt.gt(0).rename('s2_has')
    s1has = s1_any(start, end).count().unmask(0).gt(0).rename('s1_has')
    fused = s2has.Or(s1has).rename('fused_has')
    img = ee.Image.cat([s2has, s2cnt, s1has, fused]).updateMask(crop)
    return img.reduceRegion(**RED).getInfo()


def clear_hist(start, end):
    cnt = s2_clear(start, end).count().unmask(0)
    img = ee.Image.cat([cnt.eq(0).rename('f_zero'), cnt.eq(1).rename('f_one'),
                        cnt.gte(2).rename('f_two_plus')]).updateMask(crop)
    return img.reduceRegion(**RED).getInfo()


def retry(fn, *a, n=4):
    for k in range(n):
        try:
            return fn(*a)
        except Exception as e:                     # noqa: BLE001
            print(f'    attempt {k+1} failed: {str(e)[:160]}', flush=True)
            time.sleep(8 * (k + 1))
    return None


# ---- 13 NASS weeks: Monday .. Sunday, week ending 6 Apr .. 29 Jun 2025 ----
first_sunday = datetime.date(2025, 4, 6)
with open(OUT, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['week_start_mon', 'week_ending_sun', 's2_usable_pct', 's2_mean_clear_obs',
                's1_present_pct', 'fused_pct'])
    for k in range(13):
        sun = first_sunday + datetime.timedelta(days=7 * k)
        mon = sun - datetime.timedelta(days=6)
        start, end = mon.isoformat(), (sun + datetime.timedelta(days=1)).isoformat()   # end exclusive
        t0 = time.time()
        r = retry(week_stats, start, end)
        if r is None:
            w.writerow([mon, sun, '', '', '', '']); fh.flush(); continue
        row = [mon.isoformat(), sun.isoformat(),
               f"{100*r['s2_has']:.2f}", f"{r['s2_clear_count']:.3f}",
               f"{100*r['s1_has']:.2f}", f"{100*r['fused_has']:.2f}"]
        w.writerow(row); fh.flush()
        print(f'  week ending {sun}:  S2 {row[2]}%  (mean clear obs {row[3]})   S1 {row[4]}%   fused {row[5]}%'
              f'   [{time.time()-t0:.0f}s]', flush=True)
print('wrote', OUT, flush=True)

# ---- clear-observation histogram for the cloudy fortnights ----
with open(OUT2, 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['window_start', 'window_end_inclusive', 'pct_zero_clear_obs', 'pct_one_clear_obs', 'pct_two_plus'])
    for a, b in [('2025-05-12', '2025-05-25'), ('2025-05-19', '2025-06-01'),
                 ('2025-04-14', '2025-04-27'), ('2025-04-28', '2025-05-11')]:
        end_excl = (datetime.date.fromisoformat(b) + datetime.timedelta(days=1)).isoformat()
        r = retry(clear_hist, a, end_excl)
        if r is None:
            continue
        w.writerow([a, b, f"{100*r['f_zero']:.2f}", f"{100*r['f_one']:.2f}", f"{100*r['f_two_plus']:.2f}"]); fh.flush()
        print(f'  {a}..{b}:  zero {100*r["f_zero"]:.1f}%   one {100*r["f_one"]:.1f}%   two+ {100*r["f_two_plus"]:.1f}%', flush=True)
print('wrote', OUT2, flush=True)
