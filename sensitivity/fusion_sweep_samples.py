# -*- coding: utf-8 -*-
"""Threshold sweep and rule accounting of the fusion logic on the fixed Nebraska cropland pixels,
with a Sentinel-1 GRD quantity standing in for the coherence layer.

Inputs : data/nebraska_2025_samples.csv   Sentinel-2 bands + SCL, 6,017 pixels x 13 weeks
         <grd>/s1_grd_samples.csv                            written by sample_s1_grd.py
Output : <out>/rule_shares_<MMDD>.csv   same columns as fusion_sweep.py plus
             pct_no_observation  cloud pixels without a Sentinel-1 value (share of ALL pixels; no decision)
             pct_tilled_cum      pixels labelled Tilled in this or any earlier week (share of all pixels)
         <out>/coherence_standin_summary.csv   distribution of the stand-in per week

Rules (manuscript, fusion section):
  1  SCL cloud                                              -> Tilled if g < gamma_low, else Untilled
  2  clear, p_max < T, optical Untilled, g < gamma_low      -> Tilled
  3  clear, p_max < T, optical Tilled,   g > gamma_high     -> Untilled
  otherwise the optical label is kept. Shares are relative to the pixels that receive a decision.

Usage: conda run -n geo python fusion_sweep_samples.py --grd ../output_grd --out ../output_grd/proxy_fitted
           --standin proxy --feature-order fitted
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import argparse
import itertools
import os

import joblib
import numpy as np
import pandas as pd

ROOT = _REPO
APP = _os.path.join(_DATA, 'nebraska_2025_samples.csv')
PKL = _os.path.join(_MODELS, 'tillage_classifier.pkl')
PIPELINE_ORDER = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'NDSI', 'BSI', 'NDBSI', 'NDTI']
TS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
GL = [0.15, 0.20, 0.25, 0.30, 0.35]
GH = [0.50, 0.55, 0.60, 0.65, 0.70]


def add_indices(d):
    eps = 1e-10
    b2, b3, b4, b8, b11, b12 = [d[k].astype('float64') for k in ('B2', 'B3', 'B4', 'B8', 'B11', 'B12')]
    d['NDVI'] = (b8 - b4) / (b8 + b4 + eps)
    d['NDSI'] = (b3 - b11) / (b3 + b11 + eps)
    d['BSI'] = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + eps)
    d['NDBSI'] = (d['BSI'] - d['NDVI']) / (d['BSI'] + d['NDVI'] + eps)
    d['NDTI'] = (b11 - b12) / (b11 + b12 + eps)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grd', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--standin', choices=['proxy', 'pipeline'], default='proxy',
                    help='proxy = sqrt(max(rho,0)) from same-orbit 12-day pairs; pipeline = quantity of detectTill.py')
    ap.add_argument('--feature-order', choices=['fitted', 'pipeline'], default='fitted')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    clf = joblib.load(PKL)
    cols = list(clf.feature_names_in_) if a.feature_order == 'fitted' else PIPELINE_ORDER
    d = add_indices(pd.read_csv(APP))
    s = pd.read_csv(os.path.join(a.grd, 's1_grd_samples.csv')).drop_duplicates(['pid', 'week_end'])
    d = d.merge(s, on=['pid', 'week_end'], how='left')
    d['g'] = np.sqrt(d.rho.clip(lower=0)) if a.standin == 'proxy' else d.g_pipeline
    p = clf.predict_proba(np.nan_to_num(d[cols].values.astype(float)))
    d['pmax'] = p.max(1)
    d['opt'] = (p.argmax(1) == list(clf.classes_).index(1)).astype(int)
    d['cloud'] = d.SCL.isin([8, 9, 10])
    n_pix = d.pid.nunique()
    weeks = sorted(d.week_end.unique())

    summ = []
    for w in weeks:
        g = d[d.week_end == w]
        v = g.g.dropna()
        summ.append({'week_end': w, 'pct_with_value': 100 * g.g.notna().mean(), 'median': v.median(), 'p10': v.quantile(0.1),
                     'p90': v.quantile(0.9), 'pct_below_0.25': 100 * (v < 0.25).mean(), 'pct_above_0.60': 100 * (v > 0.60).mean()})
    summ = pd.DataFrame(summ)
    summ.to_csv(os.path.join(a.out, 'coherence_standin_summary.csv'), index=False, float_format='%.3f')
    print(summ.to_string(index=False, float_format=lambda x: '%.3f' % x))

    combos = list(itertools.product(TS, GL, GH))
    ever = {c: set() for c in combos}
    rows = {w: [] for w in weeks}
    for w in weeks:
        g = d[d.week_end == w]
        pid, cloud, has = g.pid.values, g.cloud.values, g.g.notna().values
        gv, pmax, opt = g.g.fillna(-1).values, g.pmax.values, g.opt.values
        decided = ~cloud | has
        n = max(int(decided.sum()), 1)
        for c in combos:
            T, gl, gh = c
            low = ~cloud & (pmax < T) & has
            r1 = cloud & has
            r2 = low & (opt == 0) & (gv < gl)
            r3 = low & (opt == 1) & (gv > gh)
            final = opt.copy()
            final[r1] = (gv[r1] < gl).astype(int)
            final[r2] = 1
            final[r3] = 0
            tilled = decided & (final == 1)
            ever[c].update(pid[tilled].tolist())
            rows[w].append([w[5:7] + w[8:10], T, gl, gh, n, 100.0 * r1.sum() / n, 100.0 * r2.sum() / n, 100.0 * r3.sum() / n,
                            100.0 * (decided & ~r1 & ~r2 & ~r3).sum() / n, 100.0 * tilled.sum() / n,
                            100.0 * (~decided).sum() / len(g), 100.0 * len(ever[c]) / n_pix])
    names = ['tag', 'T', 'gamma_low', 'gamma_high', 'n_valid', 'pct_cloud_override', 'pct_enhance', 'pct_stability',
             'pct_optical_accepted', 'pct_tilled_pixel', 'pct_no_observation', 'pct_tilled_cum']
    base = []
    for w in weeks:
        df = pd.DataFrame(rows[w], columns=names)
        df.to_csv(os.path.join(a.out, 'rule_shares_%s.csv' % df.tag.iloc[0]), index=False, float_format='%.3f')
        base.append(df[(df['T'] == 0.65) & (df.gamma_low == 0.25) & (df.gamma_high == 0.60)])
    print(pd.concat(base).to_string(index=False, float_format=lambda x: '%.2f' % x))


if __name__ == '__main__':
    main()
