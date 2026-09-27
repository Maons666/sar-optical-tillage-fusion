# Weekly Field-Level Tillage Mapping with Sentinel-1/2 Fusion: Code Release

Reproduction code for:

> **Weekly Field-Level Mapping of Agricultural Tillage Events Using
> Sentinel-1/2 Data Fusion and Crop Sequence Boundaries: A Feasibility
> Study in Nebraska, USA.**
> Wang X., Di L., Zhang C., Li H., Shao B., Wei Y., Liu Z., Wang Y. (2026).
> *Soil and Tillage Research*, manuscript STILL-D-26-02880, in revision.
> (Submitted as "Near-real-time Field-Level Agricultural Tillage Event
> Mapping for the Midwestern U.S. ...".)

Section, figure and table numbers below are those of the revised manuscript.

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
│   └── tillage_fusion.py         CORE fusion pipeline (§3.4):
│                                  RF optical classification + S-1 InSAR
│                                  coherence at 9-pixel window + optical
│                                  confidence gate at p_max = 0.65 + γ threshold at 0.25 +
│                                  CSB parcel aggregation via zonal stats
│
├── evaluation/                   ← §4.1, §4.2 and §4.6
│   ├── evaluate_holdout.py       §4.1 field-level hold-out evaluation
│   │                              (OA + bootstrap CI, BA, P, R, F1, κ, MCC)
│   ├── metrics_from_table4.py    §4.1 metrics of Table 5 from the confusion
│   │                              matrix of Table 4
│   ├── confidence_map_stats.py   §4.2 numbers quoted for Figure 7
│   ├── shap_analysis.py          §4.6 SHAP driver (from saved RF pickle)
│   └── shap_from_csv.py          §4.6 SHAP driver (end-to-end from CSV)
│
├── sensitivity/                  ← §4.5 threshold sensitivity and rule shares
│   ├── sample_s2_nebraska_2025.py   GEE: Sentinel-2 bands + SCL at 6,017 random
│   │                                 corn/soybean pixels, weekly windows of 2025
│   ├── sample_s1_grd.py          GEE: Sentinel-1 GRD intensity correlation of
│   │                              12-day pairs at the same pixels
│   ├── fusion_sweep_samples.py   fusion rules for every threshold combination
│   ├── routing_without_slc.py    share of clear pixels retained by the gate
│   ├── optical_only_cumulative.py   cumulative contribution of each channel
│   └── make_tables_and_figure_samples.py   Tables 6 and 7, data of Figure 11
│
├── weather/                      ← §2.1, Table 1
│   ├── parse_nass_national.py    USDA NASS Crop Progress reports -> CSV
│   ├── gee_weekly_coverage_nass_aligned.py   weekly S-2 and S-1/2 coverage
│   └── build_nebraska_table.py   assembles Table 1
│
├── gee/                          ← §4.4 GEE coverage analysis
│   └── coverage_analysis.js      weekly cropland coverage under S-2 only
│                                  vs (S-1 ∪ S-2), 2025 over NE
│
└── figures_latex/                ← sources of the figures (TikZ / PGFPlots)
    ├── figstyle.tex              shared style
    ├── build_figures.ps1         compiles every figure (needs a TeX system)
    ├── fig02 ... fig06, fig10 ... fig13   Figures 2-6 and 9-12 of the paper
    │                              (file numbers follow the submitted version)
    ├── fig07_make_confidence_map.py   Figure 7 from the pipeline rasters
    ├── fig12_export_shap_points.py    SHAP values -> coordinates of Figure 12
    └── dat_*.dat, inc_fig12_*    data read by the figure sources
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

### §3.4 — Fusion pipeline

```bash
python pipeline/tillage_fusion.py
```

Runs, block-by-block:
  1. Optical RF classification + per-pixel confidence p_max (Shannon entropy
     is kept as the uncertainty map of Figure 7)
  2. InSAR coherence over a 9-pixel moving window
  3. Confidence-gated multi-modal fusion: pixels with p_max < 0.65 are
     referred to the SAR rules, γ < 0.25 flags soil disturbance and
     γ > 0.60 flags a structurally stable surface
  4. CSB parcel aggregation via `rasterstats.zonal_stats`

Outputs to `out/`:
  * `Fused_Tillage_Result_<dates>.tif`         final classification
  * `RF_Confidence_<dates>.tif`                per-pixel confidence 0–100
  * `S1_Coherence_<dates>.tif`                 raw coherence layer
  * `Cloud_Mask_<dates>.tif`                   binary cloud mask
  * `CSB_NE_updated.gpkg`                      CSB polygons with
                                               `tillage_<dates>` attribute

### §4.1 — hold-out evaluation of the optical classifier

Requires the labelled training CSV (not included; available from the
corresponding author on request, see the Data availability statement).
The CSV must carry a column that identifies the field each pixel belongs to.

```bash
python evaluation/evaluate_holdout.py \
    --csv path/to/training_pixels.csv \
    --field-col field_id --label-col tillage --tilled-class 1
```

The hold-out is drawn at the field level (whole fields on one side only), so
pixels of the same field never occur in both partitions. The labelled sample is
class-balanced at the sampling stage, so the 200-tree Random Forest is trained
without class weights. Reports the confusion matrix, Overall Accuracy with a
1,000-resample bootstrap 95% CI, Balanced Accuracy, Precision, Recall and F1 of
the Tilled class, Cohen's κ and MCC (Tables 4 and 5 of the paper).

### §4.4 — Sentinel-2 vs (S-1 ∪ S-2) weekly cropland coverage

Paste `gee/coverage_analysis.js` into the Google Earth Engine Code
Editor, run it, then click **Run** on the two export tasks. Two CSVs
land in `Drive/GEE_exports/`; the mean of the `fraction` column times
100 is the weekly cropland coverage percentage reported in the paper.

### §4.5 — Threshold sensitivity and use of each fusion rule

The analysis runs on 6,017 corn and soybean pixels sampled at random over
Nebraska and revisited in twelve weekly windows (6 April to 22 June 2025).
Single-look complex data were processed only for the mapped area, so for
this sample-based analysis the coherence magnitude is estimated from
Sentinel-1 GRD data: the local correlation of the backscatter intensities of
a 12-day pair (9 x 9 window at 30 m), gamma_hat = sqrt(max(rho_I, 0)).
It carries no phase information and does not replace interferometric coherence.

```bash
python sensitivity/sample_s2_nebraska_2025.py        # -> data/nebraska_2025_samples.csv
python sensitivity/sample_s1_grd.py --out data/grd   # -> data/grd/s1_grd_samples.csv
python sensitivity/fusion_sweep_samples.py --grd data/grd --out data/sweep
python sensitivity/routing_without_slc.py --out data/routing --final 2025-06-22
python sensitivity/make_tables_and_figure_samples.py --inputs data/sweep \
    --gate data/routing/gate_sweep_target_fitted.csv --out figures_latex
```

Both sampling scripts need an Earth Engine account (`ee.Initialize(project=...)`)
and `models/tillage_classifier.pkl`. Run each script with `--help` for its options.

### §4.6 — SHAP interpretability

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

### Figures

The diagrams and charts of the paper are LaTeX sources (TikZ / PGFPlots).

```powershell
cd figures_latex
./build_figures.ps1            # all figures
./build_figures.ps1 -Only fig13   # one figure
```

Figure 12 is compiled with LuaLaTeX, the others with pdfLaTeX. Figures 1 and 8
are maps and are not generated by this repository.

---

## Data sources (not included in this repository)

| Data | Provider | Access |
|---|---|---|
| Sentinel-1 SLC and GRD / Sentinel-2 SR HARMONIZED | ESA Copernicus | Google Earth Engine (`COPERNICUS/S1_GRD_FLOAT`), Copernicus Data Space |
| USDA Crop Sequence Boundaries v2024 | USDA NASS | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/ |
| USDA Cropland Data Layer 2024 | USDA NASS | Google Earth Engine `USDA/NASS/CDL/2024` |
| Climate at a Glance (precipitation) | NOAA NCEI | https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/ |
| Crop Progress 2025 | USDA NASS | https://usda.library.cornell.edu/concern/publications/8336h188j |
| U.S. Drought Monitor | NDMC, USDA, NOAA | https://droughtmonitor.unl.edu/ |

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
