"""
Concept Fig C — Signal-trace framing.

Three stacked panels showing how optical NDTI, SAR coherence γ, and
Shannon entropy H co-evolve through a cloudy tillage window.
"""
import os, math
import numpy as np
from _pil_helpers import Canvas, draw_text, rect_filled, _dashed_line, COL

C = Canvas(11, 8, dpi=300)

draw_text(C, 0.5, 0.97,
          'Co-evolution of optical and SAR signals through a cloudy tillage window',
          size=26, bold=True, anchor='mm')

# ----- synthetic but physically plausible signals -------------------
np.random.seed(42)
T = 60
days = np.arange(0, T)
tillage_day = 32
cloud_start, cloud_end = 18, 30

# NDTI: high pre-tillage, low after; gap during cloud
ndti = 0.42 - 0.005 * np.maximum(days - tillage_day, 0) + np.random.normal(0, 0.012, T)
ndti_mask = (days >= cloud_start) & (days <= cloud_end)
ndti[ndti_mask] = np.nan

# γ: continuous, drops at tillage
gamma = 0.82 - 0.55 / (1 + np.exp(-(days - tillage_day) * 1.4)) + np.random.normal(0, 0.02, T)
gamma = np.clip(gamma, 0.05, 0.95)

# H: low normally; spikes during cloud
H = 0.15 + np.random.normal(0, 0.03, T)
H[ndti_mask] = 0.90 + np.random.normal(0, 0.04, ndti_mask.sum())
H = np.clip(H, 0.02, 0.98)

# ----- layout: 3 panels stacked -------------------------------------
PANELS = {
    'ndti':  (0.13, 0.66, 0.83, 0.22),   # (x, y_bottom, w, h)
    'gamma': (0.13, 0.39, 0.83, 0.22),
    'H':     (0.13, 0.12, 0.83, 0.22),
}

def axis_box(c, key, ylab):
    x, y, w, h = PANELS[key]
    rect_filled(c, (x, y), (w, h), fill='white', outline='#444', outline_w=2)
    # light cloud band
    cs = cloud_start / T; ce = cloud_end / T
    rect_filled(c, (x + cs * w, y + 0.005), ((ce - cs) * w, h - 0.01),
                fill='#E8E8E8')
    # y label
    draw_text(c, x - 0.015, y + h/2, ylab,
              size=20, anchor='rm')
    return x, y, w, h

def to_xy(x, y, w, h, t, v, vmin, vmax):
    """map (day, value) to normalized canvas coords"""
    return (x + (t / T) * w, y + (v - vmin) / (vmax - vmin) * h)

def plot_line(c, x, y, w, h, ts, vs, vmin, vmax, color, marker_face, lw=3, ms=6):
    pts = []
    for t, v in zip(ts, vs):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            if pts:
                _draw_segments(c, pts, color, lw)
                pts = []
            continue
        pts.append(to_xy(x, y, w, h, t, v, vmin, vmax))
    if pts:
        _draw_segments(c, pts, color, lw)
    # markers
    for t, v in zip(ts, vs):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            continue
        px, py = to_xy(x, y, w, h, t, v, vmin, vmax)
        ppx = int(px * c.W); ppy = int((1.0 - py) * c.H)
        c.d.ellipse((ppx - ms, ppy - ms, ppx + ms, ppy + ms),
                    fill=marker_face, outline=color, width=2)

def _draw_segments(c, pts, color, width):
    for (px, py), (qx, qy) in zip(pts[:-1], pts[1:]):
        a = (int(px * c.W), int((1.0 - py) * c.H))
        b = (int(qx * c.W), int((1.0 - qy) * c.H))
        c.d.line((a[0], a[1], b[0], b[1]), fill=color, width=width)

def vline_event(c, x, y, w, h, t, color, label=None):
    px = x + (t / T) * w
    px_a = int(px * c.W)
    py_a = int((1.0 - y) * c.H)
    py_b = int((1.0 - (y + h)) * c.H)
    _dashed_line(c.d, px_a, py_b, px_a, py_a, color, 3, dash=14, gap=10)
    if label:
        draw_text(c, px + 0.005, y + h - 0.015, label,
                  size=16, color=color, italic=True, anchor='lt')

def hline(c, x, y, w, h, v, vmin, vmax, color, label=None, dashed=True):
    py = y + (v - vmin) / (vmax - vmin) * h
    px_a = int(x * c.W); px_b = int((x + w) * c.W)
    py_pixel = int((1.0 - py) * c.H)
    if dashed:
        _dashed_line(c.d, px_a, py_pixel, px_b, py_pixel, color, 2, dash=12, gap=8)
    else:
        c.d.line((px_a, py_pixel, px_b, py_pixel), fill=color, width=2)
    if label:
        draw_text(c, x + w + 0.005, py, label,
                  size=14, color=color, italic=True, anchor='lm')

# ---- panel: NDTI ---------------------------------------------------
x, y, w, h = axis_box(C, 'ndti', 'Optical  NDTI')
plot_line(C, x, y, w, h, days, ndti, -0.05, 0.55,
          color=COL['opt'][1], marker_face=COL['opt'][0])
vline_event(C, x, y, w, h, tillage_day, '#B83A35', 'tillage event')
draw_text(C, x + (24/T) * w, y + 0.06, 'data gap\n(cloud cover)',
          size=15, italic=True, color='#555', anchor='mm')

# ---- panel: γ ------------------------------------------------------
x, y, w, h = axis_box(C, 'gamma', 'SAR coherence  γ')
plot_line(C, x, y, w, h, days, gamma, 0.0, 1.0,
          color=COL['sar'][1], marker_face=COL['sar'][0])
hline(C, x, y, w, h, 0.25, 0.0, 1.0, '#704A20', 'γ = 0.25 threshold')
vline_event(C, x, y, w, h, tillage_day, '#B83A35')
draw_text(C, x + (45/T) * w, y + h - 0.04,
          'γ remains diagnostic\nthrough the cloud period',
          size=15, italic=True, color='#555', anchor='mm')

# ---- panel: H ------------------------------------------------------
x, y, w, h = axis_box(C, 'H', 'Optical entropy  H')
plot_line(C, x, y, w, h, days, H, 0.0, 1.05,
          color=COL['gate'][1], marker_face=COL['gate'][0])
hline(C, x, y, w, h, 0.65, 0.0, 1.05, '#9C7800', 'H = 0.65 gate')
vline_event(C, x, y, w, h, tillage_day, '#B83A35')
draw_text(C, x + (24/T) * w, y + h + 0.02,
          'H exceeds gate  ⇒  SAR module takes over',
          size=15, italic=True, color='#9C7800', anchor='mm')

# x-axis label at bottom
draw_text(C, 0.5, 0.07, 'Day of 2025 spring window',
          size=20, anchor='mm')

# legend at top of figure
def lg_swatch(cx, cy, color, label, marker_face):
    px = int(cx * C.W); py = int((1.0 - cy) * C.H)
    C.d.line((px - 24, py, px + 24, py), fill=color, width=3)
    C.d.ellipse((px - 6, py - 6, px + 6, py + 6),
                fill=marker_face, outline=color, width=2)
    draw_text(C, cx + 0.03, cy, label, size=16, anchor='lm')

lg_swatch(0.14, 0.93, COL['opt'][1],  'Optical NDTI', COL['opt'][0])
lg_swatch(0.30, 0.93, COL['sar'][1],  'SAR γ',         COL['sar'][0])
lg_swatch(0.40, 0.93, COL['gate'][1], 'Entropy H',     COL['gate'][0])
rect_filled(C, (0.52, 0.926), (0.03, 0.012), fill='#E8E8E8')
draw_text(C, 0.56, 0.932, 'cloudy period', size=16, anchor='lm')
draw_text(C, 0.72, 0.932, '┄ tillage event', size=16, color='#B83A35',
          anchor='lm')

out = os.path.join(os.path.dirname(__file__), 'fig_concept_C_signals.png')
C.save(out); print('saved:', out)
