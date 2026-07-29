"""
Concept A2 — Target physical property (top/bottom layout).
Top:    OPTICAL — crop residue surface cover (high vs low).
Bottom: SAR    — topsoil structural state (structured vs disturbed).
"""
import os, random
from _pil_helpers import (
    Canvas, box, arrow, draw_text, rect_filled, _dashed_line, COL,
)

C = Canvas(14.0, 9.0, dpi=300)
draw_text(C, 0.5, 0.965,
          'Target physical property — crop residue cover vs topsoil structural state',
          size=36, bold=True, anchor='mm')

# ============================================================
# OPTICAL banner
# ============================================================
box(C, (0.03, 0.89), (0.94, 0.055),
    'OPTICAL  —  Crop-residue cover (biochemical signature)',
    key='opt', fontsize=30, bold=True)

# ============================================================
# Residue strip (FULL WIDTH)
# ============================================================
RS_X, RS_Y, RS_W, RS_H = 0.05, 0.55, 0.90, 0.30
rect_filled(C, (RS_X, RS_Y), (RS_W, RS_H),
            fill='#C9B98D', outline='#705B30', outline_w=5)
random.seed(12)
for _ in range(420):
    rx = RS_X + random.uniform(0.02, 0.48) * RS_W
    ry0 = RS_Y + 0.07 * RS_H; ry1 = RS_Y + 0.95 * RS_H
    ang = random.uniform(-0.04, 0.04)
    px0 = int(rx * C.W); py0 = int((1 - ry0) * C.H)
    px1 = int((rx + ang) * C.W); py1 = int((1 - ry1) * C.H)
    C.d.line((px0, py0, px1, py1), fill='#7A6234', width=3)
for _ in range(55):
    rx = RS_X + random.uniform(0.55, 0.98) * RS_W
    ry0 = RS_Y + 0.45 * RS_H; ry1 = RS_Y + 0.80 * RS_H
    ang = random.uniform(-0.03, 0.03)
    px0 = int(rx * C.W); py0 = int((1 - ry0) * C.H)
    px1 = int((rx + ang) * C.W); py1 = int((1 - ry1) * C.H)
    C.d.line((px0, py0, px1, py1), fill='#7A6234', width=3)
# vertical divider
px = int((RS_X + 0.50 * RS_W) * C.W)
_dashed_line(C.d, px, int((1 - RS_Y - 0.97 * RS_H) * C.H),
                  px, int((1 - RS_Y - 0.03 * RS_H) * C.H),
             '#333', 3, dash=18, gap=12)
# labels above
draw_text(C, RS_X + 0.25 * RS_W, RS_Y + RS_H + 0.025,
          'high residue  (no-till)',
          size=28, bold=True, italic=True, color='#3F7A56', anchor='mm')
draw_text(C, RS_X + 0.75 * RS_W, RS_Y + RS_H + 0.025,
          'low residue  (tilled)',
          size=28, bold=True, italic=True, color='#B83A35', anchor='mm')

# ============================================================
# SAR banner
# ============================================================
box(C, (0.03, 0.42), (0.94, 0.055),
    'SAR  —  Topsoil structural state (porosity · aggregates · roughness)',
    key='sar', fontsize=30, bold=True)

# ============================================================
# Soil aggregates (FULL WIDTH — two panels side by side)
# ============================================================
AG_L_X, AG_Y, AG_W, AG_H = 0.05, 0.07, 0.40, 0.30
AG_R_X = 0.55

def soil_panel(px, py, pw, ph, intact):
    rect_filled(C, (px, py), (pw, ph), fill='#C9A472',
                outline='#704A20', outline_w=5)
    random.seed(31 if intact else 73)
    n = 24 if intact else 55
    for _ in range(n):
        rx = px + random.uniform(0.05, 0.95) * pw
        ry = py + random.uniform(0.10, 0.92) * ph
        rad_norm = (random.uniform(0.045, 0.090) * pw if intact
                    else random.uniform(0.018, 0.035) * pw)
        ppx = int(rx * C.W); ppy = int((1 - ry) * C.H)
        rr = int(rad_norm * C.W)
        C.d.ellipse((ppx - rr, ppy - rr, ppx + rr, ppy + rr),
                    fill='#8B6B33', outline='#4A3A1A', width=2)
    if intact:
        for _ in range(12):
            rx = px + random.uniform(0.15, 0.85) * pw
            ry = py + random.uniform(0.20, 0.80) * ph
            ppx = int(rx * C.W); ppy = int((1 - ry) * C.H)
            C.d.ellipse((ppx - 12, ppy - 12, ppx + 12, ppy + 12),
                        fill='#FFFFFF', outline='#704A20', width=2)

soil_panel(AG_L_X, AG_Y, AG_W, AG_H, intact=True)
soil_panel(AG_R_X, AG_Y, AG_W, AG_H, intact=False)

arrow(C, (AG_L_X + AG_W + 0.005, AG_Y + AG_H/2),
         (AG_R_X - 0.005,         AG_Y + AG_H/2),
      width=6, head=30, color='#704A20')
draw_text(C, (AG_L_X + AG_W + AG_R_X) / 2, AG_Y + AG_H/2 + 0.032,
          'tillage', size=26, italic=True, bold=True,
          color='#704A20', anchor='mm')

draw_text(C, AG_L_X + AG_W/2, AG_Y + AG_H + 0.025,
          'structured topsoil  (large aggregates + macropores)',
          size=26, bold=True, italic=True, color='#3F7A56', anchor='mm')
draw_text(C, AG_R_X + AG_W/2, AG_Y + AG_H + 0.025,
          'disturbed matrix  (fine fragments, fewer pores)',
          size=26, bold=True, italic=True, color='#B83A35', anchor='mm')

C.save(os.path.join(os.path.dirname(__file__), 'fig_concept_A2_properties.png'))
print('saved fig_concept_A2_properties.png  ', C.W, 'x', C.H)
