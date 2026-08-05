# Supplementary materials — IEEE Sensors Journal submission

This folder contains everything referenced in the manuscript that ScholarOne treats as **supplementary** rather than as the main manuscript or its figures. Three categories:

```
supplementary/
├── demo_v20.gif         # Animated playback of the v20 algorithm on the median-lead subject
├── reproduce.py         # Single-entry reproducer for every numbered result in the paper
├── requirements.txt     # Pinned Python dependencies (numpy, scipy, scikit-learn, mne, ...)
├── results/             # Raw JSON outputs that back every headline number in the paper
└── scripts/             # All analysis scripts referenced by reproduce.py
```

## What gets uploaded to which ScholarOne field

| File | ScholarOne field | Purpose |
|---|---|---|
| `demo_v20.gif` | "Supplementary multimedia" | Live-system demonstrator referenced in manuscript §V.D |
| `reproduce.py` + `requirements.txt` + `scripts/` (zipped) | "Supplementary file" | Full reproducer that regenerates every numbered result |
| `results/*.json` (zipped together) | "Supplementary file" | JSON-format raw metrics behind every headline in the paper, for reviewer numerical verification |

The reviewer rationale for shipping the JSON results: a reviewer who wants to spot-check whether the F1 = 76.79 number really has the per-subject distribution we claim can simply read `publication_results_v17.json` rather than re-running the pipeline.

## Mapping JSON results to manuscript claims

| Manuscript claim | Backing JSON |
|---|---|
| LOSO progression table (Table I) | `publication_results_v3..v14.json` (incl. v9, v11, v14) |
| Feature-family ablation (Table II) | `publication_results_v11.json` |
| Awake-vs-drowsy coherence stats (Table III, Fig 1) | `publication_results_v21_reviewer.json` (`item1_coherence`) |
| v17 ROC operating points (Table IV, Fig 3) | `publication_results_v17_roc.json` |
| Paired Wilcoxon + Cohen's d (Table V; v17-vs-v11, v20-vs-v13) | `publication_results_v10b.json` |
| Per-subject F1/AUC/κ + 95% CIs (Table VI) | `publication_results_v21_reviewer.json` (`item2_subjectwise`) |
| Cross-dataset transfer + pooled LOSO (Table VII) | `publication_results_v12.json`, `publication_results_v16.json` |
| v20 advance-prediction Pareto (Table VIII) | `publication_results_v20.json` |
| v20 lead-vs-severity (Table IX, Fig 4) | `publication_results_v20_severity.json` |
| Baselines comparison (Table X) | drawn from v11 / v14 / v16 / v20 above |
| v17 monitoring headline F1 = 76.79 | `publication_results_v17.json` |
| Raw-vs-EMA posterior + smoothing latency (Fig 2) | `publication_results_v21_reviewer.json` (`item3_latency`) + `publication_results_v17.json` |
| v18 phase coherence negative ablation | `publication_results_v18.json` |
| v19 posterior ensemble negative ablation | `publication_results_v19.json` |
| v15 per-driver calibration sweep (supporting only, not a numbered table) | `publication_results_v15.json` |
| Runtime claim (56 ms / 10-s epoch) | `runtime_benchmark.json` |

## Running the reproducer (for reviewers)

```bash
# 1. Install pinned dependencies (Python 3.12 recommended)
pip install -r requirements.txt

# 2. Drop the raw datasets into the expected locations:
#      DROZY_O1_O2/         (extracted occipital EDFs from DROZY)
#      Raw_Data/            (SEED-VIG raw .mat files)
#      perclos_labels/      (SEED-VIG perclos .mat files)
#    Note: the datasets themselves are NOT redistributed in this archive,
#    consistent with their respective use agreements. Both are publicly
#    available from the originating institutions.

# 3. Run everything
python reproduce.py --list      # list the 17-step plan
python reproduce.py             # run; ~5 min wall-clock excluding EEGNet
python reproduce.py --only v17  # run a single named step
```

The reproducer is idempotent: every step is skipped if its output JSON / cache / figure already exists.

## Reproducer step → script mapping

`reproduce.py` calls each script under `scripts/` in dependency order:

```
v3/v4/v5  : publication_analysis.py          baselines + LDA z-score variants
v6        : riemannian_analysis.py           Riemannian TS untuned
v7        : nested_cv_analysis.py            Riemannian TS nested-CV tuned
v8        : calibration_analysis.py          calibration window sweep
v9        : extended_features.py             50-feature extended LDA
v11       : ablation_analysis.py             feature-family ablation (paper headline)
v12       : seed_vig_validation.py           DROZY → SEED-VIG transfer + SEED LOSO
v13       : advance_prediction.py            initial uncontrolled lead-time eval
v14       : eegnet_baseline.py               EEGNet deep baseline (~28 min)
v15       : personal_calibration.py          per-driver calibration sweep
v16       : pooled_loso.py                   pooled 31-subject DROZY ∪ SEED-VIG LOSO
v17       : hmm_smoothing.py                 causal EMA + HMM smoothing sweep
v18       : extended_coherence.py            phase-coh negative ablation
v19       : ensemble_analysis.py             posterior ensemble negative ablation
v20       : advance_prediction_v20.py        FPR-controlled advance-prediction Pareto
Tier 1 #1 : v17_roc.py                       monitoring ROC + 3 operating points
Tier 1 #2 : v17_v20_stats.py                 paired Wilcoxon + Cohen's d
Tier 1 #3 : v20_lead_vs_severity.py          lead-time vs PERCLOS-severity envelope
Tier 1 #4 : live_demo_figure.py              programmatic live-demo figure + GIF
v21       : reviewer_revision_analysis.py    coherence stats + per-subject CIs + EMA latency (internal-review additions)
runtime   : runtime_benchmark.py             56 ms / 10-s epoch claim
figures   : make_figures.py                  every figure in publication_figures_v5/
```

## Hardware / wall-clock budget

| Component | CPU time |
|---|---|
| Feature extraction (DROZY 50-feat) | ~80 s |
| Feature extraction (SEED-VIG 10-feat) | ~25 s |
| All LOSO LDA variants combined | ~30 s |
| Riemannian (covariance + tangent space) | ~3 min |
| EEGNet 10-fold LOSO | ~28 min |
| Phase coherence (PLV / ImCoh / wPLI extraction) | ~140 s |
| Advance-prediction sweep (v20, all 5×4×5×5 + 4×5 grid points) | ~90 s |
| Total without EEGNet | **~5 min** |
| Total with EEGNet | **~35 min** |

Measured on Intel Core i5-1240P @ 1.7 GHz (12 logical cores, no GPU). PyTorch CPU wheel only; no CUDA dependency.

## Public artefacts

The same supplementary content (plus the raw `.tex` source) is also released at:

`https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG`

at the commit tagged `paper-submission-v1`. A Zenodo DOI is minted from that release prior to acceptance and added to the manuscript's Reproducibility section.
