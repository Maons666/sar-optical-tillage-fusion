"""
Evaluation of the baseline optical Random Forest classifier (Section 4.1).

Protocol
--------
* The labelled pixels are split into a training and a hold-out partition at the
  field level: every pixel of a given field goes entirely into one partition, so
  spatially autocorrelated pixels of the same field never appear on both sides
  (grouped hold-out; --field-col names the column that identifies the field).
* Class balance is handled at the sampling stage, i.e. the labelled sample is
  balanced between the Tilled and Not Tilled classes before training; the
  classifier is therefore trained WITHOUT class weights.
* Random Forest with 200 trees (the model used for mapping).
* Reported on the hold-out partition: confusion matrix, Overall Accuracy with a
  1,000-resample bootstrap 95% CI, Balanced Accuracy, Precision, Recall and F1 of
  the Tilled class, Cohen's kappa and the Matthews correlation coefficient
  (the panel of Table 5).

USAGE
-----
    python evaluation/evaluate_holdout.py --csv path/to/training_pixels.csv \
        --field-col field_id --label-col tillage --tilled-class 1

    --holdout-fraction   share of FIELDS held out (default 0.2)
    --seed               random seed for the field split and the bootstrap
"""

import argparse

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, cohen_kappa_score,
                             confusion_matrix, f1_score, matthews_corrcoef, precision_score,
                             recall_score)
from sklearn.model_selection import GroupShuffleSplit

FEATURES = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'NDSI', 'BSI', 'NDBSI', 'NDTI']


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--csv', required=True)
    p.add_argument('--field-col', required=True,
                   help='column identifying the field (polygon) each pixel belongs to')
    p.add_argument('--label-col', default='tillage')
    p.add_argument('--tilled-class', type=int, default=1, help='label value that codes "Tilled"')
    p.add_argument('--holdout-fraction', type=float, default=0.20)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--n-estimators', type=int, default=200)
    p.add_argument('--bootstrap', type=int, default=1000)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    missing = [c for c in FEATURES + [args.label_col, args.field_col] if c not in df.columns]
    if missing:
        raise SystemExit('missing columns in the CSV: %s' % missing)
    X = df[FEATURES].to_numpy(dtype=float)
    y = (df[args.label_col].to_numpy() == args.tilled_class).astype(int)   # 1 = Tilled
    groups = df[args.field_col].to_numpy()
    print('>> %d pixels from %d fields | Tilled %d (%.2f%%), Not tilled %d'
          % (len(df), len(np.unique(groups)), y.sum(), 100 * y.mean(), len(y) - y.sum()))

    # field-level hold-out: whole fields go to one side only
    split = GroupShuffleSplit(n_splits=1, test_size=args.holdout_fraction, random_state=args.seed)
    tr, te = next(split.split(X, y, groups))
    assert not set(groups[tr]) & set(groups[te])
    print('>> training: %d pixels / %d fields | hold-out: %d pixels / %d fields (Tilled %d, Not tilled %d)'
          % (len(tr), len(np.unique(groups[tr])), len(te), len(np.unique(groups[te])), y[te].sum(), len(te) - y[te].sum()))

    rf = RandomForestClassifier(n_estimators=args.n_estimators, class_weight=None,
                                n_jobs=-1, random_state=args.seed)
    rf.fit(X[tr], y[tr])
    pred = rf.predict(X[te])
    yt = y[te]

    cm = confusion_matrix(yt, pred, labels=[1, 0])
    tp, fn, fp, tn = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
    print('\nConfusion matrix (rows = actual Tilled, Not tilled; columns = predicted Tilled, Not tilled)')
    print('   TP=%d  FN=%d\n   FP=%d  TN=%d' % (tp, fn, fp, tn))

    rng = np.random.default_rng(args.seed)
    oas = []
    for _ in range(args.bootstrap):
        i = rng.integers(0, len(yt), len(yt))
        oas.append(accuracy_score(yt[i], pred[i]))
    lo, hi = np.percentile(oas, [2.5, 97.5])

    print('\nOverall Accuracy        = %.2f%%   (bootstrap 95%% CI %.2f-%.2f%%)'
          % (100 * accuracy_score(yt, pred), 100 * lo, 100 * hi))
    print('Balanced Accuracy       = %.2f%%' % (100 * balanced_accuracy_score(yt, pred)))
    print('Precision (Tilled)      = %.2f%%' % (100 * precision_score(yt, pred)))
    print('Recall    (Tilled)      = %.2f%%' % (100 * recall_score(yt, pred)))
    print('F1        (Tilled)      = %.2f%%' % (100 * f1_score(yt, pred)))
    print("Cohen's kappa           = %.3f" % cohen_kappa_score(yt, pred))
    print('MCC                     = %.3f' % matthews_corrcoef(yt, pred))


if __name__ == '__main__':
    main()
