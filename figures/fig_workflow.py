"""
Fig W: Improved workflow (4-panel a/b/c/d) for Till v0.9.
"""
import os
from _pil_helpers import Canvas, box, arrow, draw_text, hline_dashed, COL

C = Canvas(13, 9, dpi=300)

# overall title
draw_text(C, 0.5, 0.97,
          'Workflow of the All-Weather Tillage Detection Framework',
          size=34, bold=True, anchor='mm')

# panel boundaries (left half / right half × top half / bottom half)
PANELS = {
    'a': (0.020, 0.50, 0.48, 0.45),   # (x, y_bottom, w, h)
    'b': (0.500, 0.50, 0.48, 0.45),
    'c': (0.020, 0.02, 0.48, 0.45),
    'd': (0.500, 0.02, 0.48, 0.45),
}

def panel_title(c, pkey, text):
    x, y, w, h = PANELS[pkey]
    draw_text(c, x + 0.005, y + h - 0.005, f'({pkey}) {text}',
              size=22, bold=True, anchor='lt')

def L(pkey, lx, ly, lw, lh):
    """convert intra-panel 0-1 coord to global"""
    px, py, pw, ph = PANELS[pkey]
    inner_top_pad = 0.04   # leave room for panel title
    return (px + lx * pw,
            py + ly * (ph - inner_top_pad),
            lw * pw,
            lh * (ph - inner_top_pad))

# ===================================================================
# Panel (a) — Cloud-Native Data Acquisition & Harmonization
# ===================================================================
panel_title(C, 'a', 'Cloud-Native Data Acquisition & Harmonization')

inputs = [
    (0.04, 'S2 L2A\nMultispectral',     'input'),
    (0.27, 'S1 SLC\n(IW, VV)',          'input'),
    (0.50, 'USDA CSB\nv2024',           'input'),
    (0.73, '2024 Ground\nTruth (n=126,963)', 'gt'),
]
for xn, lab, k in inputs:
    x, y, w, h = L('a', xn, 0.78, 0.20, 0.16)
    box(C, (x, y), (w, h), lab, key=k, fontsize=20)

x, y, w, h = L('a', 0.10, 0.46, 0.80, 0.14)
box(C, (x, y), (w, h),
    'Geometric Harmonization\nReproject to Conus Albers Equal-Area (EPSG:5070)',
    key='proc', fontsize=22, bold=True)

# arrows from each input to hub
for xn, _, _ in inputs:
    p1x = PANELS['a'][0] + (xn + 0.10) * PANELS['a'][2]
    p1y = PANELS['a'][1] + 0.78 * (PANELS['a'][3] - 0.04)
    p2y = PANELS['a'][1] + 0.60 * (PANELS['a'][3] - 0.04)
    arrow(C, (p1x, p1y), (p1x, p2y), width=3, head=15)

x, y, w, h = L('a', 0.22, 0.16, 0.56, 0.12)
box(C, (x, y), (w, h),
    'Weekly Mosaics\n(rolling 7-day temporal window)',
    key='out', fontsize=22, bold=True)
# arrow hub -> mosaics
hub_x = PANELS['a'][0] + 0.50 * PANELS['a'][2]
hub_y = PANELS['a'][1] + 0.46 * (PANELS['a'][3] - 0.04)
mos_y = PANELS['a'][1] + (0.16 + 0.12) * (PANELS['a'][3] - 0.04)
arrow(C, (hub_x, hub_y), (hub_x, mos_y), width=4, head=18)

# ===================================================================
# Panel (b) — Optical Feature Engineering & Epistemic UQ
# ===================================================================
panel_title(C, 'b', 'Optical Feature Engineering & Epistemic UQ')

x, y, w, h = L('b', 0.30, 0.83, 0.40, 0.10)
box(C, (x, y), (w, h), 'S2 Mosaic', key='opt', fontsize=22, bold=True)

x2, y2, w2, h2 = L('b', 0.08, 0.60, 0.84, 0.14)
box(C, (x2, y2), (w2, h2),
    'Spectral Indices\nNDTI · NDVI · NDSI · BSI · NDBSI',
    key='proc', fontsize=22)
arrow(C, (x + w/2, y), (x2 + w2/2, y2 + h2), width=3, head=15)

x3, y3, w3, h3 = L('b', 0.18, 0.38, 0.64, 0.12)
box(C, (x3, y3), (w3, h3), 'Random Forest  (200 trees)',
    key='proc', fontsize=22, bold=True)
arrow(C, (x2 + w2/2, y2), (x3 + w3/2, y3 + h3), width=3, head=15)

# branching outputs
xa, ya, wa, ha = L('b', 0.03, 0.10, 0.42, 0.16)
xb, yb, wb, hb = L('b', 0.55, 0.10, 0.42, 0.16)
box(C, (xa, ya), (wa, ha),
    'Class Prediction\n(tilled / untilled)', key='out', fontsize=20, bold=True)
box(C, (xb, yb), (wb, hb),
    'Shannon Entropy H\n(per-pixel confidence)', key='dec', fontsize=20, bold=True)
arrow(C, (x3 + 0.30 * w3, y3), (xa + wa/2, ya + ha), width=3, head=15)
arrow(C, (x3 + 0.70 * w3, y3), (xb + wb/2, yb + hb), width=3, head=15)

draw_text(C, xb + wb/2, ya - 0.005, 'H < 0.65   ⇒   confident',
          size=18, italic=True, color='#9C7800', anchor='mm')

# ===================================================================
# Panel (c) — SAR SLC Phase Processing
# ===================================================================
panel_title(C, 'c', 'SAR SLC Phase Processing')

x, y, w, h = L('c', 0.13, 0.82, 0.74, 0.11)
box(C, (x, y), (w, h),
    'S1 SLC pair  (t,  t + 6 d)', key='sar', fontsize=22, bold=True)

x2, y2, w2, h2 = L('c', 0.18, 0.60, 0.64, 0.10)
box(C, (x2, y2), (w2, h2),
    'Coregistration  &  Topographic Correction',
    key='proc', fontsize=22)
arrow(C, (x + w/2, y), (x2 + w2/2, y2 + h2), width=3, head=15)

x3, y3, w3, h3 = L('c', 0.18, 0.38, 0.64, 0.12)
box(C, (x3, y3), (w3, h3),
    'Interferometric Coherence γ\n(9 × 9 spatial average)',
    key='proc', fontsize=22)
arrow(C, (x2 + w2/2, y2), (x3 + w3/2, y3 + h3), width=3, head=15)

x4, y4, w4, h4 = L('c', 0.18, 0.12, 0.64, 0.14)
box(C, (x4, y4), (w4, h4),
    'Disturbance Flag\nγ < 0.25  ⇒  tilled pixel',
    key='out', fontsize=22, bold=True)
arrow(C, (x3 + w3/2, y3), (x4 + w4/2, y4 + h4), width=4, head=18)

# sensitivity-sweep callout
draw_text(C, x4 + w4 + 0.005, y4 + h4/2,
          'Sensitivity\nsweep:\nγ ∈ {0.15,\n0.20, 0.25,\n0.30}',
          size=16, italic=True, color='#B86C2C', anchor='lm')

# ===================================================================
# Panel (d) — Dynamic Fusion & Field-Level Aggregation
# ===================================================================
panel_title(C, 'd', 'Dynamic Multi-Modal Fusion & Field-Level Aggregation')

# headers for inputs
draw_text(C, PANELS['d'][0] + 0.18 * PANELS['d'][2],
          PANELS['d'][1] + (0.92) * (PANELS['d'][3] - 0.04),
          'from (b):\nclass + H', size=16, italic=True,
          color='#3F7A56', anchor='mm')
draw_text(C, PANELS['d'][0] + 0.82 * PANELS['d'][2],
          PANELS['d'][1] + (0.92) * (PANELS['d'][3] - 0.04),
          'from (c):\nγ flag', size=16, italic=True,
          color='#B86C2C', anchor='mm')

x, y, w, h = L('d', 0.05, 0.62, 0.90, 0.20)
box(C, (x, y), (w, h),
    'Dynamic Fusion Rules\n'
    'R1 · Cloud override     R2 · Confidence-based synergy     R3 · False-alarm suppression',
    key='fuse', fontsize=20, bold=True)

arrow(C, (PANELS['d'][0] + 0.18 * PANELS['d'][2],
          PANELS['d'][1] + 0.88 * (PANELS['d'][3] - 0.04)),
         (x + 0.20 * w, y + h), width=3, head=15)
arrow(C, (PANELS['d'][0] + 0.82 * PANELS['d'][2],
          PANELS['d'][1] + 0.88 * (PANELS['d'][3] - 0.04)),
         (x + 0.80 * w, y + h), width=3, head=15)

x2, y2, w2, h2 = L('d', 0.18, 0.46, 0.64, 0.09)
box(C, (x2, y2), (w2, h2), 'Pixel-level Fused Tillage', key='proc', fontsize=20)
arrow(C, (x + w/2, y), (x2 + w2/2, y2 + h2), width=3, head=15)

x3, y3, w3, h3 = L('d', 0.10, 0.28, 0.80, 0.09)
box(C, (x3, y3), (w3, h3),
    'CSB Zonal Aggregation  →  Tillage Fraction (TF)',
    key='proc', fontsize=20)
arrow(C, (x2 + w2/2, y2), (x3 + w3/2, y3 + h3), width=3, head=15)

x4, y4, w4, h4 = L('d', 0.06, 0.06, 0.88, 0.13)
box(C, (x4, y4), (w4, h4),
    'Weekly Field-Level Tillage Map',
    key='out', fontsize=24, bold=True)
arrow(C, (x3 + w3/2, y3), (x4 + w4/2, y4 + h4), width=4, head=18)

# save
out = os.path.join(os.path.dirname(__file__), 'fig_workflow.png')
C.save(out)
print('saved:', out)
