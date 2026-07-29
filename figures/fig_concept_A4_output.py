"""
Concept A4 — Fused field-level tillage map (standalone).
"""
import os, random
from _pil_helpers import Canvas, box, draw_text, rect_filled

C = Canvas(12.0, 7.0, dpi=300)
draw_text(C, 0.5, 0.94,
          'Fused field-level tillage map (CSB parcel aggregation)',
          size=36, bold=True, anchor='mm')

# ============================================================
# Field map (edge-aligned tiled grid, FULL WIDTH)
# ============================================================
FM_X, FM_Y, FM_W, FM_H = 0.05, 0.20, 0.90, 0.62
rect_filled(C, (FM_X, FM_Y), (FM_W, FM_H),
            fill='white', outline='#333', outline_w=4)

random.seed(99)
rows, cols_n = 6, 12
cell_w = FM_W / cols_n; cell_h = FM_H / rows
for i in range(rows):
    for j in range(cols_n):
        px = FM_X + j * cell_w
        py = FM_Y + i * cell_h
        tilled = random.random() < 0.44
        fc = '#F3D6BD' if tilled else '#E2F0DA'
        ec = '#B86C2C' if tilled else '#3F7A56'
        rect_filled(C, (px, py), (cell_w, cell_h),
                    fill=fc, outline=ec, outline_w=2)

# legend boxes
box(C, (0.07, 0.085), (0.16, 0.060),
    'tilled', fc='#F3D6BD', ec='#B86C2C',
    fontsize=30, bold=True, text_color='#704A20')
box(C, (0.27, 0.085), (0.26, 0.060),
    'untilled (no-till)', fc='#E2F0DA', ec='#3F7A56',
    fontsize=30, bold=True, text_color='#3F7A56')

# caption
draw_text(C, 0.78, 0.115,
          'USDA CSB polygons coloured by fused decision',
          size=22, italic=True, anchor='mm', color='#333')

C.save(os.path.join(os.path.dirname(__file__), 'fig_concept_A4_output.png'))
print('saved fig_concept_A4_output.png  ', C.W, 'x', C.H)
