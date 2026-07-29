"""
Concept A3 — Entropy gate (standalone horizontal threshold bar).
"""
import os
from _pil_helpers import Canvas, box, arrow, draw_text, rect_filled

C = Canvas(14.0, 5.5, dpi=300)
draw_text(C, 0.5, 0.93,
          'Shannon entropy gate — dynamic switch between optical and SAR streams',
          size=36, bold=True, anchor='mm')

# ============================================================
# Horizontal threshold bar
# ============================================================
GATE_X, GATE_Y, GATE_W, GATE_H = 0.07, 0.40, 0.86, 0.20
threshold = 0.65
split_x = GATE_X + threshold * GATE_W

rect_filled(C, (GATE_X, GATE_Y), (threshold * GATE_W, GATE_H),
            fill='#D5E4D8', outline='#3F7A56', outline_w=6)
rect_filled(C, (split_x, GATE_Y), ((1 - threshold) * GATE_W, GATE_H),
            fill='#F3D6BD', outline='#B86C2C', outline_w=6)

draw_text(C, GATE_X + 0.5 * threshold * GATE_W, GATE_Y + GATE_H/2,
          'OPTICAL stream\n(H < 0.65)',
          size=40, bold=True, anchor='mm', color='#3F7A56')
draw_text(C, split_x + 0.5 * (1 - threshold) * GATE_W, GATE_Y + GATE_H/2,
          'SAR stream\n(H ≥ 0.65)',
          size=40, bold=True, anchor='mm', color='#B86C2C')

# tick marks + labels below
for v in [0.0, 0.25, 0.50, 0.65, 0.85, 1.0]:
    xn = GATE_X + v * GATE_W
    px, py = C.P(xn, GATE_Y)
    C.d.line((px, py - 5, px, py + 22), fill='#333', width=4)
    draw_text(C, xn, GATE_Y - 0.045,
              f'{v:.2f}'.rstrip('0').rstrip('.'),
              size=28, anchor='mm')
draw_text(C, GATE_X + GATE_W/2, GATE_Y - 0.110,
          'Shannon entropy  H', size=32, italic=True, anchor='mm')

# threshold red marker above bar
arrow(C, (split_x, GATE_Y + GATE_H + 0.085),
         (split_x, GATE_Y + GATE_H + 0.005),
      width=7, head=32, color='#B83A35')
draw_text(C, split_x, GATE_Y + GATE_H + 0.120,
          'GATE   H = 0.65',
          size=32, bold=True, anchor='mm', color='#B83A35')

C.save(os.path.join(os.path.dirname(__file__), 'fig_concept_A3_gate.png'))
print('saved fig_concept_A3_gate.png  ', C.W, 'x', C.H)
