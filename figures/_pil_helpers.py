"""
PIL-based publication-figure helpers for Till v0.9.

All drawing functions accept normalized 0-1 coordinates (origin top-left)
and convert internally to pixels. This lets layout code stay resolution-
independent. Default canvas is 3600x2400 px (= 12x8 in at 300 dpi).
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

# ---- color palette (face, edge) ------------------------------------
COL = {
    'input': ('#E5EEF7', '#3B6FB6'),
    'proc':  ('#F2F2F2', '#666666'),
    'out':   ('#E2F0DA', '#558B40'),
    'dec':   ('#FFF4D9', '#C99700'),
    'opt':   ('#D5E4D8', '#3F7A56'),
    'sar':   ('#F3D6BD', '#B86C2C'),
    'fuse':  ('#E3D8E9', '#7E5BA0'),
    'gt':    ('#FCE4E4', '#B83A35'),
    'gate':  ('#FFEDB0', '#9C7800'),
}

# ---- font loading --------------------------------------------------
def _font_path(name_candidates):
    for n in name_candidates:
        for d in ['C:/Windows/Fonts', 'C:\\Windows\\Fonts']:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None

FONT_REG  = _font_path(['times.ttf', 'arial.ttf'])
FONT_BOLD = _font_path(['timesbd.ttf', 'arialbd.ttf'])
FONT_ITAL = _font_path(['timesi.ttf', 'ariali.ttf'])
_font_cache = {}

def font(size, bold=False, italic=False):
    key = (size, bold, italic)
    if key in _font_cache:
        return _font_cache[key]
    path = FONT_BOLD if bold else (FONT_ITAL if italic else FONT_REG)
    if path is None:
        f = ImageFont.load_default()
    else:
        f = ImageFont.truetype(path, size)
    _font_cache[key] = f
    return f


# ---- canvas wrapper ------------------------------------------------
class Canvas:
    def __init__(self, w_in, h_in, dpi=300, bg='white'):
        self.W = int(round(w_in * dpi))
        self.H = int(round(h_in * dpi))
        self.dpi = dpi
        self.img = Image.new('RGB', (self.W, self.H), bg)
        self.d = ImageDraw.Draw(self.img)

    # convert normalized (x, y) — y is "up" semantically — into pixels
    def P(self, x, y):
        return (int(x * self.W), int((1.0 - y) * self.H))

    def Pwh(self, x, y, w, h):
        # box top-left in PIL = (x_left, y_top)
        return (int(x * self.W), int((1.0 - y - h) * self.H),
                int((x + w) * self.W), int((1.0 - y) * self.H))

    def save(self, path):
        self.img.save(path)
        return path


# ---- primitives ----------------------------------------------------
def box(c, xy, wh, text, key='proc', fontsize=22, bold=False, italic=False,
        outline_w=2, radius=14, fc=None, ec=None, text_color='black',
        align='center'):
    """xy, wh in normalized 0-1 coords."""
    x, y = xy; w, h = wh
    if fc is None or ec is None:
        fc_d, ec_d = COL[key]
        fc = fc or fc_d; ec = ec or ec_d
    px0, py0, px1, py1 = c.Pwh(x, y, w, h)
    c.d.rounded_rectangle((px0, py0, px1, py1), radius=radius,
                          fill=fc, outline=ec, width=outline_w)
    cx = (px0 + px1) // 2; cy = (py0 + py1) // 2
    draw_text(c, cx / c.W, 1.0 - cy / c.H, text,
              size=fontsize, bold=bold, italic=italic, color=text_color,
              anchor='mm', align=align)


def draw_text(c, x, y, text, size=22, bold=False, italic=False,
              color='black', anchor='mm', align='center'):
    f = font(size, bold=bold, italic=italic)
    px, py = c.P(x, y)
    if '\n' in text:
        c.d.multiline_text((px, py), text, font=f, fill=color,
                           anchor=anchor, align=align, spacing=4)
    else:
        c.d.text((px, py), text, font=f, fill=color, anchor=anchor)


def arrow(c, p1, p2, color='#222', width=3, head=18, dashed=False):
    """p1, p2 in normalized coords (y up)."""
    x1, y1 = c.P(*p1)
    x2, y2 = c.P(*p2)
    if dashed:
        _dashed_line(c.d, x1, y1, x2, y2, color, width)
    else:
        c.d.line((x1, y1, x2, y2), fill=color, width=width)
    # arrow head
    ang = math.atan2(y2 - y1, x2 - x1)
    hx = x2; hy = y2
    left  = (hx - head * math.cos(ang - math.pi/7),
             hy - head * math.sin(ang - math.pi/7))
    right = (hx - head * math.cos(ang + math.pi/7),
             hy - head * math.sin(ang + math.pi/7))
    c.d.polygon([(hx, hy), left, right], fill=color)


def _dashed_line(d, x1, y1, x2, y2, color, width, dash=12, gap=8):
    L = math.hypot(x2 - x1, y2 - y1)
    if L == 0: return
    n = int(L // (dash + gap))
    ux = (x2 - x1) / L; uy = (y2 - y1) / L
    pos = 0
    for _ in range(n + 1):
        sx = x1 + ux * pos; sy = y1 + uy * pos
        ex = x1 + ux * min(pos + dash, L); ey = y1 + uy * min(pos + dash, L)
        d.line((sx, sy, ex, ey), fill=color, width=width)
        pos += dash + gap


def rect_filled(c, xy, wh, fill, outline=None, outline_w=0):
    x, y = xy; w, h = wh
    px0, py0, px1, py1 = c.Pwh(x, y, w, h)
    if outline:
        c.d.rectangle((px0, py0, px1, py1), fill=fill, outline=outline, width=outline_w)
    else:
        c.d.rectangle((px0, py0, px1, py1), fill=fill)


def hline_dashed(c, x1, x2, y, color='#444', width=2, dash=10, gap=6):
    px1, py = c.P(x1, y); px2, _ = c.P(x2, y)
    _dashed_line(c.d, px1, py, px2, py, color, width, dash, gap)


def vline_dashed(c, x, y1, y2, color='#444', width=2, dash=10, gap=6):
    px, py1 = c.P(x, y1); _, py2 = c.P(x, y2)
    _dashed_line(c.d, px, py1, px, py2, color, width, dash, gap)
