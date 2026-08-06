# Pro-Active Driver Monitoring System Using EEG

Two-channel occipital EEG for subject-independent driver drowsiness monitoring
and advance prediction, in a vehicle-headrest form factor.

This repository holds the code and results behind the manuscript
**"Inter-Hemispheric Occipital Coherence for Subject-Independent Driver
Drowsiness Monitoring and Advance Prediction"**, submitted to the *IEEE Sensors
Journal* on 6 August 2026. The snapshot the paper cites is the tag
`paper-submission-v1`.

M. R. Thalassery, S. S. Ali, A. R. Pal, A. Chemori, G. Murali Mohan ·
VIT Chennai, India, and LIRMM, Université de Montpellier, CNRS, France ·
Corresponding author: Dr. Abhishek Rudra Pal, abhishek.rudrapal@vit.ac.in

---

## What it does

Two electrodes at O₁ and O₂ — about the only scalp sites a headrest can reach
without a cap or a camera — feed a ten-feature shrinkage LDA: sample and
permutation entropy, aperiodic 1/f slope, peak-alpha-frequency difference, and
O₁–O₂ magnitude-squared coherence in the θ, α and β bands. A causal exponential
moving-average smoother (τ = 600 s) runs on the posterior, and a per-driver
percentile-calibrated threshold sets the alarm.

The load-bearing feature is **inter-hemispheric coherence**. Removing that one
family costs more than removing any other, and coherence falls as drivers become
drowsy in every band, most strongly in β (Cohen's *d* = −0.40, *p* < 10⁻⁵⁰
across 14 498 epochs).

## Results

Everything below is under **strict leave-one-subject-out** cross-validation: no
subject contributes to both training and test.

**Monitoring — DROZY, 10 subjects, 14 498 epochs**

| Pipeline | F1 | AUC | κ |
|---|---|---|---|
| Lean 10-feature LDA | 62.08 % | 64.55 % | 0.242 |
| **+ causal EMA smoother** | **76.79 %** | **76.62 %** | **0.539** |
| Riemannian tangent space, 2-ch | 57.69 % | — | — |
| EEGNet (Lawhern 2018), 2-ch | 47.32 % | — | — |

The smoother's gain holds up subject-wise: paired Wilcoxon *p* = 0.005,
Cohen's *d* = 1.11, *n* = 10.

**Generalisation**

| Evaluation | F1 |
|---|---|
| Cross-dataset, DROZY → SEED-VIG, no fine-tuning | 64.93 % |
| Pooled 31-subject LOSO, DROZY ∪ SEED-VIG | 66.13 % |

**Advance prediction — SEED-VIG, 21 subjects.** Survival-framed and
FPR-controlled, measured against a PERCLOS behavioural anchor:

| Behavioural onset | Sessions flagged early | Median lead | Per-session false-alert rate |
|---|---|---|---|
| Mild, PERCLOS > 0.30 | 71.4 % | **+8.83 min** | 0.0 % |
| Severe, PERCLOS > 0.70 | 85.7 % | **+31.67 min** | 9.5 % |

**Cost to run:** 56 ms per 10-second epoch on a laptop CPU, with under 100 bytes
of trained model state — an ARM Cortex-M4 target. Per-driver calibration adds
about 5 kB per driver and refits in milliseconds via closed-form Ledoit–Wolf
shrinkage.

Negative results are reported as well: phase-coherence variants (PLV, ImCoh,
wPLI) add nothing over magnitude coherence at two channels, and a three-model
posterior ensemble does not beat the smoothed lean LDA on its own.

> **On the 9.5 % above.** It is a *per-session false-alert rate* for the
> advance-prediction track at the severe PERCLOS threshold. A different,
> deprecated "9.5 % false alarms" appears in this repository's history (see
> below). The two are unrelated quantities — do not conflate them.

## The numbers this repository used to report

An earlier version of this page reported **89.54 % accuracy**, a four-channel
**91.32 %** baseline, a **1.95 % drop**, and a single-subject "27 critical
detections / 9.5 % false alarms". It also claimed drowsiness prediction
"5–10 minutes in advance".

**Those figures are wrong and must not be cited.** They came from a stratified
random epoch split that placed epochs from the same subject in both training and
test — subject-level leakage, which lets a classifier recognise the subject
rather than the state.

The full record is frozen in [DEPRECATED_RESULTS.md](DEPRECATED_RESULTS.md), and
[WORK_DIARY.md](WORK_DIARY.md) is kept as a dated log carrying the same warning.
Nothing has been deleted: the error and its correction are both part of the
record.

The corrected results are in the tables above. They are lower than the
leaked-split figures, and they are real.

## Reproducing

```bash
pip install -r requirements.txt
python reproduce.py --list      # the 18-step plan, and where it will look
python reproduce.py             # run everything not already done
python reproduce.py --only v17  # just the monitoring headline
```

Each step is skipped when its output already exists, so an interrupted run
restarts cheaply. Budget roughly 5 minutes, or about 1.5 hours if you include
the EEGNet baseline, on a laptop CPU with no GPU.

The `publication_results_v*.json` files here are the archived outputs behind
every number in the paper; a fresh run should reproduce them to floating-point
tolerance.

### Data access

Neither dataset is redistributed here — both require accepting their own terms.

- **DROZY** — University of Liège; Massoz *et al.*, IEEE WACV 2016. Extract the
  occipital channels with `extract_O1_O2_channels.py`, which writes
  `DROZY_O1_O2/`.
- **SEED-VIG** — Shanghai Jiao Tong University, BCMI Lab; Zheng and Lu,
  *J. Neural Eng.* 2017. Place `Raw_Data/` and `perclos_labels/` beside the
  analysis scripts, or point at them with the `SEED_VIG_DIR` environment
  variable.

## Layout

```
reproduce.py                   single-entry reproducer
requirements.txt               pinned dependencies
publication_results_v*.json    archived results behind the paper
DEPRECATED_RESULTS.md          the leaked-split record, frozen
WORK_DIARY.md                  dated development log (deprecated numbers)

submission_compact/            the manuscript: main.tex, references.bib,
                               figures/, supplementary/
submission_ready/              the built IEEE upload package, and the scripts
                               that build and verify it
submission/                    2026-08-02 base, kept for reference only
```

The manuscript's figures are generated, not hand-made: each generator writes its
final `fig1_`…`fig5_` name straight into `submission_compact/figures/`, as
vector PDF for the paper and PNG for the portal. There is no copy-and-rename
step in the build.

## Status and licence

Submitted to the IEEE Sensors Journal on 6 August 2026. **Not yet peer-reviewed.**
A Zenodo DOI will be minted from the release if and when the paper is accepted.

No licence has been chosen yet, so default copyright applies and no permissions
are granted. If you want to use any of this, please ask the corresponding author.
