# -*- coding: utf-8 -*-
"""Tables and figure data for the threshold-sensitivity section, from the output of fusion_sweep_samples.py.

Same deliverables as make_tables_and_figure.py, for the sample-based run (fixed cropland pixels, Sentinel-1
GRD stand-in). Differences: the tillage fraction of the final week is the CUMULATIVE pixel-level share
(pct_tilled_cum), a column "no observation" is reported, and there is no field-level column.

Input : <inputs>/rule_shares_<MMDD>.csv
        <routing>/gate_sweep_target_<order>.csv   (optional, written by routing_without_slc.py)
Output: <out>/dat_rule_shares.dat, dat_sens_gamma_low.dat, dat_sens_gamma_high.dat, dat_sens_T.dat,
        dat_gate_target.dat, tab_rule_shares.tex, tab_threshold_sensitivity.tex, summary.txt

Usage : conda run -n geo python make_tables_and_figure_samples.py --inputs ../output_grd/proxy_fitted
            --gate ../output_no_slc/gate_sweep_target_fitted.csv --out ../output_grd/proxy_fitted/figure
            --first-week 0406 --final-week 0622 --standin "amplitude-correlation stand-in"
"""
import argparse
import glob
import os
import re

import pandas as pd

BASE = {'T': 0.65, 'gamma_low': 0.25, 'gamma_high': 0.60}
MONTH = {'03': 'Mar', '04': 'Apr', '05': 'May', '06': 'Jun'}


def label(tag):
    return '%d %s' % (int(tag[2:]), MONTH[tag[:2]])


def base_row(df):
    return df[(df[list(BASE)].round(2) == pd.Series(BASE)).all(axis=1)].iloc[0]


def one_free(df, free):
    fixed = {k: v for k, v in BASE.items() if k != free}
    return df[(df[list(fixed)].round(2) == pd.Series(fixed)).all(axis=1)].sort_values(free)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', required=True)
    ap.add_argument('--gate', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--first-week', default='0406')
    ap.add_argument('--final-week', default='0622')
    ap.add_argument('--standin', default='Sentinel-1 stand-in', help='name of the SAR quantity, used in the captions')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    weeks = {}
    for f in sorted(glob.glob(os.path.join(a.inputs, 'rule_shares_*.csv'))):
        tag = re.search(r'rule_shares_(\d{4})\.csv$', f).group(1)
        if a.first_week <= tag <= a.final_week:
            weeks[tag] = pd.read_csv(f, dtype={'tag': str})
    if not weeks:
        raise SystemExit('no rule_shares_<MMDD>.csv between %s and %s in %s' % (a.first_week, a.final_week, a.inputs))
    lines = ['weeks: %s to %s (%d)' % (label(min(weeks)), label(max(weeks)), len(weeks))]

    # ------------------------------------------------------------ rule shares per week, baseline thresholds
    rows = []
    for tag, df in sorted(weeks.items()):
        b = base_row(df)
        rows.append(dict(tag=tag, week=label(tag), opt=b.pct_optical_accepted, r1=b.pct_cloud_override, r2=b.pct_enhance,
                         r3=b.pct_stability, noobs=b.pct_no_observation, tp=b.pct_tilled_pixel, tcum=b.pct_tilled_cum))
    rs = pd.DataFrame(rows)
    with open(os.path.join(a.out, 'dat_rule_shares.dat'), 'w', encoding='ascii', newline='\n') as fh:
        fh.write('tag week opt r1 r2 r3 noobs tp tcum\n')
        for r in rows:
            fh.write('%s {%s} %.2f %.2f %.2f %.2f %.2f %.2f %.2f\n' % (r['tag'], r['week'], r['opt'], r['r1'], r['r2'], r['r3'],
                                                                     r['noobs'], r['tp'], r['tcum']))
    tex = [r'\begin{table}[!htbp]', r'  \centering',
           r'  \caption{Share of the sampled cropland pixels decided by each branch of the fusion logic at the baseline thresholds ($\pmax = 0.65$, $\glow = 0.25$, $\ghigh = 0.60$), by weekly window, Nebraska 2025, with the %s in place of the coherence layer. The four shares refer to the pixels that received a decision and sum to 100\%%; pixels under cloud without a Sentinel-1 value received none and are given as a share of all pixels.}' % a.standin,
           r'  \label{tab:rule-shares}', r'  \small', r'  \setlength{\tabcolsep}{5pt}',
           r'  \begin{tabular}{@{}l r r r r r r@{}}', r'    \toprule',
           r'    Week ending & Optical accepted (\%) & Rule 1: cloud override (\%) & Rule 2: enhancement (\%) & Rule 3: stability (\%) & No observation (\%) & Tilled, cumulative (\%) \\',
           r'    \midrule']
    for r in rows:
        tex.append('    ' + ' & '.join([r['week']] + ['%.1f' % r[k] for k in ('opt', 'r1', 'r2', 'r3', 'noobs', 'tcum')]) + r' \\')
    tex += [r'    \bottomrule', r'  \end{tabular}', r'\end{table}']
    open(os.path.join(a.out, 'tab_rule_shares.tex'), 'w', encoding='utf-8', newline='\n').write('\n'.join(tex) + '\n')
    lines.append('rule 1 decided %.1f-%.1f%% of decided pixels per week (mean %.1f%%)' % (rs.r1.min(), rs.r1.max(), rs.r1.mean()))
    lines.append('rules 2+3 together %.2f-%.2f%% per week (mean %.2f%%); rule 2 mean %.2f%%, rule 3 mean %.2f%%'
                 % ((rs.r2 + rs.r3).min(), (rs.r2 + rs.r3).max(), (rs.r2 + rs.r3).mean(), rs.r2.mean(), rs.r3.mean()))
    lines.append('no observation (cloud, no Sentinel-1 value) %.1f-%.1f%% of all pixels per week' % (rs.noobs.min(), rs.noobs.max()))
    lines.append('cumulative tilled share at baseline, %s: %.1f%%' % (label(a.final_week), rs.tcum.iloc[-1]))

    # ------------------------------------------------------------ threshold sensitivity, final week, cumulative share
    df = weeks[a.final_week]
    names = (('gamma_low', r'$\glow$'), ('gamma_high', r'$\ghigh$'), ('T', r'$\pmax$ gate $T$'))
    tex = [r'\begin{table}[!htbp]', r'  \centering',
           r'  \caption{Sensitivity of the cumulative pixel-level tillage share on %s to each decision threshold, the other two held at their baseline values (in bold), with the %s in place of the coherence layer.}' % (label(a.final_week), a.standin),
           r'  \label{tab:threshold-sensitivity}', r'  \small', r'  \begin{tabular}{@{}l l l l l l@{}}', r'    \toprule',
           r'    Threshold & \multicolumn{5}{l}{Value tested $\rightarrow$ tillage share (\%)} \\', r'    \midrule']
    for free, lab in names:
        d = one_free(df, free)
        d[[free, 'pct_tilled_pixel', 'pct_tilled_cum']].to_csv(os.path.join(a.out, 'dat_sens_%s.dat' % free), sep=' ', index=False,
                                                              float_format='%.3f', lineterminator='\n')
        near = d[(d[free] - BASE[free]).abs() < 0.101]
        cells = []
        for _, r in near.iterrows():
            c = '%.2f $\\rightarrow$ %.1f' % (r[free], r.pct_tilled_cum)
            cells.append(r'\textbf{%s}' % c if abs(r[free] - BASE[free]) < 1e-6 else c)
        tex.append('    %s & %s \\\\' % (lab, ' & '.join(cells)))
        b = d[(d[free] - BASE[free]).abs() < 1e-6].pct_tilled_cum.iloc[0]
        lo = d[(d[free] - (BASE[free] - 0.05)).abs() < 1e-6].pct_tilled_cum
        hi = d[(d[free] - (BASE[free] + 0.05)).abs() < 1e-6].pct_tilled_cum
        lines.append('%s -0.05 / +0.05 changes the cumulative share on %s by %+.2f / %+.2f pp (full range tested %.1f-%.1f%%)'
                     % (free, label(a.final_week), lo.iloc[0] - b, hi.iloc[0] - b, d.pct_tilled_cum.min(), d.pct_tilled_cum.max()))
    tex += [r'    \bottomrule', r'  \end{tabular}', r'\end{table}']
    open(os.path.join(a.out, 'tab_threshold_sensitivity.tex'), 'w', encoding='utf-8', newline='\n').write('\n'.join(tex) + '\n')

    # ------------------------------------------------------------ gate sweep on the target pixels (no labels)
    if a.gate and os.path.exists(a.gate):
        g = pd.read_csv(a.gate)
        g[['T', 'pct_of_clear_retained']].rename(columns={'pct_of_clear_retained': 'retained'}).to_csv(
            os.path.join(a.out, 'dat_gate_target.dat'), sep=' ', index=False, float_format='%.2f', lineterminator='\n')
        r = g.set_index(g['T'].round(2)).pct_of_clear_retained
        lines.append('gate: clear pixels kept by the optical channel %.1f%% at T=0.65 (%.1f%% at 0.60, %.1f%% at 0.70); weeks of the gate file pooled'
                     % (r[0.65], r[0.60], r[0.70]))
    open(os.path.join(a.out, 'summary.txt'), 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('written to', a.out)


if __name__ == '__main__':
    main()
