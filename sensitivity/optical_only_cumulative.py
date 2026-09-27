# -*- coding: utf-8 -*-
"""Cumulative share of the sampled pixels labelled Tilled by the optical channel alone (clear pixels only),
and by rule 1 alone, up to a final week. Companion of fusion_sweep_samples.py (baseline thresholds).

Usage: conda run -n geo python optical_only_cumulative.py --grd ../output_grd --final 2025-06-22
"""
import argparse
import os

import joblib
import numpy as np
import pandas as pd

from fusion_sweep_samples import APP, PKL, add_indices

ap = argparse.ArgumentParser()
ap.add_argument('--grd', required=True)
ap.add_argument('--final', default='2025-06-22')
a = ap.parse_args()
clf = joblib.load(PKL)
d = add_indices(pd.read_csv(APP))
d = d.merge(pd.read_csv(os.path.join(a.grd, 's1_grd_samples.csv')).drop_duplicates(['pid', 'week_end']), on=['pid', 'week_end'], how='left')
d = d[d.week_end <= a.final]
p = clf.predict_proba(np.nan_to_num(d[list(clf.feature_names_in_)].values.astype(float)))
d['opt'] = p.argmax(1) == list(clf.classes_).index(1)
d['cloud'] = d.SCL.isin([8, 9, 10])
d['g'] = np.sqrt(d.rho.clip(lower=0))
n = d.pid.nunique()
opt = set(d[~d.cloud & d.opt].pid)
r1 = set(d[d.cloud & d.g.notna() & (d.g < 0.25)].pid)
print('pixels %d, weeks %d, final week %s' % (n, d.week_end.nunique(), a.final))
print('labelled Tilled by the optical channel in at least one clear week : %.2f%%' % (100.0 * len(opt) / n))
print('labelled Tilled by rule 1 in at least one cloudy week             : %.2f%%' % (100.0 * len(r1) / n))
print('either                                                            : %.2f%%' % (100.0 * len(opt | r1) / n))
cl = d[d.cloud & d.g.notna()]
print('cloud pixel-weeks with a Sentinel-1 value: %d, of which g < 0.25: %.1f%%' % (len(cl), 100.0 * (cl.g < 0.25).mean()))
print('pixels under cloud (with a Sentinel-1 value) in at least k weeks:',
      {k: round(100.0 * (cl.groupby('pid').size() >= k).sum() / n, 1) for k in (1, 3, 5)})
