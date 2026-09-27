# -*- coding: utf-8 -*-
"""What can be said about the fusion routing WITHOUT any coherence data.

Input : data/nebraska_2025_samples.csv  (6,017 fixed random corn/soybean pixels of
        Nebraska, 13 weekly Sentinel-2 mosaics of spring 2025, bands + SCL) and the deployed classifier.
Output: <out>/routing_by_week_<order>.csv   share of pixels per week that are
            cloud (SCL 8-10)                     -> rule 1 would decide
            clear, p_max >= T                    -> optical accepted
            clear, p_max <  T, optical Untilled  -> candidate for rule 2 (fires only if gamma < gamma_low)
            clear, p_max <  T, optical Tilled    -> candidate for rule 3 (fires only if gamma > gamma_high)
        <out>/gate_sweep_target_<order>.csv  the same four shares pooled over all weeks for T = 0.50 ... 0.90
The two candidate shares are UPPER BOUNDS of the rule 2 and rule 3 shares; which of the candidates the
rules actually change cannot be known without coherence.

Usage: conda run -n geo python routing_without_slc.py --out ../output_no_slc
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import argparse
import os

import joblib
import numpy as np
import pandas as pd

ROOT = _REPO
APP = _os.path.join(_DATA, 'nebraska_2025_samples.csv')
PKL = _os.path.join(_MODELS, 'tillage_classifier.pkl')
PIPELINE_ORDER = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'NDSI', 'BSI', 'NDBSI', 'NDTI']
GATES = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]


def add_indices(d):
    eps = 1e-10
    b2, b3, b4, b8, b11, b12 = [d[k].astype('float64') for k in ('B2', 'B3', 'B4', 'B8', 'B11', 'B12')]
    d['NDVI'] = (b8 - b4) / (b8 + b4 + eps)
    d['NDSI'] = (b3 - b11) / (b3 + b11 + eps)
    d['BSI'] = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + eps)
    d['NDBSI'] = (d['BSI'] - d['NDVI']) / (d['BSI'] + d['NDVI'] + eps)
    d['NDTI'] = (b11 - b12) / (b11 + b12 + eps)
    return d


def shares(g, T):
    n = float(len(g))
    clear = ~g.cloud
    low = clear & (g.pmax < T)
    return {'n': int(n), 'pct_cloud': 100 * g.cloud.sum() / n,
            'pct_optical_accepted': 100 * (clear & (g.pmax >= T)).sum() / n,
            'pct_rule2_candidate': 100 * (low & (g.label == 0)).sum() / n,
            'pct_rule3_candidate': 100 * (low & (g.label == 1)).sum() / n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--final', default='9999', help='last week-ending date to include, e.g. 2025-06-22')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    clf = joblib.load(PKL)
    fitted = list(clf.feature_names_in_)
    tilled_col = list(clf.classes_).index(1)
    d = add_indices(pd.read_csv(APP))
    d['cloud'] = d['SCL'].isin([8, 9, 10])
    d = d[d.week_end <= a.final].copy()
    for name, cols in (('fitted', fitted), ('pipeline', PIPELINE_ORDER)):
        p = clf.predict_proba(np.nan_to_num(d[cols].values.astype(float)))
        d['pmax'] = p.max(1)
        d['label'] = (p.argmax(1) == tilled_col).astype(int)
        rows = [dict(week_end=w, **shares(g, 0.65)) for w, g in d.groupby('week_end')]
        rows.append(dict(week_end='all weeks', **shares(d, 0.65)))
        by_week = pd.DataFrame(rows)
        by_week.to_csv(os.path.join(a.out, 'routing_by_week_%s.csv' % name), index=False, float_format='%.2f')
        sweep = pd.DataFrame([dict(T=T, **shares(d, T)) for T in GATES])
        clear_n = float((~d.cloud).sum())
        sweep['pct_of_clear_retained'] = [100 * ((~d.cloud) & (d.pmax >= T)).sum() / clear_n for T in GATES]
        sweep.to_csv(os.path.join(a.out, 'gate_sweep_target_%s.csv' % name), index=False, float_format='%.2f')
        print('\n=== feature order: %s ===' % name)
        print(by_week.to_string(index=False, float_format=lambda v: '%.2f' % v))
        print(sweep.to_string(index=False, float_format=lambda v: '%.2f' % v))


if __name__ == '__main__':
    main()
