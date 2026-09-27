# -*- coding: utf-8 -*-
"""Every accuracy figure quoted in the manuscript, derived from the confusion matrix of Table 4.

Table 4 (authoritative, per the author's decision of 2026-09-17):
    TP = 11,328   FN = 1,397   FP = 1,345   TN = 11,323      (n = 25,393)

The bootstrap resamples the 25,393 hold-out pixels with replacement; because a pixel is fully
described by the cell it falls in, this equals a multinomial resample of the four cells.

Run:  conda run -n geo python metrics_from_table4.py
"""
import os as _os
_REPO = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
_DATA = _os.path.join(_REPO, 'data')        # inputs and outputs, not part of the repository
_MODELS = _os.path.join(_REPO, 'models')    # tillage_classifier.pkl, available on request
import os

import numpy as np

TP, FN, FP, TN = 11328, 1397, 1345, 11323
OUT = _os.path.join(_DATA, 'metrics_from_table4.txt')


def metrics(tp, fn, fp, tn):
    tp, fn, fp, tn = [np.asarray(v, dtype=float) for v in (tp, fn, fp, tn)]
    n = tp + fn + fp + tn
    oa = (tp + tn) / n
    prec = tp / (tp + fp)
    rec = tp / (tp + fn)
    spec = tn / (tn + fp)
    f1 = 2 * tp / (2 * tp + fp + fn)
    ba = (rec + spec) / 2
    pe = ((tp + fn) * (tp + fp) + (fp + tn) * (fn + tn)) / n ** 2
    kappa = (oa - pe) / (1 - pe)
    mcc = (tp * tn - fp * fn) / np.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return dict(OA=oa, Precision=prec, Recall=rec, Specificity=spec, F1=f1, BalancedAccuracy=ba, Kappa=kappa, MCC=mcc)


n = TP + FN + FP + TN
point = metrics(TP, FN, FP, TN)
rng = np.random.RandomState(42)
draws = rng.multinomial(n, [TP / n, FN / n, FP / n, TN / n], size=1000)
boot = metrics(draws[:, 0], draws[:, 1], draws[:, 2], draws[:, 3])

lines = ['Confusion matrix (Table 4): TP=%d FN=%d FP=%d TN=%d  n=%d' % (TP, FN, FP, TN, n),
         'Actual Tilled     = %d (%.2f%%)' % (TP + FN, 100.0 * (TP + FN) / n),
         'Actual Not tilled = %d (%.2f%%)' % (FP + TN, 100.0 * (FP + TN) / n),
         'Predicted Tilled  = %d (%.2f%%)' % (TP + FP, 100.0 * (TP + FP) / n), '']
for k in ('OA', 'BalancedAccuracy', 'Precision', 'Recall', 'Specificity', 'F1', 'Kappa', 'MCC'):
    lo, hi = np.percentile(boot[k], [2.5, 97.5])
    if k in ('Kappa', 'MCC'):
        lines.append('%-17s %.3f    1,000-resample bootstrap 95%% CI [%.3f, %.3f]' % (k, point[k], lo, hi))
    else:
        lines.append('%-17s %.2f%%   1,000-resample bootstrap 95%% CI [%.2f, %.2f]%%' % (k, 100 * point[k], 100 * lo, 100 * hi))
lines.append('')
lines.append('Precision - Recall = %.2f percentage points' % (100 * (point['Precision'] - point['Recall'])))
lines.append('Missed Tilled pixels: %.2f%% of actual Tilled (about one in %.1f)' % (100 * (1 - point['Recall']), 1 / (1 - point['Recall'])))
txt = '\n'.join(lines)
print(txt)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(txt + '\n')
