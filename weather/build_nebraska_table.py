"""
B3 — merge the three primary sources into one weekly table for Nebraska.

inputs  (data/)
    B3_nass_weekly_12states_2025.csv          USDA NASS Crop Progress (national reports)
    B3_usdm_nebraska_2025.csv                 U.S. Drought Monitor, cumulative % area
    B3_gee_weekly_coverage_nass_aligned.csv   Earth Engine, NASS-aligned weeks
output
    B3_nebraska_weekly_conditions_2025.csv
"""
import csv, datetime, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RES = os.path.join(ROOT, 'data')


def load(name):
    with open(os.path.join(RES, name), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


nass = {r['week_ending']: r for r in load('B3_nass_weekly_12states_2025.csv') if r['state'] == 'Nebraska'}
usdm = {r['map_date']: r for r in load('B3_usdm_nebraska_2025.csv')}
gee = {r['week_ending_sun']: r for r in load('B3_gee_weekly_coverage_nass_aligned.csv')}

rows = []
for we in sorted(gee):
    sun = datetime.date.fromisoformat(we)
    tue = (sun - datetime.timedelta(days=5)).isoformat()          # USDM map issued on the Tuesday of that week
    n, u, g = nass[we], usdm[tue], gee[we]
    short = float(n['topsoil_vs']) + float(n['topsoil_s'])
    rows.append(dict(
        week_ending=we,
        days_suitable=n['days_suitable'],
        topsoil_short_or_very_short_pct=f'{short:.0f}',
        corn_planted_pct=(f"{float(n['corn_planted']):.0f}" if n['corn_planted'] else ''),
        corn_planted_5yr_avg_pct=(f"{float(n['corn_planted_avg']):.0f}" if n['corn_planted_avg'] else ''),
        usdm_map_date=tue,
        drought_D1_D4_pct_area=f"{float(u['pct_D1_or_worse']):.1f}",
        drought_D2_D4_pct_area=f"{float(u['pct_D2_or_worse']):.1f}",
        s2_clear_pct_cropland=f"{float(g['s2_usable_pct']):.1f}",
        s2_mean_clear_obs=g['s2_mean_clear_obs'],
        s1_present_pct_cropland=f"{float(g['s1_present_pct']):.1f}",
        s1_or_s2_pct_cropland=f"{float(g['fused_pct']):.1f}",
    ))

out = os.path.join(RES, 'B3_nebraska_weekly_conditions_2025.csv')
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print('wrote', out, f'({len(rows)} weeks)')

s2 = [float(r['s2_clear_pct_cropland']) for r in rows]
fu = [float(r['s1_or_s2_pct_cropland']) for r in rows]
mean = lambda v: sum(v) / len(v)
cloudy = [i for i, r in enumerate(rows) if '2025-05-18' <= r['week_ending'] <= '2025-06-08']
early = [i for i, r in enumerate(rows) if r['week_ending'] <= '2025-05-11']
print(f'13-week mean      : S2 {mean(s2):.1f}%   S1|S2 {mean(fu):.1f}%   gap {mean(fu)-mean(s2):.1f} pp')
print(f'6 weeks to 11 May : S2 {min(s2[i] for i in early):.1f}-{max(s2[i] for i in early):.1f}%')
print(f'4 weeks 12May-8Jun: S2 {mean([s2[i] for i in cloudy]):.1f}% ({min(s2[i] for i in cloudy):.1f}-{max(s2[i] for i in cloudy):.1f})   '
      f'S1|S2 {mean([fu[i] for i in cloudy]):.1f}% ({min(fu[i] for i in cloudy):.1f}-{max(fu[i] for i in cloudy):.1f})   '
      f'gap {mean([fu[i] for i in cloudy]) - mean([s2[i] for i in cloudy]):.1f} pp')
