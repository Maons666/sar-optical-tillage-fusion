# Near-Real-Time Field-Level Tillage Mapping — Code Release

Reproduction code for:

> **Near-real-time Field-Level Agricultural Tillage Event Mapping for the
> Midwestern U.S. Using Sentinel-1/2 Data Fusion and Crop Sequence
> Boundaries.**
> Wang X., Li H., Shao B., Wei Y., Liu Z., Wang Y., Di L. (2026).
> *Soil and Tillage Research*, submitted.

This repository ships **code only**. All training samples, trained
models, and raster/vector intermediates are excluded by `.gitignore`.
See §2.2 of the paper for the public data sources.

---

## Repository layout

```
code_release/
├── README.md                     this file
├── LICENSE.md                    MIT
├── requirements.txt              Python dependencies
├── .gitignore
│
├── pipeline/                     ← operational analysis pipeline
│   ├── shp2gpkg.py               utility: Shapefile -> GeoPackage
│   ├── fetch_s2_roi.py           GEE: fetch Sentinel-2 SR HARMONIZED mosaic
│   │                              for an ROI over a date window (§3.1)
│   ├── merge.py                  merge Sentinel-1 SLC burst fragments and
│   │                              align them to the S2 grid (§3.3)
│   └── tillage_fusion.py         CORE fusion pipeline (§3.4 / §4.5):
│                                  RF optical classification + S-1 InSAR
│                                  coherence at 9-pixel window + entropy
│                                  gate at 0.65 + γ threshold at 0.25 +
│                                  CSB parcel aggregation via zonal stats
│
├── evaluation/                   ← §4.1 + §4.7 evaluation
│   ├── rebalance_evaluate.py     §4.1 six-metric performance panel
│   │                              (OA, balanced-OA, BA, F1_minority, κ, MCC)
│   ├── shap_analysis.py          §4.7 SHAP driver (from saved RF pickle)
│   └── shap_from_csv.py          §4.7 SHAP driver (end-to-end from CSV)
│
├── gee/                          ← §4.5 GEE coverage analysis
│   └── coverage_analysis.js      weekly cropland coverage under S-2 only
│                                  vs (S-1 ∪ S-2), May–June 2025 over NE
│
└── figures/                      ← concept-figure generators
    ├── _pil_helpers.py           shared canvas / drawing primitives
    ├── fig_workflow.py           Figure 2 workflow diagram
    ├── fig_concept_A1_physics.py Figure 3 (measurement physics)
    ├── fig_concept_A2_properties.py Figure 4 (target physical property)
    ├── fig_concept_A3_gate.py    Figure 5 (Shannon entropy gate)
    ├── fig_concept_A4_output.py  auxiliary (fused output schematic)
    ├── fig_concept_B_scenario.py Figure 10 (sensor-mode across cloud regimes)
    ├── fig_concept_C_signals.py  Figure 11 (three-signal co-evolution)
    └── fig_subpanels.py          sub-panels used by the concept figs
```

---

## Environment setup

Geospatial dependencies (`rasterio`, `geopandas`, `gdal`, `rasterstats`)
have OS-level binary requirements and are best installed via **conda**.

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>

# recommended: create a conda environment
conda create -n tillage python=3.11
conda activate tillage
conda install -c conda-forge rasterio geopandas gdal rasterstats shapely
pip install -r requirements.txt
```

For the GEE script (`pipeline/fetch_s2_roi.py`), authenticate once:

```bash
earthengine authenticate
```

---

## Expected working directory layout (data lives outside the repo)

`pipeline/tillage_fusion.py` and its siblings expect the following layout
when run from a project root (see the `--- 配置区 ---` section at the top
of each script; adjust paths as needed):

```
<project_root>/
├── data/
│   ├── raw/          Sentinel-1 SLC burst tiffs (from ASF or Copernicus)
│   ├── ready/
│   │   ├── S2/       Sentinel-2 mosaic exported by fetch_s2_roi.py
│   │   └── SLC/      S-1 SLC bursts aligned to the S-2 grid by merge.py
│   └── utils/        ROI.gpkg  and  CSB_NE.gpkg
├── models/
│   └── tillage_classifier.pkl    trained Random Forest classifier
├── out/                          fusion outputs (tif) written here
└── (this repo's pipeline/ scripts run from <project_root>)
```

None of these data / model artefacts are shipped in this repository.
They must be obtained from the public sources listed at the bottom of
this file, and the RF classifier is available from the corresponding
author upon reasonable request.

---

## Reproducing the paper's numbers

### §3.1 — Sentinel-2 acquisition

```bash
# adjust ROI, start / end dates inside the script's __main__
python pipeline/fetch_s2_roi.py
```

Submits an `Export.image.toDrive` job. The mosaic lands in Google Drive
(`Tillage_Export/`) and should be moved into `data/ready/S2/`.

### §3.3 — Sentinel-1 SLC alignment

```bash
# raw S1 burst tiffs staged under data/raw/
python pipeline/merge.py
```

Merges S1 fragments by acquisition date and reprojects/aligns each stack
to the S2 master grid.

### §3.4 / §4.5 — Fusion pipeline

```bash
python pipeline/tillage_fusion.py
```

Runs, block-by-block:
  1. Optical RF classification + Shannon-entropy confidence
  2. InSAR coherence over a 9-pixel moving window
  3. Entropy-gated multi-modal fusion using thresholds
     H ≥ 0.65 (SAR override) and γ < 0.25 (soil-disturbance flag)
  4. CSB parcel aggregation via `rasterstats.zonal_stats`

Outputs to `out/`:
  * `Fused_Tillage_Result_<dates>.tif`         final classification
  * `RF_Confidence_<dates>.tif`                per-pixel confidence 0–100
  * `S1_Coherence_<dates>.tif`                 raw coherence layer
  * `Cloud_Mask_<dates>.tif`                   binary cloud mask
  * `CSB_NE_updated.gpkg`                      CSB polygons with
                                               `tillage_<dates>` attribute

### §4.1 — six-metric performance panel

Requires the original training CSV (not included).

```bash
python evaluation/rebalance_evaluate.py \
    --csv path/to/training_pixels.csv \
    --tilled-class 1
```

Reports natural-distribution OA, balanced-subset OA (with 1,000-resample
95% bootstrap CI), balanced accuracy, F1 on the minority Tilled class,
Cohen's κ, and MCC.

### §4.5 — Sentinel-2 vs (S-1 ∪ S-2) weekly cropland coverage

Paste `gee/coverage_analysis.js` into the Google Earth Engine Code
Editor, run it, then click **Run** on the two export tasks. Two CSVs
land in `Drive/GEE_exports/`; the mean of the `fraction` column times
100 is the weekly cropland coverage percentage reported in the paper.

### §4.7 — SHAP interpretability

End-to-end from the training CSV (retrains the classifier under the
same hyperparameters as §4.1):

```bash
python evaluation/shap_from_csv.py \
    --csv path/to/training_pixels.csv \
    --label-col tillage \
    --n-samples 2000 \
    --out-dir figs/shap
```

Alternatively, from a saved pickle:

```bash
python evaluation/shap_analysis.py \
    --model    models/rf.pkl \
    --features data/X_holdout.parquet \
    --labels   data/y_holdout.npy \
    --out-dir  figs/shap
```

### Concept figures (Figures 2, 3, 4, 5, 10, 11)

```bash
python figures/fig_workflow.py
python figures/fig_concept_A1_physics.py
python figures/fig_concept_A2_properties.py
python figures/fig_concept_A3_gate.py
python figures/fig_concept_B_scenario.py
python figures/fig_concept_C_signals.py
```

Each script drops a PNG next to itself.

---

## Data sources (not included in this repository)

| Data | Provider | Access |
|---|---|---|
| Sentinel-1 SLC / Sentinel-2 SR HARMONIZED | ESA Copernicus | Google Earth Engine, Copernicus Data Space |
| USDA Crop Sequence Boundaries v2024 | USDA NASS | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/ |
| USDA Cropland Data Layer 2024 | USDA NASS | Google Earth Engine `USDA/NASS/CDL/2024` |
| May 2025 National Climate Report | NOAA NCEI | https://www.ncei.noaa.gov/access/monitoring/monthly-report/national/202505 |

The 126,962-pixel ground-truth training set collected during the 2024
field campaign contains coordinates that could identify participating
operators and is available from the corresponding author upon reasonable
request. The trained Random Forest classifier
(`tillage_classifier.pkl`, ~48 MB) is likewise available on request.

---

## Citation

If you use this code, please cite the paper (BibTeX to be added after
acceptance).

## Contact

* Xinyu Wang — xwang72@gmu.edu
* Liping Di (corresponding author) — ldi@gmu.edu
* Center for Spatial Information Science and Systems
* George Mason University, Fairfax, VA, USA
