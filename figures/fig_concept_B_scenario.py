"""
Concept Fig B — Scenario comparison (3 columns × 4 rows).

Columns: clear sky / partial cloud / heavy cloud.
Rows: S2 view · entropy H · SAR coherence γ · active module.
"""
import os
from _pil_helpers import Canvas, box, draw_text, rect_filled, arrow, COL

C = Canvas(12, 8, dpi=300)

draw_text(C, 0.5, 0.97,
          'Active sensing module switches with optical-confidence regime',
          size=30, bold=True, anchor='mm')

col_x = [0.10, 0.40, 0.70]   # x-left of each column
col_w = 0.26
col_titles = ['CLEAR SKY', 'PARTIAL CLOUD', 'HEAVY CLOUD']
col_colors = [('#3F7A56', '#E2F0DA'),
              ('#C99700', '#FFF4D9'),
              ('#B86C2C', '#F3D6BD')]

# row Y-centers (top-to-bottom)
row_y    = {'header': 0.88, 's2': 0.74, 'H': 0.55, 'gamma': 0.36, 'mod': 0.18}
row_lab  = {'s2': 'S2 surface\nreflectance',
            'H': 'Shannon\nentropy  H',
            'gamma': 'SAR\ncoherence γ',
            'mod': 'Active\nmodule'}

# column headers
for x, t, (ec, fc) in zip(col_x, col_titles, col_colors):
    box(C, (x, row_y['header'] - 0.035), (col_w, 0.07),
        t, fc=ec, ec=ec, text_color='white', fontsize=24, bold=True)

# row labels (left margin)
for k in ('s2', 'H', 'gamma', 'mod'):
    draw_text(C, 0.07, row_y[k], row_lab[k],
              size=18, italic=True, anchor='rm')

# --- row 1: S2 view (stylised swatch with progressive cloud) ----------
clouds = [0.0, 0.45, 0.85]
for x, cover in zip(col_x, clouds):
    cy = row_y['s2']; ch = 0.10
    # crop field swatch
    rect_filled(C, (x + 0.01, cy - ch/2), (col_w - 0.02, ch),
                fill='#C9B98D', outline='#705B30', outline_w=2)
    # horizontal crop-line texture
    for k in range(4):
        px1 = (x + 0.015) * C.W
        px2 = (x + col_w - 0.015) * C.W
        ypx = ((1.0 - (cy - ch/2 + (k+1) * ch / 5))) * C.H
        C.d.line((px1, ypx, px2, ypx), fill='#705B30', width=1)
    # cloud overlay
    if cover > 0:
        cw = (col_w - 0.02) * cover
        rect_filled(C, (x + 0.01, cy - ch/2), (cw, ch), fill='#E8E8E8')
        draw_text(C, x + 0.01 + cw/2, cy, '☁', size=72, color='#999', anchor='mm')

# --- row 2: entropy H (grayscale band) -------------------------------
import math
def grad_band(c, x, y, w, h, h_val):
    """draw a horizontal gradient from 0 to h_val (greyscale)"""
    n = 80
    px0 = int(x * c.W); py0 = int((1.0 - y - h/2) * c.H)
    px1 = int((x + w) * c.W); py1 = int((1.0 - y + h/2) * c.H)
    step = (px1 - px0) / n
    for i in range(n):
        g = int(255 * (1.0 - (i/n) * h_val))
        color = (g, g, g)
        c.d.rectangle((int(px0 + i*step), py0, int(px0 + (i+1)*step), py1), fill=color)
    c.d.rectangle((px0, py0, px1, py1), outline='#444', width=2)

H_vals = [0.10, 0.55, 0.92]
for x, h_val in zip(col_x, H_vals):
    grad_band(C, x + 0.01, row_y['H'], col_w - 0.02, 0.08, h_val)
    draw_text(C, x + col_w/2, row_y['H'] - 0.07,
              f'H ≈ {h_val:.2f}', size=22, bold=True, anchor='mm')

# --- row 3: SAR γ (uniform swatch with "diagnostic" label) ----------
for x in col_x:
    rect_filled(C, (x + 0.01, row_y['gamma'] - 0.05), (col_w - 0.02, 0.10),
                fill='#F3D6BD', outline='#B86C2C', outline_w=2)
    draw_text(C, x + col_w/2, row_y['gamma'],
              'γ diagnostic\n(cloud-immune)',
              size=20, color='#704A20', anchor='mm')

# --- row 4: active module -------------------------------------------
modules = [
    ('USE OPTICAL',                '#3F7A56', '#E2F0DA'),
    ('WEIGHTED FUSION',            '#9C7800', '#FFF4D9'),
    ('SAR OVERRIDE',               '#B86C2C', '#F3D6BD'),
]
for x, (lab, ec, fc) in zip(col_x, modules):
    box(C, (x + 0.005, row_y['mod'] - 0.05), (col_w - 0.01, 0.10),
        lab, fc=fc, ec=ec, fontsize=22, bold=True)

# --- decision rule strip at bottom ----------------------------------
box(C, (0.04, 0.03), (0.92, 0.07),
    'Decision rule:    H < 0.30  →  optical    |    0.30 ≤ H < 0.65  →  fusion    |    H ≥ 0.65  →  SAR override',
    key='gate', fontsize=20, italic=True)

out = os.path.join(os.path.dirname(__file__), 'fig_concept_B_scenario.png')
C.save(out); print('saved:', out)
