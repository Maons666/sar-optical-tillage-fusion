# -*- coding: utf-8 -*-
"""Figure 7 -- confidence map of the optical classifier (raster figure, written as PNG).

Source rasters (the ones referenced by the ArcGIS project All-Purpose-Project.aprx):
    Till_Paper/out/RF_Confidence_0921_1005.tif   p_max x 100 of the Random Forest, 30 m, EPSG:5070
    Till_Paper/out/Cloud_Mask_0921_1005.tif      1 = SCL cloud (classes 8-10)
    Till_Paper/out/CSB_NE_updated.gpkg           USDA CSB field polygons of the strip
The window is 21 September - 5 October 2025.

Panels: (a) optical confidence p_max over the whole strip, white = high confidence, with the
        equivalent Shannon entropy H on the colour bar; (b) cloud mask of the same strip;
        (c) enlargement of the box in (a) with the CSB field boundaries.

Run: conda run -n geo python fig07_make_confidence_map.py      (writes ../fig07_confidence_map.png)
"""
import os

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Rectangle
from shapely.geometry import box

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out')
HERE = os.path.dirname(os.path.abspath(__file__))
CM = 1 / 2.54
OUTSIDE = '#DCE6F2'                  # area outside the strip
RED = '#B93737'
ZOOM = (330, 180, 710, 410)          # col0, row0, col1, row1 of the enlargement (30 m pixels)
NL = chr(10)

plt.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
                     'font.size': 9, 'axes.linewidth': 0.5, 'mathtext.fontset': 'dejavusans'})

with rasterio.open(os.path.join(OUT_DIR, 'RF_Confidence_0921_1005.tif')) as s:
    conf = s.read(1).astype('float32')
    tr, bounds = s.transform, s.bounds
with rasterio.open(os.path.join(OUT_DIR, 'Cloud_Mask_0921_1005.tif')) as s:
    cloud = s.read(1)
with rasterio.open(os.path.join(os.path.dirname(OUT_DIR), 'data', 'ready', 'S2', 'S2_ROI_mosaic_2025-09-21_2025-10-05.tif')) as s:
    s2 = s.read([1, 2, 3, 4, 5, 6])
    assert s.shape == conf.shape, 'the Sentinel-2 mosaic and the confidence raster are on different grids'
footprint = (s2 > 0).any(axis=0)                   # pixels of the strip that carry Sentinel-2 data
valid = (conf >= 50) & (conf <= 100) & footprint
P = np.where(valid, conf / 100.0, np.nan)          # optical confidence p_max
extent = (bounds.left, bounds.right, bounds.bottom, bounds.top)
c0, r0, c1, r1 = ZOOM
zx0, zx1 = tr.c + c0 * tr.a, tr.c + c1 * tr.a
zy1, zy0 = tr.f + r0 * tr.e, tr.f + r1 * tr.e
csb = gpd.read_file(os.path.join(OUT_DIR, 'CSB_NE_updated.gpkg'), bbox=(zx0, zy0, zx1, zy1))
csb = csb[csb.intersects(box(zx0, zy0, zx1, zy1))]
grey = plt.get_cmap('gray').copy()
grey.set_bad(OUTSIDE)

W = 16.0                                             # figure width in cm
strip = (bounds.top - bounds.bottom) / (bounds.right - bounds.left)
wa = 15.7
ha = wa * strip
wb = 7.7
hb = wb * strip
HGT = 0.55 + ha + 1.35 + 0.55 + hb + 0.15            # figure height in cm
fig = plt.figure(figsize=(W * CM, HGT * CM))
ya = HGT - 0.55 - ha
ax_a = fig.add_axes([0.15 / W, ya / HGT, wa / W, ha / HGT])
ax_cb = fig.add_axes([4.0 / W, (ya - 0.42) / HGT, 8.0 / W, 0.22 / HGT])
yb = 0.15
ax_b = fig.add_axes([0.15 / W, yb / HGT, wb / W, hb / HGT])
wc = hb * (c1 - c0) / float(r1 - r0)
ax_c = fig.add_axes([8.15 / W, yb / HGT, wc / W, hb / HGT])


def scalebar(ax, x, y, km, unit):
    ax.add_patch(Rectangle((x - 0.3 * unit, y - 0.45 * unit), km * 1000 + 0.6 * unit, 2.3 * unit, facecolor='white',
                           edgecolor='none', alpha=0.9, zorder=5))
    ax.plot([x, x + km * 1000], [y, y], color='black', lw=1.6, solid_capstyle='butt', zorder=6)
    ax.text(x + km * 500, y + 0.3 * unit, '%d km' % km, ha='center', va='bottom', fontsize=8, zorder=6)


im = ax_a.imshow(np.ma.masked_invalid(P), cmap=grey, vmin=0.5, vmax=1, extent=extent, interpolation='nearest')
ax_a.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fill=False, edgecolor=RED, lw=1.1))
ax_a.text(zx1 + 400, zy1, '(c)', color=RED, fontsize=9, fontweight='bold', va='top',
          bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1))
scalebar(ax_a, bounds.right - 12500, bounds.bottom + 1300, 10, 1000)
ax_a.set_title('(a) Confidence of the optical prediction', fontsize=9, loc='left', pad=3)
cb = fig.colorbar(im, cax=ax_cb, orientation='horizontal')
cb.set_ticks([0.5, 0.65, 0.8, 0.9, 1.0])
cb.set_ticklabels(['0.50' + NL + '(1.00)', '0.65' + NL + '(0.93)', '0.80' + NL + '(0.72)', '0.90' + NL + '(0.47)', '1.00' + NL + '(0)'])
cb.ax.tick_params(labelsize=8, length=2, width=0.5)
cb.ax.axvline(0.65, color=RED, lw=1.0)
fig.text(3.3 / W, (ya - 0.78) / HGT, r'$p_{\max}$' + NL + r'($H$, bit)', fontsize=8, ha='right', va='center', linespacing=1.25)
fig.text(12.2 / W, (ya - 0.31) / HGT, 'red line: gate', fontsize=8, ha='left', va='center', color=RED)

ax_b.imshow(np.ma.masked_where(~valid, cloud), cmap=ListedColormap(['#F2F2F2', '#B86B2A']), vmin=0, vmax=1,
            extent=extent, interpolation='nearest')
ax_b.set_facecolor(OUTSIDE)
ax_b.legend(handles=[Patch(facecolor='#B86B2A', label='cloud (SCL 8-10)'),
                     Patch(facecolor='#F2F2F2', edgecolor='0.5', lw=0.4, label='not flagged')],
            loc='lower left', fontsize=8, frameon=True, framealpha=0.9, borderpad=0.3, handlelength=1.0, labelspacing=0.2)
ax_b.set_title('(b) Cloud mask', fontsize=9, loc='left', pad=3)

ax_c.imshow(np.ma.masked_invalid(P[r0:r1, c0:c1]), cmap=grey, vmin=0.5, vmax=1, extent=(zx0, zx1, zy0, zy1), interpolation='nearest')
csb.boundary.plot(ax=ax_c, color=RED, linewidth=0.45)
ax_c.set_xlim(zx0, zx1)
ax_c.set_ylim(zy0, zy1)
ax_c.set_aspect('auto')
scalebar(ax_c, zx1 - 2700, zy0 + 400, 2, 420)
ax_c.set_title('(c) Enlargement with CSB field boundaries', fontsize=9, loc='left', pad=3)
fig.text((8.15 + wc + 0.2) / W, (yb + hb) / HGT, 'red lines:' + NL + 'USDA CSB' + NL + 'fields', fontsize=8, va='top', ha='left', color=RED)

for ax in (ax_a, ax_b, ax_c):
    ax.set_xticks([])
    ax.set_yticks([])
clear = valid & (cloud == 0)
cl = valid & (cloud == 1)
print('strip pixels %d; cloud share %.1f%%' % (valid.sum(), 100.0 * cl.sum() / valid.sum()))
print('clear pixels: median p_max %.2f, share below the gate %.1f%%, share above 0.90 %.1f%%'
      % (np.nanmedian(P[clear]), 100 * np.mean(P[clear] < 0.65), 100 * np.mean(P[clear] > 0.90)))
print('cloud pixels: median p_max %.2f, share above 0.90 %.1f%%' % (np.nanmedian(P[cl]), 100 * np.mean(P[cl] > 0.90)))
out = os.path.join(HERE, '..', 'fig07_confidence_map.png')
fig.savefig(out, dpi=400, facecolor='white')
print('written', os.path.abspath(out), 'fields in enlargement:', len(csb), 'size cm %.1f x %.1f' % (W, HGT))
