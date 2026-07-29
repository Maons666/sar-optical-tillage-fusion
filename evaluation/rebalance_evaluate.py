"""
Class-aware re-evaluation of the §4.1 baseline RF classifier.

Reports SIX honest metrics — every one of these will be expected by an STR
reviewer for a 93/7 imbalanced binary problem:

    1. OA (natural distribution)        — the "looks great but trivial" number
    2. OA (balanced subset)              — the methodologically meaningful one
    3. Balanced Accuracy = (TPR+TNR)/2   — equivalent to OA on virtual 50/50
    4. F1 (minority class = Tilled)      — minority-class P/R balance
    5. Cohen's kappa                     — chance-corrected agreement
    6. Matthews correlation coefficient   — imbalance-immune binary gold standard

Plus a bootstrap CI on the balanced-subset OA (1000 resamples).

USAGE
-----
    python rebalance_evaluate.py --csv data/training_pixels.csv

    # If your label coding has tilled = 0  (mine inferred from SHAP):
    python rebalance_evaluate.py --csv data/training_pixels.csv --tilled-class 0
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    cohen_kappa_score, matthews_corrcoef,
    classification_report, confusion_matrix,
)


LABEL_CANDIDATES = ['label', 'y', 'tillage', 'tilled', 'target', 'class',
                    'Label', 'Y', 'Tillage', 'Tilled', 'Target', 'Class']


def autodetect_label_col(df, override=None):
    if override:
        return override
    for c in LABEL_CANDIDATES:
        if c in df.columns:
            return c
    raise ValueError('Set --label-col explicitly')


def bootstrap_oa(y_true, y_pred, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y_true)
    accs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        accs[i] = accuracy_score(y_true[idx], y_pred[idx])
    return accs.mean(), accs.std(), np.percentile(accs, [2.5, 97.5])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv',         required=True)
    p.add_argument('--label-col',   default=None)
    p.add_argument('--drop-cols',   default='')
    p.add_argument('--tilled-class', type=int, default=0,
                   help='which y value codes for "Tilled" (SHAP suggests 0)')
    p.add_argument('--test-size',   type=float, default=0.20)
    p.add_argument('--seed',        type=int, default=42)
    p.add_argument('--n-estimators', type=int, default=500)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    print(f'>> {df.shape[0]} rows, {df.shape[1]} cols')
    lbl = autodetect_label_col(df, args.label_col)
    print(f'   label column: "{lbl}"')

    extra = [c.strip() for c in args.drop_cols.split(',') if c.strip()]
    Xdf = (df.drop(columns=[lbl] + extra, errors='ignore')
             .select_dtypes(include='number'))
    feats = list(Xdf.columns)
    X = Xdf.values.astype(np.float32)
    if np.isnan(X).any():
        X = np.where(np.isnan(X), np.nanmean(X, axis=0), X)
    y = df[lbl].values

    cls_counts = dict(zip(*np.unique(y, return_counts=True)))
    print(f'   class distribution: {cls_counts}')
    tc = args.tilled_class
    print(f'   "Tilled" = class {tc}   '
          f'(minority? {cls_counts[tc] < cls_counts[1 - tc]})')

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=args.seed)
    print(f'>> train {X_tr.shape}   test {X_te.shape}')
    print(f'   test class counts: '
          f'{dict(zip(*np.unique(y_te, return_counts=True)))}')

    rf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        min_samples_leaf=2, class_weight='balanced',
        n_jobs=-1, random_state=args.seed)
    rf.fit(X_tr, y_tr)
    pred = rf.predict(X_te)

    # ---- M1. natural-distribution metrics --------------------------------
    print('\n================ NATURAL DISTRIBUTION (n = {}) ================'
          .format(len(y_te)))
    oa_nat = accuracy_score(y_te, pred)
    bacc   = balanced_accuracy_score(y_te, pred)
    f1_til = f1_score(y_te, pred, pos_label=tc)
    f1_mac = f1_score(y_te, pred, average='macro')
    kappa  = cohen_kappa_score(y_te, pred)
    mcc    = matthews_corrcoef(y_te, pred)
    print(f'OA          (natural)            = {oa_nat*100:.2f}%')
    print(f'Balanced Accuracy                = {bacc*100:.2f}%')
    print(f'F1   (Tilled = class {tc})         = {f1_til*100:.2f}%')
    print(f'F1   (macro avg)                 = {f1_mac*100:.2f}%')
    print(f"Cohen's kappa                    = {kappa:.4f}")
    print(f'MCC                              = {mcc:.4f}')
    print('confusion matrix (rows = true):')
    print(confusion_matrix(y_te, pred))

    # ---- M2. balanced-subset OA ------------------------------------------
    # Auto-detect minority/majority so we always undersample the larger one,
    # regardless of which class the user labelled "Tilled".
    print('\n================ BALANCED SUBSET (undersampled) ================')
    rng = np.random.default_rng(args.seed)
    idx_a = np.where(y_te == tc)[0]
    idx_b = np.where(y_te == (1 - tc))[0]
    if len(idx_a) <= len(idx_b):
        minority_idx, majority_idx = idx_a, idx_b
        min_name, maj_name = f'class {tc} (Tilled)', f'class {1-tc} (Untilled)'
    else:
        minority_idx, majority_idx = idx_b, idx_a
        min_name, maj_name = f'class {1-tc} (Untilled)', f'class {tc} (Tilled)'
    n_keep = len(minority_idx)
    idx_maj_us = rng.choice(majority_idx, n_keep, replace=False)
    sel = np.concatenate([minority_idx, idx_maj_us])
    y_bal = y_te[sel]; p_bal = pred[sel]
    oa_bal = accuracy_score(y_bal, p_bal)
    print(f'minority = {min_name}, n = {n_keep}')
    print(f'majority = {maj_name}, undersampled to n = {n_keep}')
    print(f'balanced subset total n = {len(sel)}')
    print(f'OA (balanced subset)             = {oa_bal*100:.2f}%')

    mu, sd, ci = bootstrap_oa(y_bal, p_bal, n_boot=1000, seed=args.seed)
    print(f'bootstrap OA (1000 resamples)    = {mu*100:.2f}% '
          f'± {sd*100:.2f}%   95% CI [{ci[0]*100:.2f}, {ci[1]*100:.2f}]%')

    print('\n================ SUMMARY for §4.1 TABLE ================')
    print(f'  OA  (natural, n={len(y_te)})         {oa_nat*100:6.2f}%')
    print(f'  OA  (balanced, n={len(sel)})        {oa_bal*100:6.2f}%  '
          f'(95% CI {ci[0]*100:.2f}–{ci[1]*100:.2f}%)')
    print(f'  Balanced Accuracy                {bacc*100:6.2f}%')
    print(f'  F1 (Tilled minority)             {f1_til*100:6.2f}%')
    print(f"  Cohen's kappa                    {kappa:.4f}")
    print(f'  MCC                              {mcc:.4f}')


if __name__ == '__main__':
    main()
