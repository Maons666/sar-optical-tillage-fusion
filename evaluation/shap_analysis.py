"""
SHAP analysis for Till v0.9 §4.7 — Random Forest tillage classifier.

USAGE
-----
    python shap_analysis.py ^
        --model      models/rf_tillage.pkl ^
        --features   data/features_validation.parquet ^
        --feat-names data/feature_names.txt ^
        --labels     data/y_validation.npy ^
        --n-samples  2000 ^
        --out-dir    figs/shap

OUTPUTS (figs/shap/)
--------------------
    shap_values.npz                # raw SHAP values + feature names + sample idx
    01_global_bar.png              # mean |SHAP| per feature
    02_beeswarm.png                # distributional impact  (THIS IS THE MONEY PLOT for §4.7)
    03_dependence_<rank>_<feat>.png  # top-3 features
    04_cohort_tilled.png           # SHAP restricted to tilled samples
    04_cohort_untilled.png         # SHAP restricted to no-till samples
"""

import argparse
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import shap


def load_model(path):
    path = Path(path)
    if path.suffix == '.joblib':
        import joblib
        return joblib.load(path)
    with open(path, 'rb') as f:
        return pickle.load(f)


def load_features(path, feat_names_path=None):
    path = Path(path)
    if path.suffix == '.parquet':
        df = pd.read_parquet(path)
        names = list(df.columns); X = df.values
    elif path.suffix == '.csv':
        df = pd.read_csv(path)
        names = list(df.columns); X = df.values
    elif path.suffix == '.npz':
        z = np.load(path, allow_pickle=True)
        X = z['X']
        names = list(z['feature_names']) if 'feature_names' in z.files else None
    elif path.suffix in {'.pkl', '.pickle'}:
        with open(path, 'rb') as f:
            obj = pickle.load(f)
        if isinstance(obj, pd.DataFrame):
            X = obj.values; names = list(obj.columns)
        else:
            X = obj; names = None
    elif path.suffix == '.npy':
        X = np.load(path); names = None
    else:
        raise ValueError(f'unsupported feature file: {path}')

    if feat_names_path:
        with open(feat_names_path) as f:
            names = [ln.strip() for ln in f if ln.strip()]
    if names is None:
        names = [f'f{i}' for i in range(X.shape[1])]
    assert len(names) == X.shape[1], \
        f'feature_names length {len(names)} != X.shape[1] {X.shape[1]}'
    return X, names


def load_labels(path):
    path = Path(path)
    if path.suffix == '.npy':
        return np.load(path)
    if path.suffix == '.csv':
        return pd.read_csv(path).values.ravel()
    return np.loadtxt(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model',      required=True)
    p.add_argument('--features',   required=True)
    p.add_argument('--feat-names', default=None)
    p.add_argument('--labels',     default=None)
    p.add_argument('--n-samples',  type=int, default=2000)
    p.add_argument('--out-dir',    default='figs/shap')
    p.add_argument('--seed',       type=int, default=42)
    p.add_argument('--positive-class', type=int, default=1,
                   help='class index treated as "tilled" (default 1)')
    args = p.parse_args()

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    print(f'>> loading model: {args.model}')
    model = load_model(args.model)
    print(f'   model class: {type(model).__name__}')

    print(f'>> loading features: {args.features}')
    X, names = load_features(args.features, args.feat_names)
    print(f'   X shape: {X.shape}')
    print(f'   features: {names}')

    rng = np.random.default_rng(args.seed)
    if X.shape[0] > args.n_samples:
        idx = rng.choice(X.shape[0], args.n_samples, replace=False)
        X_sample = X[idx]
        print(f'   subsampled to {args.n_samples} / {X.shape[0]}')
    else:
        idx = np.arange(X.shape[0]); X_sample = X
    X_df = pd.DataFrame(X_sample, columns=names)

    print('>> building TreeExplainer')
    explainer = shap.TreeExplainer(model)

    print('>> computing SHAP values  (this is the slow step — minutes, not hours)')
    sv = explainer.shap_values(X_sample)

    pc = args.positive_class
    if isinstance(sv, list):
        shap_arr = sv[pc]
        base_val = float(np.atleast_1d(explainer.expected_value)[pc])
    elif np.asarray(sv).ndim == 3:
        shap_arr = sv[:, :, pc]
        base_val = float(np.atleast_1d(explainer.expected_value)[pc])
    else:
        shap_arr = sv
        base_val = float(np.atleast_1d(explainer.expected_value)[0])
    print(f'   SHAP array shape: {shap_arr.shape}   base_value: {base_val:.4f}')

    npz_path = out_dir / 'shap_values.npz'
    np.savez(npz_path,
             shap_values=shap_arr, X_sample=X_sample,
             feature_names=np.array(names),
             base_value=base_val, sample_idx=idx)
    print(f'>> saved raw values -> {npz_path}')

    # ---- 1. global bar -------------------------------------------------
    plt.figure(figsize=(8, max(4, 0.35 * len(names))))
    shap.summary_plot(shap_arr, X_df, plot_type='bar',
                      show=False, max_display=len(names))
    plt.tight_layout()
    plt.savefig(out_dir / '01_global_bar.png', dpi=300); plt.close()
    print('>> saved 01_global_bar.png')

    # ---- 2. beeswarm ---------------------------------------------------
    plt.figure(figsize=(9, max(4, 0.35 * len(names))))
    shap.summary_plot(shap_arr, X_df, show=False, max_display=len(names))
    plt.tight_layout()
    plt.savefig(out_dir / '02_beeswarm.png', dpi=300); plt.close()
    print('>> saved 02_beeswarm.png')

    # ---- 3. dependence plots for top-3 ---------------------------------
    importance = np.abs(shap_arr).mean(axis=0)
    top_idx = np.argsort(importance)[::-1][:3]
    print('   top-3 features by mean |SHAP|:')
    for fi in top_idx:
        print(f'      {names[fi]:30s}  {importance[fi]:.4f}')
    for rank, fi in enumerate(top_idx, 1):
        plt.figure(figsize=(7, 5))
        shap.dependence_plot(fi, shap_arr, X_df,
                             feature_names=names, show=False)
        plt.tight_layout()
        safe = names[fi].replace('/', '_').replace(' ', '_').replace('\\', '_')
        plt.savefig(out_dir / f'03_dependence_{rank}_{safe}.png', dpi=300)
        plt.close()
        print(f'>> saved 03_dependence_{rank}_{safe}.png')

    # ---- 4. class-cohort plots -----------------------------------------
    if args.labels:
        y = load_labels(args.labels)
        y_sample = y[idx] if y.shape[0] == X.shape[0] else y
        for cls, name in [(pc, 'tilled'), (1 - pc, 'untilled')]:
            mask = (y_sample == cls)
            if mask.sum() < 50:
                print(f'   skipping cohort "{name}" (n={mask.sum()} < 50)')
                continue
            plt.figure(figsize=(9, max(4, 0.35 * len(names))))
            shap.summary_plot(shap_arr[mask], X_df.iloc[mask],
                              show=False, max_display=len(names))
            plt.title(f'cohort: {name}  (n = {int(mask.sum())})')
            plt.tight_layout()
            plt.savefig(out_dir / f'04_cohort_{name}.png', dpi=300); plt.close()
            print(f'>> saved 04_cohort_{name}.png')

    print('\nDONE.  Look in', out_dir.resolve())


if __name__ == '__main__':
    main()
