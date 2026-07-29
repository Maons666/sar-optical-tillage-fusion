"""
Standalone sub-panels extracted from concept Fig A.

Generates eight focused PNGs (300 dpi).  Several panels (03, 05, 06) are
rendered text-free per author request — the labels in the docx caption
will be supplied separately.
"""
import os, math, random
from PIL import ImageDraw
from _pil_helpers import (
    Canvas, box, arrow, draw_text, rect_filled, _dashed_line, COL, font,
)

OUT = os.path.dirname(__file__)


# =====================================================================
# Reusable primitives
# =====================================================================
def satellite_icon(c, cx, cy, body_color, panel_color, size=0.08, accent='#FFFFFF'):
    bw, bh = size, size * 0.55
    px = int((cx - bw/2) * c.W); py = int((1 - cy - bh/2) * c.H)
    qx = int((cx + bw/2) * c.W); qy = int((1 - cy + bh/2) * c.H)
    c.d.rounded_rectangle((px, py, qx, qy), radius=10,
                          fill=body_color, outline='black', width=3)
    lpx0 = int((cx - bw/2 - size * 0.85) * c.W)
    lpy0 = int((1 - cy - bh/2 * 0.75) * c.H)
    lpx1 = int((cx - bw/2) * c.W)
    lpy1 = int((1 - cy + bh/2 * 0.75) * c.H)
    c.d.rectangle((lpx0, lpy0, lpx1, lpy1), fill=panel_color, outline='black', width=3)
    for k in range(4):
        xv = lpx0 + (k + 1) * (lpx1 - lpx0) // 5
        c.d.line((xv, lpy0, xv, lpy1), fill=accent, width=2)
    rpx0 = int((cx + bw/2) * c.W); rpx1 = int((cx + bw/2 + size * 0.85) * c.W)
    rpy0 = lpy0; rpy1 = lpy1
    c.d.rectangle((rpx0, rpy0, rpx1, rpy1), fill=panel_color, outline='black', width=3)
    for k in range(4):
        xv = rpx0 + (k + 1) * (rpx1 - rpx0) // 5
        c.d.line((xv, rpy0, xv, rpy1), fill=accent, width=2)


def sun_icon(c, cx, cy, r=0.04, color='#E6A91A'):
    px = int(cx * c.W); py = int((1 - cy) * c.H)
    rr = int(r * c.W)
    c.d.ellipse((px - rr, py - rr, px + rr, py + rr),
                fill=color, outline='#A77800', width=2)
    for k in range(8):
        ang = math.pi * 2 * k / 8
        x0 = px + int(rr * 1.25 * math.cos(ang))
        y0 = py + int(rr * 1.25 * math.sin(ang))
        x1 = px + int(rr * 1.90 * math.cos(ang))
        y1 = py + int(rr * 1.90 * math.sin(ang))
        c.d.line((x0, y0, x1, y1), fill=color, width=4)


def ray(c, p1, p2, color, width=3, head=0):
    """Single straight line; optional arrowhead at p2."""
    x1, y1 = c.P(*p1); x2, y2 = c.P(*p2)
    c.d.line((x1, y1, x2, y2), fill=color, width=width)
    if head:
        ang = math.atan2(y2 - y1, x2 - x1)
        left  = (x2 - head * math.cos(ang - math.pi/7),
                 y2 - head * math.sin(ang - math.pi/7))
        right = (x2 - head * math.cos(ang + math.pi/7),
                 y2 - head * math.sin(ang + math.pi/7))
        c.d.polygon([(x2, y2), left, right], fill=color)


# =====================================================================
# Sub-panel 01 — Sentinel-2 optical sensing
#   Rays diverge from a single sun point to multiple ground points,
#   then reflect upward and converge into the single satellite point.
# =====================================================================
def panel_01_sentinel2():
    C = Canvas(8.0, 6.0, dpi=300)
    draw_text(C, 0.5, 0.94, 'Sentinel-2 — optical sensing',
              size=36, bold=True, anchor='mm', color='#3F7A56')

    sat_x, sat_y = 0.18, 0.76
    sun_x, sun_y = 0.82, 0.76
    satellite_icon(C, sat_x, sat_y, body_color='#3F7A56',
                   panel_color='#558B40', size=0.10)
    draw_text(C, sat_x, 0.63, 'Sentinel-2',
              size=28, bold=True, anchor='mm', color='#3F7A56')
    sun_icon(C, sun_x, sun_y, r=0.045)
    draw_text(C, sun_x, 0.63, 'sunlight',
              size=26, italic=True, anchor='mm', color='#A77800')

    # ground swatch
    rect_filled(C, (0.14, 0.22), (0.72, 0.10),
                fill='#C9B98D', outline='#705B30', outline_w=3)
    draw_text(C, 0.50, 0.27, 'crop residue + soil surface',
              size=22, italic=True, color='#3A2A0E', anchor='mm')

    # 5 ground touch-down x-positions
    ground_xs = [0.22, 0.36, 0.50, 0.64, 0.78]
    ground_y_top = 0.32       # top of ground strip
    # sun emission point (slightly below the sun centre)
    sun_p = (sun_x, sun_y - 0.045)
    # satellite reception point (slightly below the body)
    sat_p = (sat_x, sat_y - 0.045)

    for gx in ground_xs:
        gp = (gx, ground_y_top)
        # incoming solar ray: from single sun point → ground point
        ray(C, sun_p, gp, color='#E6A91A', width=2, head=12)
        # reflected ray: from same ground point → single satellite point
        ray(C, gp, sat_p, color='#3F7A56', width=2, head=12)

    draw_text(C, 0.50, 0.10,
              'Solar rays diverge from a single source, illuminate the surface,\n'
              'and reflected rays converge at the Sentinel-2 sensor.',
              size=22, italic=True, anchor='mm', color='#333')
    C.save(os.path.join(OUT, 'sub_01_sentinel2.png'))
    print('saved sub_01_sentinel2.png')


# =====================================================================
# Sub-panel 02 — SWIR reflectance spectrum
#   Curves shape based on published spectra (Daughtry 2001/2004,
#   Hively et al. 2018).  Provided here as a CONCEPTUAL reference;
#   replace with USGS / ECOSTRESS spectral-library digitised values
#   for the final submission.
# =====================================================================
def panel_02_swir_spectrum():
    # Text-free version. Bolder lines & frame for use as a sub-element in
    # a larger composite figure. Curves are wheat-straw residue (green)
    # and Williams loam (brown), values after Daughtry (2001, 2004).
    C = Canvas(10.0, 6.0, dpi=300)

    AX = (0.08, 0.08, 0.88, 0.86)
    x0, y0, w, h = AX
    rect_filled(C, (x0, y0), (w, h), fill='white', outline='#333', outline_w=5)

    # ---- reflectance values, after Daughtry (2001) Agron. J. 93:125-131
    # and Daughtry (2004) Remote Sens. Environ. 90:126-134.
    # Wheat straw  – senescent residue, USGS/ECOSTRESS reference
    # Williams loam – dry mineral soil reference.
    spectra = [
        # wl    residue  bare_soil
        (0.50,  0.12,    0.10),
        (0.70,  0.22,    0.18),
        (0.90,  0.36,    0.25),
        (1.10,  0.45,    0.30),
        (1.30,  0.52,    0.33),
        (1.50,  0.53,    0.35),
        (1.65,  0.53,    0.36),
        (1.80,  0.49,    0.36),
        (1.90,  0.30,    0.22),    # atmospheric H2O band (both depressed)
        (2.00,  0.47,    0.31),
        (2.05,  0.46,    0.31),
        (2.10,  0.32,    0.31),    # cellulose absorption (residue only)
        (2.15,  0.45,    0.30),
        (2.20,  0.47,    0.29),    # clay 2.2 μm feature (soil only, shallow)
        (2.25,  0.45,    0.28),
        (2.30,  0.34,    0.27),    # lignin absorption (residue only)
        (2.35,  0.43,    0.27),
        (2.40,  0.45,    0.26),
        (2.50,  0.45,    0.25),
    ]
    wls       = [s[0] for s in spectra]
    res_vals  = [s[1] for s in spectra]
    soil_vals = [s[2] for s in spectra]

    # x-axis tick marks only (no labels)
    for wl in [0.5, 1.0, 1.5, 2.0, 2.3, 2.5]:
        xn = x0 + (wl - 0.5) / 2.0 * w
        px, py = C.P(xn, y0)
        C.d.line((px, py - 4, px, py + 18), fill='#333', width=4)

    # y-axis tick marks only (no labels)
    for v in [0.0, 0.2, 0.4, 0.6]:
        yn = y0 + 0.06 + v * (h - 0.10) / 0.6
        px, py = C.P(x0, yn)
        C.d.line((px - 18, py, px + 4, py), fill='#333', width=4)

    def xy(wl, v):
        xn = x0 + (wl - 0.5) / 2.0 * w
        yn = y0 + 0.06 + (v / 0.6) * (h - 0.10)
        return xn, yn

    # plot bare soil (thicker line)
    pts = [xy(wls[k], soil_vals[k]) for k in range(len(spectra))]
    for a, b in zip(pts[:-1], pts[1:]):
        px1, py1 = C.P(*a); px2, py2 = C.P(*b)
        C.d.line((px1, py1, px2, py2), fill='#B07C40', width=8)

    # plot crop residue (thickest line)
    pts = [xy(wls[k], res_vals[k]) for k in range(len(spectra))]
    for a, b in zip(pts[:-1], pts[1:]):
        px1, py1 = C.P(*a); px2, py2 = C.P(*b)
        C.d.line((px1, py1, px2, py2), fill='#3F7A56', width=10)

    C.save(os.path.join(OUT, 'sub_02_swir_spectrum.png'))
    print('saved sub_02_swir_spectrum.png')


# =====================================================================
# Sub-panel 03 — Crop-residue surface cover  (NO TEXT, visual only)
# =====================================================================
def panel_03_residue_strip():
    C = Canvas(10.0, 5.0, dpi=300)
    x0, y0, w, h = 0.05, 0.20, 0.90, 0.60
    rect_filled(C, (x0, y0), (w, h),
                fill='#C9B98D', outline='#705B30', outline_w=4)
    random.seed(12)
    # left half: dense residue
    for _ in range(220):
        rx = x0 + random.uniform(0.02, 0.48) * w
        ry0 = y0 + 0.08 * h; ry1 = y0 + 0.94 * h
        ang = random.uniform(-0.05, 0.05)
        px0 = int(rx * C.W); py0 = int((1 - ry0) * C.H)
        px1 = int((rx + ang) * C.W); py1 = int((1 - ry1) * C.H)
        C.d.line((px0, py0, px1, py1), fill='#7A6234', width=3)
    # right half: sparse residue
    for _ in range(35):
        rx = x0 + random.uniform(0.55, 0.98) * w
        ry0 = y0 + 0.44 * h; ry1 = y0 + 0.80 * h
        ang = random.uniform(-0.04, 0.04)
        px0 = int(rx * C.W); py0 = int((1 - ry0) * C.H)
        px1 = int((rx + ang) * C.W); py1 = int((1 - ry1) * C.H)
        C.d.line((px0, py0, px1, py1), fill='#7A6234', width=3)
    # divider
    px = int((x0 + 0.50 * w) * C.W)
    _dashed_line(C.d, px, int((1 - y0 - 0.97 * h) * C.H),
                       px, int((1 - y0 - 0.03 * h) * C.H),
                 '#333', 3, dash=18, gap=12)
    C.save(os.path.join(OUT, 'sub_03_residue_strip.png'))
    print('saved sub_03_residue_strip.png')


# =====================================================================
# Sub-panel 04 — Sentinel-1 SAR sensing
#   Show BOTH the transmitted pulse (sat → ground) AND the back-
#   scattered return (ground → sat) as two clear arrows.
# =====================================================================
def panel_04_sentinel1():
    C = Canvas(8.0, 6.0, dpi=300)
    draw_text(C, 0.5, 0.94, 'Sentinel-1 — SAR sensing',
              size=36, bold=True, anchor='mm', color='#B86C2C')

    sat_x, sat_y = 0.50, 0.78
    satellite_icon(C, sat_x, sat_y,
                   body_color='#B86C2C', panel_color='#D17D2E', size=0.10)
    draw_text(C, sat_x, 0.65, 'Sentinel-1',
              size=28, bold=True, anchor='mm', color='#B86C2C')

    # ground swatch
    rect_filled(C, (0.18, 0.18), (0.64, 0.10),
                fill='#C9A472', outline='#704A20', outline_w=3)
    draw_text(C, 0.50, 0.23, 'topsoil structural state',
              size=22, italic=True, color='#3A2A0E', anchor='mm')

    # Reflection geometry: both rays meet at one ground spot.
    # The two arrows diverge only at the satellite end (where the
    # antenna physically separates "emit" from "receive" in time);
    # at the ground they share essentially the same spot.
    ground_spot = (sat_x, 0.29)
    sat_left   = (sat_x - 0.05, sat_y - 0.045)
    sat_right  = (sat_x + 0.05, sat_y - 0.045)

    # transmitted pulse: from the satellite (slightly left) DOWN to the ground spot
    ray(C, sat_left, ground_spot, color='#B86C2C', width=4, head=18)
    draw_text(C, sat_x - 0.21, 0.50, 'transmitted\npulse',
              size=22, italic=True, bold=True, color='#B86C2C', anchor='mm')

    # backscattered return: from the SAME ground spot UP to the satellite (slightly right)
    ray(C, ground_spot, sat_right, color='#B86C2C', width=4, head=18)
    draw_text(C, sat_x + 0.21, 0.50, 'backscattered\nreturn',
              size=22, italic=True, bold=True, color='#B86C2C', anchor='mm')

    draw_text(C, 0.50, 0.07,
              'Active C-band radar: the sensor emits the pulse and records its return.\n'
              'Independent of solar illumination and cloud cover.',
              size=22, italic=True, anchor='mm', color='#333')
    C.save(os.path.join(OUT, 'sub_04_sentinel1.png'))
    print('saved sub_04_sentinel1.png')


# =====================================================================
# Sub-panel 05 — Scatterer rearrangement (LARGE canvas, NO TEXT)
# =====================================================================
def panel_05_scatterers():
    C = Canvas(18.0, 9.0, dpi=300)        # extra-large
    PX, PY, PW, PH = 0.04, 0.10, 0.42, 0.80
    PX2 = 0.54

    random.seed(7)
    N = 24
    HL = [3, 11, 18]
    HL_COL = ['#3F7A56', '#7E5BA0', '#B83A35']
    DEFAULT = '#B86C2C'
    pos_t1 = [(random.random(), random.random()) for _ in range(N)]
    radii  = [random.randint(15, 22) for _ in range(N)]
    cols   = [DEFAULT] * N
    for i, c_ in zip(HL, HL_COL):
        cols[i] = c_
    random.seed(13)
    pos_t2 = []
    for nx, ny in pos_t1:
        dx = random.uniform(-0.55, 0.55); dy = random.uniform(-0.55, 0.55)
        pos_t2.append((max(0.03, min(0.97, nx + dx)),
                       max(0.03, min(0.97, ny + dy))))

    def draw_panel(px, py, pw, ph, positions):
        rect_filled(C, (px, py), (pw, ph), fill='#FFF4E6',
                    outline='#B86C2C', outline_w=4)
        for (nx, ny), r, col in zip(positions, radii, cols):
            cx = px + 0.05 * pw + nx * 0.90 * pw
            cy = py + 0.05 * ph + ny * 0.90 * ph
            rpx = int(cx * C.W); rpy = int((1 - cy) * C.H)
            C.d.ellipse((rpx - r, rpy - r, rpx + r, rpy + r),
                        fill=col, outline='black', width=2)

    draw_panel(PX,  PY, PW, PH, pos_t1)
    draw_panel(PX2, PY, PW, PH, pos_t2)

    for i, col in zip(HL, HL_COL):
        nx1, ny1 = pos_t1[i]
        nx2, ny2 = pos_t2[i]
        p1 = (PX  + 0.05 * PW + nx1 * 0.90 * PW,
              PY  + 0.05 * PH + ny1 * 0.90 * PH)
        p2 = (PX2 + 0.05 * PW + nx2 * 0.90 * PW,
              PY  + 0.05 * PH + ny2 * 0.90 * PH)
        px1 = int(p1[0] * C.W); py1 = int((1 - p1[1]) * C.H)
        px2 = int(p2[0] * C.W); py2 = int((1 - p2[1]) * C.H)
        _dashed_line(C.d, px1, py1, px2, py2, col, 4, dash=18, gap=12)

    arrow(C, (PX + PW + 0.005, 0.50), (PX2 - 0.005, 0.50),
          width=6, head=32, color='#704A20')

    C.save(os.path.join(OUT, 'sub_05_scatterers.png'))
    print('saved sub_05_scatterers.png')


# =====================================================================
# Sub-panel 06 — Topsoil aggregates (NO TEXT)
# =====================================================================
def panel_06_aggregates():
    C = Canvas(13.0, 6.0, dpi=300)
    PX, PY, PW, PH = 0.04, 0.10, 0.42, 0.78
    PX2 = 0.54

    def soil_panel(px, py, pw, ph, intact):
        rect_filled(C, (px, py), (pw, ph), fill='#C9A472',
                    outline='#704A20', outline_w=4)
        random.seed(31 if intact else 73)
        n = 22 if intact else 50
        for _ in range(n):
            rx = px + random.uniform(0.05, 0.95) * pw
            ry = py + random.uniform(0.10, 0.92) * ph
            rad_norm = random.uniform(0.04, 0.09) * pw if intact else random.uniform(0.015, 0.035) * pw
            ppx = int(rx * C.W); ppy = int((1 - ry) * C.H)
            rr = int(rad_norm * C.W)
            C.d.ellipse((ppx - rr, ppy - rr, ppx + rr, ppy + rr),
                        fill='#8B6B33', outline='#4A3A1A', width=2)
        if intact:
            for _ in range(12):
                rx = px + random.uniform(0.10, 0.90) * pw
                ry = py + random.uniform(0.18, 0.85) * ph
                ppx = int(rx * C.W); ppy = int((1 - ry) * C.H)
                C.d.ellipse((ppx - 14, ppy - 14, ppx + 14, ppy + 14),
                            fill='#FFFFFF', outline='#704A20', width=2)

    soil_panel(PX,  PY, PW, PH, intact=True)
    soil_panel(PX2, PY, PW, PH, intact=False)

    arrow(C, (PX + PW + 0.005, 0.49), (PX2 - 0.005, 0.49),
          width=6, head=28, color='#704A20')

    C.save(os.path.join(OUT, 'sub_06_aggregates.png'))
    print('saved sub_06_aggregates.png')


# =====================================================================
# Sub-panel 07 — Entropy gate (horizontal threshold bar)
# =====================================================================
def panel_07_entropy_gauge():
    C = Canvas(10.0, 5.5, dpi=300)
    draw_text(C, 0.5, 0.93, 'Shannon entropy gate',
              size=34, bold=True, anchor='mm', color='#9C7800')

    # main bar
    x0, y0, w, h = 0.10, 0.42, 0.80, 0.12
    threshold = 0.65
    split_x = x0 + threshold * w
    # green left
    rect_filled(C, (x0, y0), (threshold * w, h),
                fill='#D5E4D8', outline='#3F7A56', outline_w=4)
    # orange right
    rect_filled(C, (split_x, y0), ((1 - threshold) * w, h),
                fill='#F3D6BD', outline='#B86C2C', outline_w=4)

    # zone labels INSIDE the bar
    draw_text(C, x0 + 0.5 * threshold * w, y0 + h/2,
              'OPTICAL stream', size=26, bold=True,
              anchor='mm', color='#3F7A56')
    draw_text(C, split_x + 0.5 * (1 - threshold) * w, y0 + h/2,
              'SAR stream', size=26, bold=True,
              anchor='mm', color='#B86C2C')

    # tick marks + labels BELOW the bar
    ticks = [0.0, 0.25, 0.50, 0.65, 0.85, 1.0]
    for v in ticks:
        xn = x0 + v * w
        px, py = C.P(xn, y0)
        C.d.line((px, py + 4, px, py + 18), fill='#333', width=3)
        draw_text(C, xn, y0 - 0.045, f'{v:.2f}'.rstrip('0').rstrip('.'),
                  size=22, anchor='mm')
    draw_text(C, x0 + w/2, y0 - 0.10, 'Shannon entropy  H',
              size=22, italic=True, anchor='mm')

    # threshold marker (red downward arrow + label ABOVE the bar)
    arrow(C, (split_x, y0 + h + 0.13), (split_x, y0 + h + 0.005),
          width=5, head=22, color='#B83A35')
    draw_text(C, split_x, y0 + h + 0.18,
              'GATE   H = 0.65', size=24, bold=True,
              anchor='mm', color='#B83A35')

    # legend below ticks
    draw_text(C, 0.50, 0.05,
              'H  <  0.65   →   optical prediction is accepted              '
              'H  ≥  0.65   →   SAR coherence module overrides',
              size=20, italic=True, anchor='mm', color='#333')

    C.save(os.path.join(OUT, 'sub_07_entropy_gauge.png'))
    print('saved sub_07_entropy_gauge.png')


# =====================================================================
# Sub-panel 08 — Fused field-level map (edge-aligned tiled grid)
# =====================================================================
def panel_08_field_map():
    C = Canvas(9.0, 5.5, dpi=300)
    draw_text(C, 0.5, 0.93, 'Fused field-level tillage map',
              size=32, bold=True, anchor='mm', color='#7E5BA0')

    x0, y0, w, h = 0.06, 0.18, 0.88, 0.62
    # outer frame
    rect_filled(C, (x0, y0), (w, h), fill='white', outline='#333', outline_w=3)

    random.seed(99)
    rows, cols = 5, 10
    cell_w = w / cols
    cell_h = h / rows
    for i in range(rows):
        for j in range(cols):
            px = x0 + j * cell_w
            py = y0 + i * cell_h
            tilled = random.random() < 0.44
            fc = '#F3D6BD' if tilled else '#E2F0DA'
            ec = '#B86C2C' if tilled else '#3F7A56'
            rect_filled(C, (px, py), (cell_w, cell_h),
                        fill=fc, outline=ec, outline_w=2)

    # legend boxes
    box(C, (0.10, 0.86), (0.20, 0.05),
        'tilled', fc='#F3D6BD', ec='#B86C2C',
        fontsize=22, bold=True, text_color='#704A20')
    box(C, (0.34, 0.86), (0.26, 0.05),
        'untilled (no-till)', fc='#E2F0DA', ec='#3F7A56',
        fontsize=22, bold=True, text_color='#3F7A56')

    draw_text(C, 0.50, 0.08,
              'USDA CSB polygons coloured by the final fused tillage decision.\n'
              'Pixel-level noise is suppressed by zonal aggregation within each parcel.',
              size=22, italic=True, anchor='mm', color='#333')

    C.save(os.path.join(OUT, 'sub_08_field_map.png'))
    print('saved sub_08_field_map.png')


# =====================================================================
if __name__ == '__main__':
    panel_01_sentinel2()
    panel_02_swir_spectrum()
    panel_03_residue_strip()
    panel_04_sentinel1()
    panel_05_scatterers()
    panel_06_aggregates()
    panel_07_entropy_gauge()
    panel_08_field_map()
