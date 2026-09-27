# -*- coding: utf-8 -*-
"""Numbers quoted in Section 4.2 for the confidence map of Figure 7 (strip, 21 Sep - 5 Oct 2025).

Reads the same rasters as figures/src/fig07_make_confidence_map.py and reports
  * cloud share of the strip; p_max statistics of clear and of cloud pixels;
  * for clear pixels inside CSB fields: p_max at field edges (pixels touched by a field boundary)
    versus field interiors (at least 2 pixels = 60 m from any boundary).
Run:  conda run -n geo python fig07_confidence_stats.py
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from scipy import ndimage

OUT_DIR = _os.path.join(_REPO, 'out')
RES = _os.path.join(_DATA, 'confidence_map_stats.txt')

with rasterio.open(os.path.join(OUT_DIR, 'RF_Confidence_0921_1005.tif')) as s:
    conf = s.read(1).astype(np.float32)
    tr, crs, shape = s.transform, s.crs, s.shape
    bounds = s.bounds
with rasterio.open(os.path.join(OUT_DIR, 'Cloud_Mask_0921_1005.tif')) as s:
    cloud = s.read(1) == 1
with rasterio.open(os.path.join(os.path.dirname(OUT_DIR), 'data', 'ready', 'S2', 'S2_ROI_mosaic_2025-09-21_2025-10-05.tif')) as s:
    footprint = (s.read() > 0).any(axis=0)

valid = (conf >= 50) & (conf <= 100) & footprint
P = conf / 100.0
clear = valid & ~cloud
cl = valid & cloud
lines = []


def stats(name, m):
    v = P[m]
    lines.append('%-34s n=%9d  median %.3f  mean %.3f  <0.65: %5.1f%%  >0.90: %5.1f%%'
                 % (name, v.size, np.median(v), v.mean(), 100 * np.mean(v < 0.65), 100 * np.mean(v > 0.90)))


lines.append('strip pixels %d; cloud share %.1f%%' % (valid.sum(), 100.0 * cl.sum() / valid.sum()))
stats('clear pixels', clear)
stats('cloud pixels', cl)

csb = gpd.read_file(os.path.join(OUT_DIR, 'CSB_NE_updated.gpkg'), bbox=tuple(bounds)).to_crs(crs)
csb = csb[~csb.geometry.is_empty & csb.geometry.notna()]
infield = features.rasterize(((g, 1) for g in csb.geometry), out_shape=shape, transform=tr, fill=0, dtype='uint8').astype(bool)
edge = features.rasterize(((g, 1) for g in csb.geometry.boundary), out_shape=shape, transform=tr, fill=0,
                          all_touched=True, dtype='uint8').astype(bool)
dist = ndimage.distance_transform_edt(~edge)            # pixels to the nearest boundary pixel
interior = infield & (dist >= 2)
lines.append('CSB fields intersecting the strip: %d; clear in-field pixels: %d' % (len(csb), (clear & infield).sum()))
stats('clear, field edge (boundary px)', clear & edge)
stats('clear, field interior (>= 60 m)', clear & interior)
stats('clear, outside CSB fields', clear & ~infield & ~edge)

open(RES, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
