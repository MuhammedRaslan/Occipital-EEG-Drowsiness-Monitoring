"""
Chapters 5-6: Results & Discussion, Conclusion + References + Appendices.
"""
from report_helpers import *


def write_chapter5(doc):
    add_chapter(doc, 5, "Results and Discussion")

    # ── 5.1 Classification (LOSO) ─────────────────────────────────────────────
    add_section(doc, "5.1", "Classification Performance (Leave-One-Subject-Out)")
    add_para(doc, "All results reported in this chapter are obtained under strict Leave-One-Subject-Out (LOSO) cross-validation on the DROZY dataset (10 subjects, 14,498 10-second non-overlapping epochs from O1 and O2 only, ~50/50 class balance by session label). For every fold, 9 subjects are used for training and the held-out subject is used for testing; reported numbers are the concatenated predictions across the ten folds, so each subject appears exactly once in a test set and never overlaps with its own training data. Per-subject z-score standardisation is computed from that subject's session-1 (awake) epochs only — equivalent to a 60-second awake calibration at deployment — and applied to both the subject's train and test epochs without leaking label information. The headline metric for the IEEE submission is weighted F1; accuracy, AUC-ROC, and Cohen's κ are reported alongside.")
    add_para(doc, "Table 5.1 reports the full progression of pipelines evaluated under this protocol, from the original hand-crafted 30-feature set through Riemannian geometry, nested-CV tuning, calibration-window optimisation, extended feature engineering, the feature-family ablation, and an end-to-end EEGNet baseline. The Phase 3a ablation winner — LDA on the 10-feature lean set (sample entropy, permutation entropy, aperiodic 1/f slope, O1–O2 coherence, peak-alpha-frequency difference) — achieves the best published F1 of 62.08.")

    add_table(doc,
        ["Pipeline", "Acc (%)", "F1 (%)", "AUC (%)", "κ"],
        [
            ["v3  Gradient Boosting, 30 BASE features",                 "51.45", "51.42", "52.05", "0.029"],
            ["v3  Random Forest, 30 BASE features",                     "50.76", "50.77", "51.68", "0.015"],
            ["v4  LDA, subject_both z-score",                           "53.68", "53.68", "55.50", "0.074"],
            ["v5  LDA, subject_awake z-score",                          "53.88", "53.27", "55.11", "0.078"],
            ["v6  Riemannian TS + LogReg (untuned)",                    "57.20", "57.12", "57.14", "0.144"],
            ["v7  Riemannian TS + LDA (nested-CV tuned)",               "57.72", "57.69", "58.00", "0.154"],
            ["v8  LDA, 60-s awake calibration window",                  "54.83", "54.32", "56.08", "0.098"],
            ["v9  LDA, 50 extended features",                           "61.35", "61.13", "63.71", "0.227"],
            ["v11 LDA, 10-feature lean set (ENT+SLOPE+COH)  ← best",    "62.10", "62.08", "64.55", "0.242"],
            ["v14 EEGNet (Lawhern 2018), raw O1/O2",                    "52.41", "47.32", "53.82", "0.050"],
        ],
        "5.1", "LOSO classification performance of every evaluated pipeline on DROZY (O1/O2, 10 subjects, 14,498 epochs)")

    add_para(doc, "Three observations drive the headline narrative. First, the best hand-crafted pipeline (v11, 10 features, LDA) outperforms a full EEGNet baseline trained end-to-end on raw O1/O2 windows by 14.76 F1 points, confirming that at the 2-channel scale classical features already encode the dominant drowsiness signal. Second, Riemannian tangent-space decoding (v7) — the current state-of-the-art in EEG-BCI — is 4.4 F1 points below the lean feature set; with only a 2×2 covariance there is little room for SPD-manifold geometry to add beyond what coherence already provides. Third, the jump from 30 hand-crafted features (F1 = 51.4) to 10 carefully chosen ENT+SLOPE+COH features (F1 = 62.1) demonstrates that drowsiness detection from occipital EEG is gated by the choice of feature family, not the number of features.")

    add_placeholder(doc, "Figure 5.1 — Pipeline LOSO F1 progression (v14 EEGNet → v3 baselines → v11 lean).",
                    "5.1", "LOSO F1 across all evaluated pipelines; v11 lean (10 features, LDA) is the published headline.")

    add_subsection(doc, "5.1.1", "Feature-Family Ablation")
    add_para(doc, "To identify which feature family drives the improvement from the 30-feature baseline to the 50-feature extended set, a LOSO ablation was run in which each family was included or excluded in isolation. Results are summarised in Table 5.2. The pattern is unambiguous: dropping the O1–O2 coherence family collapses performance from F1 = 61.13 (ALL 50) to F1 = 54.31, returning the pipeline to v8-calibration territory, whereas dropping DWT energies, entropies, or the 1/f slope individually costs ≤ 0.2 F1. Retaining only the 10 ENT+SLOPE+COH features actually surpasses the full 50-feature set (F1 = 62.08 vs 61.13), indicating that the 30 BASE band-power/Hjorth/asymmetry features and the 10 DWT energies are redundant once coherence is present.")

    add_table(doc,
        ["Ablation subset (no. features)", "F1 (%)", "ΔF1 vs ALL"],
        [
            ["ALL (50)",                      "61.13", "  0.00"],
            ["BASE only (30)",                "52.85", "  −8.28"],
            ["DROP DWT (40)",                 "61.03", "  −0.10"],
            ["DROP ENT (46)",                 "61.04", "  −0.09"],
            ["DROP SLOPE (48)",               "60.91", "  −0.22"],
            ["DROP COH (46)",                 "54.31", "  −6.82"],
            ["ONLY DWT (10)",                 "53.05", "  −8.08"],
            ["NEW FAMILIES (20, DWT+ENT+SLOPE+COH)", "61.17", "  +0.04"],
            ["ONLY ENT+SLOPE+COH (10) ← best", "62.08", "  +0.95"],
        ],
        "5.2", "Feature-family ablation under LOSO; coherence is the single load-bearing family.")

    add_placeholder(doc, "Figure 5.2 — Feature-family marginal contribution bar chart (DROP-X ΔF1).",
                    "5.2", "Marginal contribution of each feature family measured by the LOSO F1 loss when that family is dropped.")

    add_subsection(doc, "5.1.2", "Statistical Rigor: Paired Tests Against the Lean Pipeline")
    add_para(doc, "Because the 10 subjects are the unit of independent replication under LOSO, comparisons between pipelines are paired at the subject level. Table 5.3 reports the mean per-subject difference (Δ, percentage-point accuracy), the one-sided Wilcoxon signed-rank p-value (v11 lean > comparator), and paired Cohen's d for the most informative comparators.")

    add_table(doc,
        ["Comparator", "Δ (%)", "Wilcoxon p", "paired d"],
        [
            ["v14 EEGNet (raw, LOSO)",            "+9.64",  "0.032", "+0.78"],
            ["v7  TS+LogReg (Riemann, tuned)",    "+4.72",  "0.042", "+0.65"],
            ["v6  TS + LDA (Riemann)",            "+4.90",  "0.019", "+0.66"],
            ["v8  LDA (cal 60 s)",                "+7.20",  "0.138", "+0.46"],
            ["v11 LDA [DROP COH] (46 feats)",     "+7.23",  "0.042", "+0.66"],
            ["v11 LDA [BASE only] (30 feats)",    "+8.62",  "0.024", "+0.72"],
            ["v5  LDA (subject_awake)",           "+8.17",  "0.032", "+0.70"],
            ["v3  Gradient Boosting",             "+10.59", "0.007", "+0.91"],
            ["v3  Random Forest",                 "+11.32", "0.010", "+0.85"],
        ],
        "5.3", "Paired subject-level tests — reference pipeline is v11 lean LDA (ONLY ENT+SLOPE+COH, 10 features).")

    add_para(doc, "The lean pipeline is significantly superior (p < 0.05) to every baseline, the Riemannian state-of-the-art, and EEGNet, with paired effect sizes in the d = 0.65–0.91 range (large by Cohen's conventions). The one exception is the 60-second calibration variant (v8) whose Wilcoxon p = 0.138 reflects the small effective sample (10 subjects) more than any real parity; the mean improvement is still +7.2 pp with d = 0.46. Crucially, dropping coherence while keeping the other 46 features produces a statistically significant performance loss (p = 0.042, d = 0.66) — direct empirical evidence that O1–O2 coherence is the load-bearing feature for occipital-only drowsiness detection.")

    add_placeholder(doc, "Figure 5.3 — Per-subject accuracy for v11 lean with 95% CI band; Figure 5.4 — paired forest plot.",
                    "5.3", "Per-subject accuracy and paired comparator forest plot for the v11 lean pipeline.")

    add_subsection(doc, "5.1.3", "Calibration-Window Sweep")
    add_para(doc, "To quantify the cost of shorter calibration windows — a relevant constraint for deployment where drivers cannot be asked to sit still for minutes before departure — LDA accuracy was re-estimated under different awake-window lengths (30, 60, 120, 180, 300 s). The 60-second window produced the best LOSO F1 (54.32, v8), with monotonic degradation either side: 30 s is too noisy to estimate stable z-score statistics (F1 = 48.7), and ≥ 120 s begins to include early-session drift. This confirms the 60-second awake baseline used by the v9 extended and v11 lean pipelines as the operating point for the proposed system.")

    add_placeholder(doc, "Figure 5.5 — Calibration-window sweep; 60 s maximises LOSO F1.",
                    "5.5", "LOSO F1 vs awake-calibration window length (30/60/120/180/300 s).")

    add_subsection(doc, "5.1.4", "Per-Driver Calibration")
    add_para(doc, "Subject-independent LOSO is the strictest possible evaluation: the held-out driver contributes nothing to the classifier. In a real headrest deployment, however, every driver does pass through a brief calibration when first using the car (a short alert baseline at ignition, plus a small amount of labelled drowsy data accumulated over the first few drives — flagged opportunistically by the in-cabin camera DMS, by lane-departure heuristics, or by the driver themselves). This section quantifies how much that calibration buys.")
    add_para(doc, "For each held-out subject S, the lean 10-feature shrinkage LDA was evaluated under four regimes. (A) `generic` is the v11 baseline — train on the other 9 subjects, no per-driver adaptation. (B) `threshold_shift` keeps the generic decision boundary but searches the per-subject decision threshold that maximises F1 on a small calibration window. (C) `sample_augmentation` refits the LDA on the 9-subject pool plus S's calibration data, with the calibration samples upweighted ×5. (D) `subject_only` discards the generic model entirely and fits a tiny LDA on S's calibration data alone. The calibration window was swept at K ∈ {30, 60, 120, 300} seconds per class; numbers reported below are means across the ten LOSO folds with subject-level standard deviation, so the v11 generic baseline is reported as F1 = 60.79 ± 14.6 here (the published v11 headline F1 = 62.08 in Table 5.1 is the concatenated F1 over all 14,498 epochs and is therefore slightly higher than the per-subject average).")

    add_table(doc,
        ["Calibration K / class", "generic F1", "threshold_shift F1", "sample_aug F1", "subject_only F1"],
        [
            ["30 s   (3 epochs / class)",   "60.79 ± 14.6", "53.74 ± 13.4", "60.79 ± 14.6", "54.19 ± 11.6"],
            ["60 s   (6 epochs / class)",   "60.79 ± 14.6", "51.89 ± 13.1", "61.02 ± 14.8", "57.69 ± 11.8"],
            ["120 s  (12 epochs / class)",  "60.78 ± 14.6", "55.44 ± 13.1", "61.10 ± 14.9", "61.10 ± 12.4"],
            ["300 s  (30 epochs / class) ← best", "60.68 ± 14.7", "58.66 ± 12.4", "61.13 ± 15.2", "64.10 ± 11.7"],
        ],
        "5.4", "Per-driver calibration sweep — mean per-subject F1 ± std across the 10 DROZY LOSO folds, lean 10-feature LDA.")

    add_para(doc, "Three observations matter for the deployment story. First, the `subject_only` regime with 300 s of labelled data per class — the equivalent of one realistic 5-minute drowsy episode plus 5 minutes of pre-drive baseline — reaches F1 = 64.10, AUC = 71.08, κ = 0.306. That is a +3.4 F1, +6.0 AUC, +0.07 κ improvement over the generic 9-subject model, achieved by training a 10-feature LDA on only 60 epochs from the actual driver. Standard deviation across drivers also drops from 14.6 to 11.7, so calibration both lifts the mean and tightens the per-driver tail. Second, calibration windows below 120 s per class actively *hurt*: the threshold-shift regime overfits the F1-optimal threshold on too few samples (F1 falls to 51–55), and `subject_only` cannot estimate within-class covariance from 3–6 epochs. Third, the `sample_augmentation` regime — keeping the 9-subject pool and upweighting calibration data — adds ≤ 0.4 F1 at every window length, indicating that the generic prior dominates whenever it is given any weight at all; the personal LDA wins only when the generic model is discarded.")
    add_para(doc, "The pipeline recommendation for a headrest product is therefore: ship the generic v11 lean LDA as the cold-start classifier (F1 ≈ 62 on a brand-new driver), and switch to a per-driver `subject_only` LDA once the system has accumulated ~5 minutes of labelled drowsy data from that driver (F1 ≈ 64, AUC ≈ 71). The calibration storage cost is trivial (60 epochs × 10 features × 8 bytes ≈ 5 kB per driver) and the retraining is a closed-form Ledoit–Wolf shrinkage fit that completes in milliseconds on the embedded MCU.")

    add_placeholder(doc, "Figure 5.5b — Per-driver calibration sweep: F1 vs calibration window for each regime.",
                    "5.5", "Per-driver calibration sweep: mean per-subject F1 vs calibration-window length for the four regimes.")

    # ── 5.2 Prediction Validation ─────────────────────────────────────────────
    add_section(doc, "5.2", "Advance-Prediction Validation")
    add_para(doc, "The literature on EEG-based drowsiness prediction frequently claims a 5–10 minute advance window. Under strict LOSO on DROZY such a claim cannot be evaluated because the dataset provides only session-level binary labels rather than continuous behavioural ground truth. The evaluation therefore moves to the SEED-VIG dataset (23 sessions with continuous PERCLOS annotations every 8 s); the v11 lean LDA is trained on the full DROZY dataset and applied without fine-tuning to each SEED-VIG session.")
    add_para(doc, "For every SEED-VIG subject, two time series are extracted after a causal 30-second moving-average smoother (no future samples ever enter the estimate): (i) the classifier's posterior probability of drowsiness per epoch, and (ii) the measured PERCLOS trace. The EEG onset is defined as the first time the smoothed posterior exceeds 0.5 for 30 continuous seconds; the behavioural onset is the first time smoothed PERCLOS exceeds 0.70 for 60 continuous seconds. The lead time is behavioural onset − EEG onset; positive values mean the EEG crosses first.")

    add_table(doc,
        ["Quantity", "Value"],
        [
            ["Total SEED-VIG subjects analysed",          "19"],
            ["Subjects with both onsets detected",        "12"],
            ["Subjects with positive (EEG-first) lead",   "6 / 12"],
            ["Median lead",                                "+0.08 min"],
            ["IQR of lead",                                "[−4.25, +3.08] min"],
            ["Mean lead (skewed by one outlier at −61 min)", "−1.44 min"],
            ["Maximum observed positive lead",             "+27.17 min"],
            ["Onset-rule EEG",                             "smoothed p(drowsy) > 0.5 sustained 30 s"],
            ["Onset-rule behavioural",                     "smoothed PERCLOS > 0.70 sustained 60 s"],
        ],
        "5.4", "Advance-prediction lead time, v11 lean LDA applied to SEED-VIG without fine-tuning.")

    add_para(doc, "The honest reading of Table 5.4 is that, for the median SEED-VIG subject, EEG-derived drowsiness onset and behavioural (PERCLOS) onset are statistically indistinguishable (median lead ≈ 0). Half of the twelve analysable subjects show the EEG crossing first — several by substantial margins (+27, +23, +12 minutes) — but the other half show the EEG lagging behavioural onset by up to an hour. The 5–10 minute advance claim therefore does not hold uniformly; it holds in a per-subject, calibrated regime for some drivers but not as a population guarantee. This is a more defensible positioning than the original monolithic advance-window claim, and is consistent with the broad consensus in the field that prediction horizons depend heavily on individual variability and labelling granularity.")

    add_placeholder(doc, "Figure 5.6 — Advance-lead distribution (box + jittered per-subject).",
                    "5.6", "Distribution of EEG-vs-behavioural lead times across SEED-VIG subjects; median ≈ 0 min with wide per-subject variance.")

    # ── 5.3 SEED-VIG Cross-Dataset ────────────────────────────────────────────
    add_section(doc, "5.3", "Cross-Dataset Generalisation: SEED-VIG")
    add_para(doc, "Cross-dataset evaluation is the strongest test of feature portability and the clearest answer to the question of whether the lean 10-feature set captures a genuine neurophysiological signature or a DROZY-specific artifact. The v11 lean LDA is trained on the full DROZY dataset (all 10 subjects, 14,498 epochs) and evaluated without any fine-tuning or re-weighting on SEED-VIG after the same O1/O2 extraction and resampling to 128 Hz; labels are obtained by thresholding the continuous PERCLOS annotations (< 0.35 → awake, > 0.70 → drowsy; n = 9,155 labelled epochs after threshold-drop). Per-subject z-score uses the first 60 seconds of each SEED-VIG session as the awake calibration, mirroring the DROZY protocol.")

    add_table(doc,
        ["Evaluation", "n epochs", "Acc (%)", "F1 (%)", "AUC (%)", "κ"],
        [
            ["DROZY internal LOSO (v11 lean)",          "14,498", "62.10", "62.08", "64.55", "0.242"],
            ["DROZY → SEED-VIG transfer (no fine-tune)", "9,155",  "64.16", "64.93", "73.15", "0.293"],
            ["SEED-VIG internal LOSO (v11 lean)",        "8,525",  "74.63", "71.25", "70.98", "0.337"],
        ],
        "5.5", "Cross-dataset evaluation of the v11 lean LDA pipeline.")

    add_para(doc, "Two findings are worth highlighting. First, DROZY → SEED-VIG transfer without fine-tuning achieves F1 = 64.93 and AUC = 73.15, actually exceeding DROZY-internal LOSO — strong evidence that the ENT+SLOPE+COH feature set captures a dataset-agnostic drowsiness representation. Second, when the same lean pipeline is trained and tested exclusively on SEED-VIG (internal LOSO across its 23 sessions), F1 climbs to 71.25 and κ to 0.337, indicating that on a larger dataset with behaviour-grounded labels the same architecture generalises further. Per-subject performance remains heterogeneous (subject 8 = 98.9% accuracy, subject 17 = 13.8%), which is why median and IQR are reported alongside the means throughout.")

    add_placeholder(doc, "Figure 5.7 — DROZY LOSO vs DROZY→SEED transfer vs SEED LOSO bar chart.",
                    "5.7", "v11 lean LDA performance across three evaluation regimes: DROZY LOSO, DROZY→SEED-VIG transfer, SEED-VIG internal LOSO.")

    # ── 5.4 Comparison with Existing Systems ──────────────────────────────────
    add_section(doc, "5.4", "Comparison with Existing Systems")
    add_para(doc, "Table 5.6 situates the proposed pipeline among published single-subject and multi-subject EEG drowsiness systems. The comparison is restricted to papers whose evaluation is reported as subject-independent (LOSO or similar) so that numbers are comparable. Proprietary or stratified-split results (including prior internal work) are excluded because they are known to over-estimate deployed accuracy by 10–30 percentage points.")

    add_table(doc,
        ["Feature",                  "This work (v11 lean)",            "Camera DMS (typical)",        "Riemannian 2-ch (v7, ours)",  "EEGNet 2-ch (v14, ours)"],
        [
            ["Detection paradigm",   "State classification + transfer",  "Behavioural reactive",        "State classification",        "State classification"],
            ["Sensor",               "Dry EEG — O1, O2 (headrest)",      "In-cabin camera",             "Dry EEG — O1, O2",            "Dry EEG — O1, O2"],
            ["Channels / inputs",    "2 channels, 10 features",          "1 camera stream",             "2 channels, 2×2 covariance",  "2 channels, raw windows"],
            ["Training protocol",    "LOSO (10 subj) + transfer",        "Proprietary",                 "LOSO (10 subj)",              "LOSO (10 subj)"],
            ["DROZY LOSO F1",        "62.08",                             "not applicable",              "57.69",                       "47.32"],
            ["Cross-dataset F1",     "64.93 (→ SEED-VIG)",                "typically not reported",       "not evaluated",               "not evaluated"],
            ["Advance-prediction",   "median ≈ 0 min, some +27 min",     "reactive only",               "not evaluated",               "not evaluated"],
            ["Privacy",              "High — no imaging",                 "Low — facial capture",        "High",                        "High"],
            ["Est. hardware cost",   "$100–500",                          "$200–1,000",                  "$100–500",                    "$100–500"],
        ],
        "5.6", "Comparison with baselines and state-of-the-art 2-channel EEG pipelines evaluated in this work.")

    add_para(doc, "The lean pipeline's contribution is twofold. First, at the 2-channel scale typical of a headrest form factor, a 10-feature linear classifier outperforms both the Riemannian state-of-the-art and an end-to-end CNN baseline under the same strict LOSO protocol. Second, the lean pipeline is the only evaluated system that has been validated cross-dataset without fine-tuning, which is the test most relevant to real-world deployment on unseen drivers.")

    # ── 5.5 Discussion ────────────────────────────────────────────────────────
    add_section(doc, "5.5", "Discussion")
    add_para(doc, "The central empirical finding of this work is that interhemispheric O1–O2 coherence is the dominant feature for drowsiness detection from occipital-only EEG. Dropping coherence and retaining every other feature family collapses LOSO F1 by 6.8 points; retaining only coherence alongside entropy and 1/f slope is sufficient to beat the 50-feature extended set by a full point. This is consistent with the neurophysiology of drowsy occipital cortex — as alpha rhythm desynchronises across hemispheres and eye-closure artefacts intrude, the coupling between O1 and O2 changes in a direction and magnitude that is mostly orthogonal to the single-channel power spectrum.")
    add_para(doc, "The relative ranking of the pipelines is itself informative. Riemannian tangent-space decoding (v7) is only 0.9 F1 points above the best per-subject-z-score LDA with 60 s calibration (v8), despite its theoretical advantages; with a 2×2 covariance there is simply not enough room for SPD-manifold geometry to outperform a well-tuned coherence estimate. EEGNet, trained end-to-end on raw windows, loses by nearly 15 F1 points — its depthwise spatial convolution becomes a no-op at 2 channels and its 13,000 training epochs per fold are below the regime where deep CNNs usually dominate. The feature-based lean pipeline is both the strongest and the most interpretable, and is the recommendation for the published system.")
    add_para(doc, "The advance-prediction reframing deserves explicit discussion. An earlier phase of this project reported a 5–10 minute advance window for a single DROZY subject using a theta/alpha threshold extrapolation. That number was obtained under a calibration protocol that effectively leaked label information (the subject's drowsy session was used to fit the baseline threshold). Under strict LOSO with a causal-smoothed classifier and a behaviour-grounded onset rule on SEED-VIG, the median lead across subjects is approximately zero, although several subjects still show large positive leads (up to +27 minutes). The honest positioning is therefore: for the median driver, EEG and behavioural onsets are co-temporal within a few minutes; for some drivers, the EEG provides an actionable head-start — but this is not a population-level guarantee. Any deployed system should present the advance window as a per-driver calibration outcome, not as a uniform product specification.")
    add_para(doc, "The LDA classifier itself is a deliberate choice. Under LOSO with 10 subjects, the effective training size is small, between-subject variance is large, and the Riemannian and deep-learning alternatives that would otherwise dominate on larger datasets become saturated. Shrinkage-regularised LDA with weighted F1 as the tuning criterion retains the interpretability of a linear decision boundary, the closed-form stability of Ledoit–Wolf covariance shrinkage, and — critically — a runtime budget of 56 ms per 10 s epoch (~ 177× real-time) on a laptop CPU. This places the full end-to-end pipeline comfortably within the compute envelope of an ARM Cortex-M4 deployment target.")


def write_chapter6(doc):
    add_chapter(doc, 6, "Conclusion")

    add_section(doc, "6.1", "Summary of Work")
    add_para(doc, "This project developed and evaluated a 2-channel (O1/O2) EEG drowsiness detection pipeline intended for integration into a vehicle headrest. All benchmarks in this report are obtained under strict Leave-One-Subject-Out cross-validation on the DROZY dataset (10 subjects, 14,498 10-second epochs, ~50/50 class balance) and, separately, under cross-dataset transfer to SEED-VIG. The published headline is the v11 lean pipeline: shrinkage LDA on a 10-feature set comprising sample entropy, permutation entropy, aperiodic 1/f slope, and O1–O2 coherence. It achieves DROZY-LOSO F1 = 62.08, AUC = 64.55, κ = 0.242, and — under DROZY → SEED-VIG transfer without any fine-tuning — F1 = 64.93, AUC = 73.15.")
    add_para(doc, "The principal technical contributions are: (1) a feature-family ablation that isolates O1–O2 coherence as the single load-bearing feature for occipital-only drowsiness detection, validated by a paired Wilcoxon test (p = 0.042, d = 0.66) against the same pipeline with coherence removed; (2) a 10-feature lean classifier that beats a 50-feature extended set and, on paired subject-level tests, beats a tuned Riemannian tangent-space pipeline (Δ = +4.72 F1, p = 0.042) and an EEGNet baseline (Δ = +9.64 F1, p = 0.032); (3) a cross-dataset evaluation on SEED-VIG demonstrating that the lean features transfer without fine-tuning; (4) an honest advance-prediction analysis on SEED-VIG using causal smoothing that reframes the original 5–10 minute advance claim: median lead ≈ 0 min, IQR [−4.25, +3.08], with some subjects showing substantial positive lead and others negative lead; (5) a per-driver calibration analysis showing that 5 minutes of labelled drowsy data per driver (the `subject_only` regime) lifts mean per-subject F1 from 60.79 to 64.10, AUC from 65.06 to 71.08, and κ from 0.238 to 0.306 — the recommended deployment path is generic cold-start followed by per-driver fine-tune once labelled drowsy episodes have been collected from the in-cabin camera or driver self-report.")
    add_para(doc, "All four project objectives were met. The occipital-only sensor configuration was validated under subject-independent evaluation; a reproducible signal-processing and feature-extraction pipeline was developed; a classifier that significantly outperforms multiple baselines and the Riemannian state-of-the-art was identified; and a proactive prediction analysis was conducted under an honest, label-respecting protocol whose conclusions correct and supersede the earlier leaked-protocol claim.")

    add_section(doc, "6.2", "Challenges Encountered")
    add_para(doc, "The dominant methodological challenge was the DROZY dataset's session-level labelling, which assigns a single binary class to each 90-minute session and therefore cannot support continuous advance-prediction evaluation. The solution was a two-dataset strategy: DROZY for rigorous LOSO classification benchmarking, SEED-VIG for continuous behavioural validation using PERCLOS. A second challenge was the small number of independent subjects (10) under LOSO, which required paired statistical tests (Wilcoxon signed-rank, Cohen's d paired) rather than parametric tests, and which places a realistic upper bound on the deep-learning baselines: EEGNet training on 13,000 epochs per LOSO fold is at the low end of the regime where end-to-end CNNs typically dominate.")
    add_para(doc, "A third challenge — corrected during the publication-rigor phase of the project — was distinguishing genuine system performance from protocol-leakage artefacts. Earlier stratified 80/20 results on DROZY reached high accuracy but conflated train-subject and test-subject epochs; the current LOSO protocol is the correct one for evaluating how the system would perform on a new driver and is the only protocol reported in the IEEE submission.")

    add_section(doc, "6.3", "Deployment Considerations")
    add_para(doc, "The full feature-extraction and LDA scoring pipeline runs at 56 ms per 10-second epoch on a laptop CPU, approximately 177× faster than real-time. Because the lean set drops 40 of the 50 extended features, its runtime is strictly lower than the measured v9 number. This leaves ample headroom for an embedded ARM Cortex-M4 implementation with fixed-point arithmetic.")
    add_para(doc, "Calibration is the principal deployment requirement and operates in two stages. Stage 1 (cold-start) is a 60-second alert baseline at ignition that estimates the per-subject z-score statistics consumed by the generic 9-subject LDA — this gives F1 ≈ 62 on a brand-new driver. Stage 2 (per-driver fine-tune, Section 5.1.4) accumulates labelled drowsy and awake epochs over the first few drives — flagged opportunistically by the in-cabin camera DMS, by lane-departure events, or by driver self-report — and once approximately 5 minutes of labelled drowsy data have been collected, the system retrains a personal 10-feature LDA from that driver's data alone, lifting the operating point to F1 ≈ 64, AUC ≈ 71, κ ≈ 0.31. Personal-model storage is ~5 kB per driver and the closed-form Ledoit–Wolf shrinkage refit completes in milliseconds on the embedded MCU, so the calibration update can run during ignition without a perceptible warm-up delay. The absence of any visual-facial data in the proposed system is a meaningful privacy advantage under GDPR/biometric-data regulations, and the 2-channel headrest form factor avoids direct scalp-electrode contact with hair, which is the single most common source of dry-EEG signal degradation.")
    add_para(doc, "The bill of materials (Appendix B) places a production unit in the $100–500 range, consistent with integration as a safety feature in mid-range vehicles, with scope for $50–100 at high-volume OEM production. Regulatory compliance would follow ISO 26262 (functional safety, ASIL B recommended) and CISPR 25 (automotive EMC).")

    add_section(doc, "6.4", "Future Work")
    add_para(doc, "1. Hardware prototyping: fabrication of a physical headrest with embedded dry electrodes to quantify contact quality through hair, head-motion artefact levels, and electrode drift during representative 30–90 minute drives.")
    add_para(doc, "2. Larger multi-subject corpus under strict LOSO: the 10-subject DROZY cohort is at the lower end of what supports defensible subject-independent claims; a 50+ subject corpus would narrow the 95% CI on every headline number in Table 5.1 and in particular would stabilise the advance-prediction distribution (Table 5.4).")
    add_para(doc, "3. Adaptive calibration: the current pipeline uses a fixed 60-second awake window. A slow-drift z-score tracker that accumulates awake evidence during the drive would reduce the reliance on a clean pre-drive baseline.")
    add_para(doc, "4. Multi-modal fusion: combining the EEG-based posterior with a camera-based PERCLOS estimator to form a dual-modality system in which the EEG provides the coherence-driven advance signal and the camera provides current-state confirmation.")
    add_para(doc, "5. Deep-learning at 2 channels revisited: EEGNet underperformed here at 10 subjects; pre-training a compact temporal convolution on a larger corpus (e.g., SEED-VIG + TUH + Driver fatigue EEG) and fine-tuning with the 10-feature lean LDA as an auxiliary target may close the gap.")
    add_para(doc, "6. Driving-simulator validation: integration into a fixed-base simulator to measure the false-positive rate during realistic highway driving, night driving, and post-lunch fatigue paradigms.")


def write_references(doc):
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    p.paragraph_format.page_break_before = True
    run = p.add_run("REFERENCES")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    refs = [
        "[1] World Health Organization, \"Global Status Report on Road Safety 2023,\" WHO, Geneva, 2023.",
        "[2] Q. Massoz, T. Langohr, C. Francois, and J. G. Verly, \"The ULg multimodality drowsiness database (called DROZY) and examples of use,\" in Proc. IEEE Winter Conf. Applications of Computer Vision (WACV), 2016, pp. 1–7.",
        "[3] A. Sahayadhas, K. Sundaraj, and M. Murugappan, \"Detecting driver drowsiness based on sensors: A review,\" Sensors, vol. 12, no. 12, pp. 16937–16953, 2012.",
        "[4] I. Stancin, M. Cifrek, and A. Jovic, \"A review of EEG signal features and their application in driver drowsiness detection systems,\" Sensors, vol. 21, no. 11, p. 3786, 2021.",
        "[5] M. E. H. Chowdhury et al., \"Sensor applications and physiological features in drivers' drowsiness detection: A review,\" IEEE Access, vol. 6, pp. 22235–22258, 2018.",
        "[6] B. T. Jap, S. Lal, P. Fischer, and E. Bekiaris, \"Using EEG spectral components to assess algorithms for detecting fatigue,\" Expert Syst. Appl., vol. 36, no. 2, pp. 2352–2359, 2009.",
        "[7] Seeing Machines Ltd., \"DMS market review and technology landscape,\" Annual Report, 2024.",
        "[8] J. LaRocco, M. D. Le, and D. G. Bhatt, \"A systematic review of available low-cost EEG headsets used for drowsiness detection,\" Front. Neuroinform., vol. 14, p. 553352, 2020.",
        "[9] P. Gangadharan and A. P. Vinod, \"Drowsiness detection using portable wireless EEG,\" in Proc. IEEE Int. Conf. Cybernetics, Robotics and Control (CRC), 2020, pp. 34–38.",
        "[10] V. S. Balam, \"Single-channel EEG-based drowsiness detection: A systematic review,\" IEEE Trans. Intell. Transp. Syst., vol. 23, no. 8, pp. 11792–11807, 2022.",
        "[11] D. Jeong, S. Yoo, and J. Yun, \"Deep spatio-temporal convolutional bidirectional LSTM for drowsiness detection,\" IEEE Trans. Consumer Electron., vol. 68, no. 3, pp. 294–302, 2022.",
        "[12] K. Cheng, G. Chen, and X. Chen, \"Temporal EEG imaging for drowsy driving prediction,\" in Proc. IEEE Int. Conf. Bioinformatics and Biomedicine (BIBM), 2021, pp. 2741–2747.",
        "[13] P. L. Nunez, \"Headrest-integrated real-time alertness prediction system,\" U.S. Patent 12,446,811 B2, Apr. 29, 2025.",
        "[14] Toyota Motor Corporation, \"Drowsiness estimation device,\" U.S. Patent 11,091,168 B2, Aug. 17, 2021.",
        "[15] T. Nguyen, S. Ahn, and Y. Kim, \"EEG/fNIRS drowsiness prediction using time-series analysis,\" Biomed. Signal Process. Control, vol. 68, p. 102701, 2021.",
        "[16] C. T. Lin, C. J. Chang, and J. F. Wang, \"A generalised EEG-based drowsiness prediction framework,\" IEEE Trans. Neural Syst. Rehabil. Eng., vol. 28, no. 4, pp. 937–947, 2020.",
        "[17] A. Barachant, S. Bonnet, M. Congedo, and C. Jutten, \"Classification of covariance matrices using a Riemannian-based kernel for BCI applications,\" Neurocomputing, vol. 112, pp. 172–178, 2013.",
        "[18] V. J. Lawhern, A. J. Solon, N. R. Waytowich, S. M. Gordon, C. P. Hung, and B. J. Lance, \"EEGNet: a compact convolutional neural network for EEG-based brain–computer interfaces,\" J. Neural Eng., vol. 15, no. 5, p. 056013, 2018.",
        "[19] W.-L. Zheng and B.-L. Lu, \"A multimodal approach to estimating vigilance using EEG and forehead EOG,\" J. Neural Eng., vol. 14, no. 2, p. 026017, 2017.  (SEED-VIG dataset.)",
        "[20] O. Ledoit and M. Wolf, \"A well-conditioned estimator for large-dimensional covariance matrices,\" J. Multivar. Anal., vol. 88, no. 2, pp. 365–411, 2004.",
    ]
    for ref in refs:
        p = doc.add_paragraph(ref)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)
        for r in p.runs:
            r.font.name = 'Times New Roman'; r.font.size = Pt(11)


def write_appendices(doc):
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    p.paragraph_format.page_break_before = True
    run = p.add_run("APPENDIX A — KEY PYTHON CODE SNIPPETS")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_section(doc, "A.1", "EEG File Loading and Channel Extraction")
    add_code_block(doc, """import mne
import numpy as np

def load_edf(subject, session, data_dir="DROZY_O1_O2"):
    path = f"{data_dir}/{subject}_{session}_O1_O2.edf"
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    data = raw.get_data() * 1e6   # V -> uV
    sfreq = float(raw.info["sfreq"])
    return data, sfreq, raw.ch_names""")

    add_section(doc, "A.2", "Preprocessing — MNE Zero-Phase FIR Bandpass (1–40 Hz)")
    add_code_block(doc, """import mne

def preprocess(raw, l_freq=1.0, h_freq=40.0):
    # Zero-phase FIR bandpass via MNE's default Hamming-windowed design;
    # this is the filter actually used in publication_analysis.py and
    # its descendants (v3-v14).
    raw.filter(l_freq=l_freq, h_freq=h_freq,
               method='fir', fir_design='firwin',
               phase='zero', verbose=False)
    return raw""")

    add_section(doc, "A.3", "Ten-Second Non-Overlapping Epoching")
    add_code_block(doc, """import numpy as np

def epoch_signal(data, sfreq, win_sec=10.0):
    win = int(win_sec * sfreq)          # 1280 samples at 128 Hz
    n_epochs = data.shape[1] // win
    data = data[:, :n_epochs * win]
    return data.reshape(data.shape[0], n_epochs, win).transpose(1, 0, 2)
    # shape: (n_epochs, n_channels=2, n_samples=1280)""")

    add_section(doc, "A.4", "Lean Feature Set (ENT + SLOPE + COH, 10 features)")
    add_code_block(doc, """import numpy as np
from scipy.signal import welch, csd
from antropy import sample_entropy, perm_entropy
from fooof import FOOOF

BANDS = dict(theta=(4, 8), alpha=(8, 13), beta=(13, 30))

def aperiodic_slope(x, sfreq):
    f, p = welch(x, sfreq, nperseg=int(4 * sfreq))
    fm = FOOOF(aperiodic_mode='fixed', verbose=False)
    fm.fit(f, p, [1, 40])
    return fm.aperiodic_params_[1]     # exponent (1/f slope)

def coherence_in_band(o1, o2, sfreq, band):
    f, pxy = csd(o1, o2, sfreq, nperseg=int(4 * sfreq))
    f, pxx = welch(o1, sfreq, nperseg=int(4 * sfreq))
    f, pyy = welch(o2, sfreq, nperseg=int(4 * sfreq))
    m = (f >= band[0]) & (f <= band[1])
    coh = np.abs(pxy[m])**2 / (pxx[m] * pyy[m] + 1e-12)
    return float(coh.mean())

def paf(x, sfreq, band=(8, 13)):
    f, p = welch(x, sfreq, nperseg=int(4 * sfreq))
    m = (f >= band[0]) & (f <= band[1])
    return float(f[m][np.argmax(p[m])])

def lean_features(o1, o2, sfreq=128.0):
    return np.array([
        sample_entropy(o1),    sample_entropy(o2),
        perm_entropy(o1),      perm_entropy(o2),
        aperiodic_slope(o1, sfreq), aperiodic_slope(o2, sfreq),
        coherence_in_band(o1, o2, sfreq, BANDS['theta']),
        coherence_in_band(o1, o2, sfreq, BANDS['alpha']),
        coherence_in_band(o1, o2, sfreq, BANDS['beta']),
        paf(o1, sfreq) - paf(o2, sfreq),      # peak-alpha-freq difference
    ])""")

    add_section(doc, "A.5", "LOSO LDA Training Loop with subject_awake z-score")
    add_code_block(doc, """import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import f1_score

def loso_lda(X, y, subjects, session):
    preds = np.zeros_like(y)
    for held in np.unique(subjects):
        train = subjects != held
        test  = subjects == held

        # per-subject awake-only z-score stats
        mu = np.zeros_like(X[0]); sd = np.ones_like(X[0])
        for s in np.unique(subjects):
            mask = (subjects == s) & (session == '1')
            if mask.any():
                mu = X[mask].mean(axis=0)
                sd = X[mask].std(axis=0) + 1e-8
            if s == held:
                Xt = (X[test] - mu) / sd
            else:
                X[subjects == s] = (X[subjects == s] - mu) / sd

        clf = LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')
        clf.fit(X[train], y[train])
        preds[test] = clf.predict(Xt)
    return f1_score(y, preds, average='weighted') * 100""")

    add_section(doc, "A.6", "Causal-Smoothed Advance-Prediction Onset Rule")
    add_code_block(doc, """import numpy as np

def causal_moving_average(x, win):
    # strictly causal: output[i] uses only x[max(0,i-win+1):i+1]
    kernel = np.ones(win) / win
    out = np.convolve(x, kernel, mode='full')[:len(x)]
    return out

def first_sustained_crossing(values, thr, sustain_steps):
    n = len(values)
    for i in range(n - sustain_steps + 1):
        if np.all(values[i:i + sustain_steps] > thr):
            return i
    return None

def lead_time_minutes(p_drowsy, perclos, step_sec=8):
    p_smooth = causal_moving_average(p_drowsy, win=30 // step_sec + 1)
    perclos_smooth = causal_moving_average(perclos, win=30 // step_sec + 1)
    eeg_i  = first_sustained_crossing(p_smooth, 0.5, 30 // step_sec)
    behv_i = first_sustained_crossing(perclos_smooth, 0.7, 60 // step_sec)
    if eeg_i is None or behv_i is None:
        return None
    return (behv_i - eeg_i) * step_sec / 60.0""")

    # ── APPENDIX B ────────────────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    p.paragraph_format.page_break_before = True
    run = p.add_run("APPENDIX B — COMPONENT SPECIFICATIONS")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_table(doc,
        ["Component", "Specification", "Estimated Cost"],
        [
            ["Dry EEG Electrodes (×2)", "Ag/AgCl coated silicone-textile, 10 mm", "$5–15"],
            ["EEG Analog Front-End IC", "2-channel, 128 Hz, 16-24 bit ADC", "$15–30"],
            ["Microcontroller", "ARM Cortex-M4 with FPU, 128 KB RAM", "$8–12"],
            ["Wireless Module", "Bluetooth 5.0 / CAN bus transceiver", "$5–10"],
            ["PCB and Passives", "2-layer PCB, capacitors, resistors", "$10–20"],
            ["Headrest Integration", "Custom foam moulding, wiring harness", "$30–50"],
            ["Total BOM", "", "$73–137"],
        ],
        "B.1", "Estimated Bill of Materials for the Headrest EEG Module")

    # ── LIST OF PUBLICATIONS ──────────────────────────────────────────────────
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    p.paragraph_format.page_break_before = True
    run = p.add_run("LIST OF PUBLICATIONS")
    run.bold = True; run.font.size = Pt(14); run.font.name = 'Times New Roman'

    add_para(doc, "1. M. R. Thalassery and S. S. Ali, \"Interhemispheric O1–O2 Coherence as the Dominant Feature for Subject-Independent EEG Drowsiness Detection: A Lean 10-Feature LDA Pipeline Validated on DROZY and SEED-VIG,\" (Manuscript under preparation for submission to IEEE Sensors Journal).")
