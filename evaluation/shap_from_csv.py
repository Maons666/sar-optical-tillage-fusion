"""
SHAP analysis for Till v0.9 §4.7 — start directly from the training CSV.

This script:
    1. Loads your training CSV.
    2. Re-trains a Random Forest with the SAME defaults as the paper.
    3. Holds out 20% for honest evaluation (prints OA / F1 — should match §4.1).
    4. Runs SHAP TreeExplainer on a 2000-pixel subsample.
    5. Saves beeswarm / bar / dependence / cohort plots into figs/shap/.

USAGE (PowerShell)
------------------
    pip install shap pandas scikit-learn pyarrow joblib

    # Simplest call — auto-detects the label column
    python shap_from_csv.py --csv data/training_pixels.csv

    # If your label column has a non-standard name:
    python shap_from_csv.py --csv data/training_pixels.csv --label-col tilled

    # If you want to drop ID / coord columns:
    python shap_from_csv.py --csv data/training_pixels.csv ^
        --drop-cols pixel_id,lon,lat,date,CSB_id

WHAT YOUR CSV NEEDS
-------------------
    - One row = one labeled pixel.
    - One column = the binary label (tilled = 1, no-till / untilled = 0).
      Auto-detected names: label, y, tillage, tilled, target, class
    - All OTHER numeric columns are treated as features.
      Non-numeric columns (strings, dates, IDs) are auto-skipped unless you
      explicitly list them with --drop-cols (recommended for clarity).
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, f1_score,
                             classification_report, confusion_matrix)

import shap


LABEL_CANDIDATES = ['label', 'y', 'tillage', 'tilled', 'target', 'class',
                    'Label', 'Y', 'Tillage', 'Tilled', 'Target', 'Class']


def autodetect_label_col(df, override=None):
    if override:
        if override not in df.columns:
            raise ValueError(f'--label-col "{override}" not in CSV columns: '
                             f'{list(df.columns)}')
        return override
    for c in LABEL_CANDIDATES:
        if c in df.columns:
            return c
    raise ValueError(
        'Could not auto-detect a label column. Tried: '
        f'{LABEL_CANDIDATES}. Use --label-col to specify.\n'
        f'Your columns: {list(df.columns)}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv',         required=True)
    p.add_argument('--label-col',   default=None)
    p.add_argument('--drop-cols',   default='',
                   help='comma-separated extra columns to drop (IDs, coords, dates)')
    p.add_argument('--n-estimators', type=int, default=500)
    p.add_argument('--max-depth',    type=int, default=None)
    p.add_argument('--min-samples-leaf', type=int, default=2)
    p.add_argument('--test-size',   type=float, default=0.20)
    p.add_argument('--n-samples',   type=int, default=2000,
                   help='subsample size for SHAP (more = slower, diminishing returns)')
    p.add_argument('--out-dir',     default='figs/shap')
    p.add_argument('--seed',        type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. load CSV ----------------------------------------------------
    print(f'>> loading {args.csv}')
    df = pd.read_csv(args.csv)
    print(f'   shape: {df.shape}')
    print(f'   columns: {list(df.columns)}')

    label_col = autodetect_label_col(df, args.label_col)
    print(f'   label column: "{label_col}"')

    extra_drop = [c.strip() for c in args.drop_cols.split(',') if c.strip()]
    drop_cols = [label_col] + extra_drop

    feature_df = df.drop(columns=drop_cols, errors='ignore')
    # keep only numeric columns
    non_numeric = feature_df.select_dtypes(exclude='number').columns.tolist()
    if non_numeric:
        print(f'   auto-dropping non-numeric columns: {non_numeric}')
        feature_df = feature_df.select_dtypes(include='number')

    feature_names = list(feature_df.columns)
    X = feature_df.values.astype(np.float32)
    y = df[label_col].values

    # handle NaNs (mean-impute, simple and safe for tree models)
    nan_count = np.isnan(X).sum()
    if nan_count:
        print(f'   imputing {nan_count} NaN cells with column means')
        col_mean = np.nanmean(X, axis=0)
        idx = np.where(np.isnan(X))
        X[idx] = np.take(col_mean, idx[1])

    print(f'   X: {X.shape}   features: {feature_names}')
    print(f'   y dist: {dict(zip(*np.unique(y, return_counts=True)))}')

    # ---- 2. train / test split ------------------------------------------
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=args.test_size,
        stratify=y, random_state=args.seed)
    print(f'>> train {X_tr.shape}   test {X_te.shape}')

    # ---- 3. train RF ----------------------------------------------------
    print('>> training RandomForest '
          f'(n_estimators={args.n_estimators}, '
          f'max_depth={args.max_depth}, '
          f'min_samples_leaf={args.min_samples_leaf}, '
          f'class_weight=balanced)')
    rf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        class_weight='balanced',
        n_jobs=-1,
        random_state=args.seed,
    )
    rf.fit(X_tr, y_tr)

    pred = rf.predict(X_te)
    oa = accuracy_score(y_te, pred)
    f1 = f1_score(y_te, pred, average='binary'
                  if len(np.unique(y)) == 2 else 'macro')
    print(f'>> hold-out  OA = {oa*100:.2f}%   F1 = {f1*100:.2f}%')
    print(classification_report(y_te, pred, digits=4))
    print('confusion matrix:\n', confusion_matrix(y_te, pred))

    # persist the trained model for later reuse
    with open(out_dir / 'rf_trained.pkl', 'wb') as f:
        pickle.dump(rf, f)
    print(f'>> saved trained model -> {out_dir / "rf_trained.pkl"}')

    # ---- 4. SHAP --------------------------------------------------------
    rng = np.random.default_rng(args.seed)
    pool = X_te if X_te.shape[0] >= args.n_samples else X
    if pool.shape[0] > args.n_samples:
        idx = rng.choice(pool.shape[0], args.n_samples, replace=False)
        X_sample = pool[idx]
        y_sample = (y_te if pool is X_te else y)[idx]
    else:
        idx = np.arange(pool.shape[0])
        X_sample = pool
        y_sample = y_te if pool is X_te else y
    X_df = pd.DataFrame(X_sample, columns=feature_names)
    print(f'>> SHAP subsample: {X_sample.shape}')

    print('>> building TreeExplainer')
    explainer = shap.TreeExplainer(rf)

    print('>> computing SHAP values (a few minutes)')
    sv = explainer.shap_values(X_sample)

    # Pick the positive class (1 = tilled)
    if isinstance(sv, list):
        shap_arr = sv[1]
        base_val = float(np.atleast_1d(explainer.expected_value)[1])
    elif np.asarray(sv).ndim == 3:
        shap_arr = sv[:, :, 1]
        base_val = float(np.atleast_1d(explainer.expected_value)[1])
    else:
        shap_arr = sv
        base_val = float(np.atleast_1d(explainer.expected_value)[0])
    print(f'   SHAP shape: {shap_arr.shape}   base value: {base_val:.4f}')

    np.savez(out_dir / 'shap_values.npz',
             shap_values=shap_arr, X_sample=X_sample, y_sample=y_sample,
             feature_names=np.array(feature_names),
             base_value=base_val, sample_idx=idx)
    print(f'>> saved raw values -> {out_dir / "shap_values.npz"}')

    # ---- 5. plots -------------------------------------------------------
    F = len(feature_names)

    plt.figure(figsize=(8, max(4, 0.35 * F)))
    shap.summary_plot(shap_arr, X_df, plot_type='bar',
                      show=False, max_display=F)
    plt.tight_layout()
    plt.savefig(out_dir / '01_global_bar.png', dpi=300); plt.close()
    print('>> saved 01_global_bar.png')

    plt.figure(figsize=(9, max(4, 0.35 * F)))
    shap.summary_plot(shap_arr, X_df, show=False, max_display=F)
    plt.tight_layout()
    plt.savefig(out_dir / '02_beeswarm.png', dpi=300); plt.close()
    print('>> saved 02_beeswarm.png')

    importance = np.abs(shap_arr).mean(axis=0)
    order = np.argsort(importance)[::-1]
    top_idx = order[:3]
    print('   top-3 by mean |SHAP|:')
    for fi in top_idx:
        print(f'      {feature_names[fi]:30s}  {importance[fi]:.4f}')
    for rank, fi in enumerate(top_idx, 1):
        plt.figure(figsize=(7, 5))
        shap.dependence_plot(fi, shap_arr, X_df,
                             feature_names=feature_names, show=False)
        plt.tight_layout()
        safe = (feature_names[fi]
                .replace('/', '_').replace(' ', '_').replace('\\', '_'))
        plt.savefig(out_dir / f'03_dependence_{rank}_{safe}.png', dpi=300)
        plt.close()
        print(f'>> saved 03_dependence_{rank}_{safe}.png')

    # cohort plots
    for cls, name in [(1, 'tilled'), (0, 'untilled')]:
        mask = (y_sample == cls)
        if mask.sum() < 50:
            print(f'   skipping cohort "{name}" (n={mask.sum()})'); continue
        plt.figure(figsize=(9, max(4, 0.35 * F)))
        shap.summary_plot(shap_arr[mask], X_df.iloc[mask],
                          show=False, max_display=F)
        plt.title(f'cohort: {name}  (n = {int(mask.sum())})')
        plt.tight_layout()
        plt.savefig(out_dir / f'04_cohort_{name}.png', dpi=300); plt.close()
        print(f'>> saved 04_cohort_{name}.png')

    # write a small text summary for the §4.7 paragraph
    with open(out_dir / 'shap_summary.txt', 'w', encoding='utf-8') as f:
        f.write(f'Trained on {X_tr.shape[0]} pixels, '
                f'evaluated on {X_te.shape[0]}.\n')
        f.write(f'Hold-out OA  = {oa*100:.2f}%\n')
        f.write(f'Hold-out F1  = {f1*100:.2f}%\n\n')
        f.write('Feature ranking by mean |SHAP|:\n')
        for fi in order:
            f.write(f'   {feature_names[fi]:30s}  {importance[fi]:.4f}\n')
    print(f'>> wrote {out_dir / "shap_summary.txt"}')

    print('\nDONE.  Look in', out_dir.resolve())


if __name__ == '__main__':
    main()
