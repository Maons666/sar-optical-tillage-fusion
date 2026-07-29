"""
Concept A1 — Measurement physics (top/bottom layout).
Top:    OPTICAL — SWIR reflectance with cellulose/lignin dips.
Bottom: SAR    — t₁/t₂ scatterer rearrangement with displacement traces.
"""
import os, math, random
from _pil_helpers import (
    Canvas, box, arrow, draw_text, rect_filled, _dashed_line, COL, font,
)

C = Canvas(14.0, 9.0, dpi=300)
draw_text(C, 0.5, 0.965,
          'Measurement physics — optical chemistry vs SAR mechanics',
          size=38, bold=True, anchor='mm')

# ============================================================
# OPTICAL banner
# ============================================================
box(C, (0.03, 0.89), (0.94, 0.055),
    'OPTICAL  —  Cellulose / lignin absorption depth (Sentinel-2 SWIR)',
    key='opt', fontsize=30, bold=True)

# ============================================================
# SWIR reflectance chart  (FULL WIDTH)
# ============================================================
SP_X, SP_Y, SP_W, SP_H = 0.07, 0.51, 0.88, 0.36
rect_filled(C, (SP_X, SP_Y), (SP_W, SP_H),
            fill='white', outline='#333', outline_w=5)

# Values after Daughtry (2001, 2004) — wheat straw / Williams loam
spectra = [
    (0.50,  0.12,    0.10), (0.70,  0.22,    0.18), (0.90,  0.36,    0.25),
    (1.10,  0.45,    0.30), (1.30,  0.52,    0.33), (1.50,  0.53,    0.35),
    (1.65,  0.53,    0.36), (1.80,  0.49,    0.36), (1.90,  0.30,    0.22),
    (2.00,  0.47,    0.31), (2.05,  0.46,    0.31), (2.10,  0.32,    0.31),
    (2.15,  0.45,    0.30), (2.20,  0.47,    0.29), (2.25,  0.45,    0.28),
    (2.30,  0.34,    0.27), (2.35,  0.43,    0.27), (2.40,  0.45,    0.26),
    (2.50,  0.45,    0.25),
]

def sp_xy(wl, v):
    xn = SP_X + 0.06 * SP_W + (wl - 0.5) / 2.0 * (SP_W - 0.08 * SP_W)
    yn = SP_Y + 0.10 * SP_H + (v / 0.6) * (SP_H - 0.18 * SP_H)
    return xn, yn

# x-axis
for wl in [0.5, 1.0, 1.5, 2.0, 2.3, 2.5]:
    xn, _ = sp_xy(wl, 0)
    px, py = C.P(xn, SP_Y)
    C.d.line((px, py - 4, px, py + 22), fill='#333', width=4)
    draw_text(C, xn, SP_Y - 0.022, f'{wl}', size=26, anchor='mm')
draw_text(C, SP_X + SP_W/2, SP_Y - 0.058,
          'wavelength  (μm)', size=30, italic=True, anchor='mm')

# y-axis
for v in [0.0, 0.2, 0.4, 0.6]:
    _, yn = sp_xy(0.5, v)
    px, py = C.P(SP_X, yn)
    C.d.line((px - 22, py, px + 4, py), fill='#333', width=4)
    draw_text(C, SP_X - 0.013, yn, f'{v:.1f}', size=26, anchor='rm')
draw_text(C, SP_X - 0.040, SP_Y + SP_H/2,
          'reflectance', size=30, italic=True, anchor='mm')

# curves
soil_pts = [sp_xy(s[0], s[2]) for s in spectra]
res_pts  = [sp_xy(s[0], s[1]) for s in spectra]
for a, b in zip(soil_pts[:-1], soil_pts[1:]):
    p1 = C.P(*a); p2 = C.P(*b)
    C.d.line((p1[0], p1[1], p2[0], p2[1]), fill='#B07C40', width=10)
for a, b in zip(res_pts[:-1], res_pts[1:]):
    p1 = C.P(*a); p2 = C.P(*b)
    C.d.line((p1[0], p1[1], p2[0], p2[1]), fill='#3F7A56', width=12)

# dip annotations
def dip_anno(wl, v_dip, label):
    xn, yn = sp_xy(wl, v_dip)
    _, yn_label = sp_xy(wl, 0.62)
    arrow(C, (xn, yn_label - 0.008), (xn, yn + 0.014),
          width=4, head=20, color='#3F7A56')
    draw_text(C, xn, yn_label + 0.018, label,
              size=26, bold=True, italic=True,
              color='#3F7A56', anchor='mm')
dip_anno(2.10, 0.32, 'cellulose dip\n2.1 μm')
dip_anno(2.30, 0.34, 'lignin dip\n2.3 μm')

# legend (inside chart, top-left)
lg_x  = SP_X + 0.025
lg_y1 = SP_Y + SP_H - 0.038
lg_y2 = SP_Y + SP_H - 0.075
px = int(lg_x * C.W)
py1 = int((1 - lg_y1) * C.H); py2 = int((1 - lg_y2) * C.H)
C.d.line((px, py1, px + 80, py1), fill='#B07C40', width=10)
draw_text(C, lg_x + 0.040, lg_y1, 'bare soil',
          size=26, italic=True, color='#705B30', anchor='lm')
C.d.line((px, py2, px + 80, py2), fill='#3F7A56', width=12)
draw_text(C, lg_x + 0.040, lg_y2, 'crop residue',
          size=26, italic=True, color='#3F7A56', anchor='lm')

# ============================================================
# SAR banner
# ============================================================
box(C, (0.03, 0.42), (0.94, 0.055),
    'SAR  —  Scatterer geometry decorrelation (Sentinel-1 SLC)',
    key='sar', fontsize=30, bold=True)

# ============================================================
# Scatterer panels (FULL WIDTH — two panels side by side)
# ============================================================
PX_L, PY_C, PW_C, PH_C = 0.05, 0.07, 0.39, 0.32
PX_R = 0.56

random.seed(7)
N = 22
HL = [3, 11, 17]
HL_COL = ['#3F7A56', '#7E5BA0', '#B83A35']
DEFAULT = '#B86C2C'
pos_t1 = [(random.random(), random.random()) for _ in range(N)]
radii  = [random.randint(15, 22) for _ in range(N)]
cols   = [DEFAULT] * N
for i, c_ in zip(HL, HL_COL):
    cols[i] = c_
random.seed(13)
pos_t2 = [(max(0.03, min(0.97, nx + random.uniform(-0.55, 0.55))),
           max(0.03, min(0.97, ny + random.uniform(-0.55, 0.55))))
          for nx, ny in pos_t1]

def draw_scat(px, py, pw, ph, positions):
    rect_filled(C, (px, py), (pw, ph), fill='#FFF4E6',
                outline='#B86C2C', outline_w=5)
    for (nx, ny), r, col in zip(positions, radii, cols):
        cx = px + 0.05 * pw + nx * 0.90 * pw
        cy = py + 0.05 * ph + ny * 0.90 * ph
        rpx = int(cx * C.W); rpy = int((1 - cy) * C.H)
        C.d.ellipse((rpx - r, rpy - r, rpx + r, rpy + r),
                    fill=col, outline='black', width=2)

draw_scat(PX_L, PY_C, PW_C, PH_C, pos_t1)
draw_scat(PX_R, PY_C, PW_C, PH_C, pos_t2)

draw_text(C, PX_L + PW_C/2, PY_C + PH_C + 0.025,
          'acquisition  t₁  (natural pattern)',
          size=28, bold=True, anchor='mm', color='#704A20')
draw_text(C, PX_R + PW_C/2, PY_C + PH_C + 0.025,
          'acquisition  t₂   (after tillage)',
          size=28, bold=True, anchor='mm', color='#704A20')

# displacement traces
for i, col in zip(HL, HL_COL):
    nx1, ny1 = pos_t1[i]; nx2, ny2 = pos_t2[i]
    p1 = (PX_L + 0.05 * PW_C + nx1 * 0.90 * PW_C,
          PY_C + 0.05 * PH_C + ny1 * 0.90 * PH_C)
    p2 = (PX_R + 0.05 * PW_C + nx2 * 0.90 * PW_C,
          PY_C + 0.05 * PH_C + ny2 * 0.90 * PH_C)
    px1 = int(p1[0] * C.W); py1 = int((1 - p1[1]) * C.H)
    px2 = int(p2[0] * C.W); py2 = int((1 - p2[1]) * C.H)
    _dashed_line(C.d, px1, py1, px2, py2, col, 4, dash=16, gap=12)

arrow(C, (PX_L + PW_C + 0.005, PY_C + PH_C/2),
         (PX_R - 0.005,        PY_C + PH_C/2),
      width=6, head=30, color='#704A20')
draw_text(C, (PX_L + PW_C + PX_R) / 2, PY_C + PH_C/2 + 0.032,
          'tillage', size=26, italic=True, bold=True,
          color='#704A20', anchor='mm')

C.save(os.path.join(os.path.dirname(__file__), 'fig_concept_A1_physics.png'))
print('saved fig_concept_A1_physics.png  ', C.W, 'x', C.H)
