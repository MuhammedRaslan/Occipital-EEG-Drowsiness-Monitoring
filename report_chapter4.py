"""
Chapter 4: Methodology (~12-15 pages).
"""
from report_helpers import *


def write_chapter4(doc):
    add_chapter(doc, 4, "Methodology")

    # ── 4.1 System Overview ───────────────────────────────────────────────────
    add_section(doc, "4.1", "System Overview")
    add_para(doc, "The proposed proactive driver monitoring system comprised an end-to-end processing pipeline that transformed raw EEG signals from two occipital electrodes into actionable drowsiness predictions with 5–10 minutes of advance warning. The pipeline operated in eight sequential stages: (1) EEG signal acquisition from O1 and O2 headrest-embedded electrodes at 128 Hz, (2) bandpass filtering to isolate the 0.5–40 Hz frequency range of interest, (3) segmentation into 60-second sliding windows with 30-second overlap, (4) Welch's PSD estimation for each window, (5) theta and alpha band power extraction via trapezoidal integration, (6) feature vector construction, (7) temporal trend analysis using linear regression on a rolling 5-minute buffer, and (8) time-to-threshold extrapolation for alert generation. Figure 4.1 presents the system architecture.")
    add_figure(doc, GENERATED_FIGS.get("sys_arch", ""), "System architecture of the proactive EEG-based driver monitoring system", "4.1")
    add_para(doc, "The data flow pipeline is further detailed in Figure 4.2, showing the transformation of raw microvolt-level EEG signals through each processing stage to the final alert output.")
    add_figure(doc, GENERATED_FIGS.get("dataflow", ""), "Signal processing and data flow pipeline — 8-stage transformation from raw EEG to alert output", "4.2")

    # ── 4.2 Dataset ───────────────────────────────────────────────────────────
    add_section(doc, "4.2", "Dataset")
    add_subsection(doc, "4.2.1", "Primary Dataset: DROZY")
    add_para(doc, "The primary dataset used for system development and validation was the DROZY database, provided by the University of Liège, Belgium [2]. The DROZY dataset was designed specifically for drowsiness research and comprised EEG recordings from controlled driving simulation experiments.")
    add_para(doc, "The dataset included recordings from 10 subjects (6 male, 4 female), each recorded across two sessions. Session 1 was conducted while subjects were in an alert/rested state, while Session 2 was conducted after a period of sleep deprivation designed to induce drowsiness. Each session lasted approximately 90 minutes, yielding a total of approximately 30 hours of continuous EEG data across all subjects and sessions.")
    add_para(doc, "For the present project, only the O1-Ref and O2-Ref channels (occipital electrodes referenced to a common reference) were extracted from the full multi-channel recordings using a custom Python extraction script. The sampling rate was 128 Hz for all recordings. The extracted data were stored in EDF (European Data Format) files, with one file per subject per session (20 files total). Session 1 recordings were assigned the binary label 0 (Alert/Awake), and Session 2 recordings were assigned the label 1 (Drowsy/Sleep-Deprived).")
    add_figure(doc, GENERATED_FIGS.get("dataset", ""), "DROZY dataset structure — 10 subjects × 2 sessions with binary labelling scheme", "4.3")

    add_table(doc,
        ["Parameter", "Value"],
        [
            ["Source", "University of Liège, Belgium"],
            ["Subjects", "10 (6 male, 4 female)"],
            ["Sessions per subject", "2 (Alert + Drowsy)"],
            ["Duration per session", "~60 minutes per session on average"],
            ["Channels extracted", "O1-Ref, O2-Ref"],
            ["Sampling rate", "128 Hz"],
            ["File format", "EDF"],
            ["Epoch length", "10 s non-overlapping"],
            ["Total epochs (10 s)", "14,498"],
            ["Class distribution", "≈ 50% awake (7,234) / 50% drowsy (7,264)"],
            ["Evaluation protocol", "Leave-One-Subject-Out (LOSO)"],
        ],
        "4.1", "DROZY Dataset Parameters (10 s LOSO Protocol)")

    add_subsection(doc, "4.2.2", "Cross-Dataset Validation: SEED-VIG")
    add_para(doc, "The SEED-VIG dataset from Shanghai Jiao Tong University was used for cross-dataset generalization testing. SEED-VIG contained 23 experimental sessions (21 unique subjects; 2 subjects had repeat sessions) recorded with a 17-channel occipital-posterior configuration at 200 Hz, with continuous PERCLOS (percentage of eye closure) values provided every 8 seconds. In this work, raw O1 (channel 15) and O2 (channel 17) were extracted, resampled from 200 Hz to 128 Hz to match the DROZY pipeline, and epoched into 10-second non-overlapping windows. Each epoch was labelled from the mean perclos value inside the window using the thresholds PERCLOS < 0.35 → awake (label 0) and PERCLOS > 0.70 → drowsy (label 1); in-between epochs were discarded. After thresholding, 9,155 labelled epochs from 21 subjects (5,923 awake / 3,232 drowsy) remained for cross-dataset evaluation.")

    # ── 4.3 Hardware Design ───────────────────────────────────────────────────
    add_section(doc, "4.3", "Hardware Design Concept")
    add_para(doc, "The headrest sensor configuration was designed to position EEG electrodes at the O1 and O2 occipital sites (International 10-20 system) within a standard vehicle headrest. The O1 position is located at 20% of the distance from the inion to the nasion, 20% to the left of the midline, while O2 is the corresponding position 20% to the right. These positions naturally fall within the contact zone where the driver's head rests against the headrest during normal driving posture.")
    add_para(doc, "The electrode design employed dry silicone-textured conductive fabric with a 10 mm diameter circular contact area. Unlike wet gel electrodes traditionally used in clinical EEG, dry electrodes achieve acceptable impedance (<50 kΩ optimal, <100 kΩ acceptable) through passive skin contact, including contact through hair in the occipital region. The silicone texture promotes consistent skin coupling while maintaining driver comfort during extended driving periods.")
    add_figure(doc, GENERATED_FIGS.get("headrest", ""), "Headrest-embedded EEG sensor configuration showing O1/O2 electrode placement", "4.4")

    add_table(doc,
        ["Component", "Specification"],
        [
            ["Electrodes", "Dry silicone-textile, 10 mm diameter, Ag/AgCl coated"],
            ["Channels", "2 (O1 + O2) + 1 reference"],
            ["Sampling rate", "128 Hz (min), 256 Hz (optimal)"],
            ["ADC resolution", "16-bit minimum, 24-bit preferred"],
            ["Input impedance", ">10 MΩ"],
            ["Processor", "ARM Cortex-M4 with FPU"],
            ["Connectivity", "CAN bus (vehicle) + Bluetooth (optional)"],
            ["Power consumption", "<6W from 12V vehicle supply"],
            ["Electrode impedance", "<50 kΩ optimal, <100 kΩ acceptable"],
        ],
        "4.2", "Hardware Specifications for the Headrest EEG Module")

    # ── 4.4 Signal Preprocessing ──────────────────────────────────────────────
    add_section(doc, "4.4", "Signal Preprocessing")
    add_para(doc, "Each O1/O2 EDF recording was bandpass filtered to 1–40 Hz using MNE-Python's default zero-phase FIR design (Hamming-windowed sinc, transition bandwidth 1 Hz on both sides, firwin). The 1 Hz high-pass removed slow baseline drift and DC offset from electrode impedance fluctuations; the 40 Hz low-pass attenuated powerline interference (50/60 Hz) and high-frequency muscle artifact while preserving the delta, theta, alpha, and beta bands. FIR filtering was preferred over Butterworth because its exactly linear phase response avoids temporal smearing of event-related features, which is important for the coherence and entropy measures used downstream.")
    add_para(doc, "Filtered signals were segmented into 10-second non-overlapping epochs (1,280 samples per epoch at 128 Hz). A 10-second window was chosen as a compromise between spectral resolution (0.1 Hz bin width from a 10-s Welch segment, sufficient to resolve sub-bands) and temporal responsiveness (10-s update cadence). Non-overlapping epochs were used so that every feature vector represented independent data — this matters for the Leave-One-Subject-Out evaluation in Section 4.6, because overlapping windows would leak information across train/test folds. Across the 10 DROZY subjects × 2 sessions, preprocessing yielded 14,498 epochs (approximately 7,234 awake and 7,264 drowsy).")

    add_figure(doc, EXISTING_FIGS.get("raw_compare", ""), "Raw EEG comparison — Awake (Session 1) vs. Drowsy (Session 2) for O1 and O2 channels, showing the increase in low-frequency rhythmic activity during drowsiness.", "4.5", 5.0)

    # ── 4.5 Feature Extraction ────────────────────────────────────────────────
    add_section(doc, "4.5", "Feature Extraction")
    add_para(doc, "Three feature tiers were evaluated in this work. The baseline 30-feature set reproduced the classical drowsiness biomarker literature (band powers, band-ratio, spectral entropy, Hjorth parameters, zero-crossing rate, skewness per O1/O2 channel plus six cross-channel asymmetry features). An extended 50-feature set augmented this with 20 additional features drawn from modern EEG literature: discrete wavelet transform (db4, 5-level) sub-band energies, sample entropy and permutation entropy, the aperiodic 1/f slope, peak alpha frequency difference, and coherence in the theta, alpha, and beta bands. The final lean set retained only the 10 features that drove the headline result (Section 4.7 ablation).")
    add_subsection(doc, "4.5.1", "Baseline Per-Channel Features")
    add_para(doc, "For each channel (O1, O2) and each epoch, Welch's method (2-s segments, 50% overlap, Hann window) estimated the PSD. Band power was integrated trapezoidally over the delta (0.5–4 Hz), theta (4–8 Hz), alpha (8–13 Hz), and beta (13–30 Hz) bands. Two band ratios — theta/alpha and (theta+alpha)/(alpha+beta) — were computed as drowsiness-sensitive biomarkers. Spectral entropy H_spec = −Σ p_i log p_i, with p_i the normalised PSD bin, quantified the irregularity of the frequency distribution. Hjorth activity, mobility, and complexity captured time-domain signal complexity. Zero-crossing rate and skewness completed the 15-feature per-channel vector.")
    add_subsection(doc, "4.5.2", "Extended Per-Channel Features")
    add_para(doc, "Five additional per-channel features captured non-spectral structure. Discrete wavelet energies E_k = Σ |c_k[n]|² (k = 0..4) over the db4 5-level decomposition (sub-bands A5, D5, D4, D3, D2) provided time-frequency localisation complementary to Welch. Sample entropy SampEn(m=2, r=0.2·σ) and permutation entropy PermEn(order=3) quantified signal irregularity in a scale-free manner. The aperiodic 1/f slope was fit by linear regression of log_{10}(PSD) against log_{10}(f) over 2–40 Hz; physiologically, flattening of this slope (less negative values) has been linked to reduced cortical arousal.")
    add_subsection(doc, "4.5.3", "Cross-Channel Features")
    add_para(doc, "Four cross-channel features captured O1↔O2 interaction, which is physiologically meaningful at the occipital pole because of the tight inter-hemispheric coupling of visual/alpha rhythms. Peak alpha frequency (PAF) was the argmax of PSD within 8–13 Hz, and its |PAF_O1 − PAF_O2| difference was included. Magnitude-squared coherence C_xy(f) = |P_xy(f)|² / (P_xx(f)·P_yy(f)) was averaged within the theta, alpha, and beta bands to produce three coherence features.")

    add_table(doc,
        ["Tier", "Count", "Contents"],
        [
            ["Baseline (v3 / v5)", "30",
             "Per-channel: band powers (δ, θ, α, β); band ratios (θ/α, slow/fast); spectral entropy; Hjorth activity/mobility/complexity; zero-crossing rate; skewness. Cross-channel: band asymmetries; total θ/α; mean θ/α ratio."],
            ["Extended (v9)", "50",
             "Baseline + per-channel DWT sub-band energies (5); per-channel sample entropy and permutation entropy (2); per-channel 1/f slope (1); cross-channel PAF Δ (1); cross-channel θ/α/β coherence (3)."],
            ["Lean (v11, headline)", "10",
             "Only the extended families that carried non-redundant information: per-channel sample entropy (2), permutation entropy (2), 1/f slope (2); cross-channel PAF Δ (1); cross-channel θ/α/β coherence (3)."],
        ],
        "4.2", "Feature Tiers Evaluated in this Work")

    add_figure(doc, EXISTING_FIGS.get("ml_flow", ""), "Feature extraction and classification pipeline (10-s epoch → Welch/DWT/coherence → per-subject z-score → LDA).", "4.6", 4.5)

    # ── 4.6 ML Classification ─────────────────────────────────────────────────
    add_section(doc, "4.6", "Classification and Evaluation Protocol")
    add_para(doc, "Linear Discriminant Analysis (LDA) with automatic Ledoit–Wolf shrinkage (solver=lsqr, shrinkage='auto') was the primary classifier for the feature-based pipelines. Shrinkage LDA was selected for three reasons: (i) it is statistically consistent even when the sample count is comparable to the feature count, (ii) its analytic closed-form fit avoids the instability of stochastic optimisers on the small DROZY dataset, and (iii) it produced the highest per-subject F1 across all the classifiers surveyed (including Logistic Regression, SVM, Gradient Boosting, Random Forest, and a Riemannian tangent-space + LDA baseline). A class-balanced Logistic Regression and a Riemannian tangent-space + LDA variant are retained as reported comparators in Chapter 5.")
    add_para(doc, "Per-subject z-score normalisation was applied before classification using the subject's own session-1 (awake) epochs as the calibration sample. Formally, for each subject s and feature column j the normalised feature was x̃_{s,j} = (x_{s,j} − μ_{s,j}) / σ_{s,j}, where μ_{s,j} and σ_{s,j} were the mean and standard deviation computed over subject s's awake epochs only. This 'subject_awake' scheme was preferred over a global scaler because individual resting-EEG amplitudes vary by an order of magnitude across subjects, and over a 'subject_both' scheme (using both awake and drowsy epochs) because the latter subtly leaks drowsy-class statistics into the feature standardisation. A calibration-window variant, where only the first 60 seconds of session-1 EEG defined μ and σ, was additionally evaluated (Chapter 5, Section 5.2.4) because it is the setting realistically available at deployment.")
    add_para(doc, "Evaluation used a strict Leave-One-Subject-Out (LOSO) cross-validation. In each of 10 outer folds, one subject's 1,400–1,500 epochs were withheld as the test set and the remaining 9 subjects formed the training set. Per-subject z-score statistics were computed within the training fold only. Reported overall metrics (accuracy, weighted F1, AUC-ROC, Cohen's κ) were computed by concatenating the 10 held-out prediction arrays. Per-subject metrics were computed on each fold's test set and summarised with their mean and 95% confidence interval (t-distribution) in Chapter 5.")
    add_para(doc, "The weighted F1 score was chosen as the primary selection metric because the two classes were approximately balanced (50/50) but not exactly so, and weighted-F1 accounts for minor imbalances while penalising single-class predictions. Cohen's κ was reported alongside as a leakage-sanity check: because it is zero for any constant predictor, κ ≥ 0.20 under LOSO is a minimum bar for non-trivial subject-generalisation.")

    # ── 4.7 Feature-Family Ablation and Baseline Comparators ───────────────────
    add_section(doc, "4.7", "Feature-Family Ablation and Baseline Comparators")
    add_para(doc, "A feature-family ablation was conducted to identify which of the extended families in the 50-feature set contributed non-redundant information and to derive the lean 10-feature pipeline used in the headline result. Nine feature sub-sets were evaluated with the same LDA classifier and LOSO protocol: ALL (50), BASE only (30), DROP-DWT (40), DROP-ENT (46), DROP-SLOPE (48), DROP-COH (46), ONLY-DWT (10), ONLY-ENT+SLOPE+COH (10), and NEW-FAMILIES (20 = extended minus BASE). Family sizes are indicated in parentheses. The cached feature matrix (shape 14,498 × 50, stored as features_v9_cache.npz) was re-used so that no feature extraction was re-run. The ablation findings are reported quantitatively in Chapter 5, Section 5.3, and motivate the final lean 10-feature choice.")
    add_para(doc, "Three comparator baselines beyond the feature-LDA family were trained under the same LOSO protocol to contextualise the headline number:")
    add_para(doc, "(a) Riemannian tangent-space classifier. A spatial covariance matrix C = X·Xᵀ/N was estimated per epoch from the 2-channel signal using the OAS shrinkage estimator. The 2×2 SPD covariance was projected to the tangent space of the symmetric-positive-definite manifold via the logarithmic map log_{Ĉ}(C) = Ĉ^{1/2}·logm(Ĉ^{-1/2}·C·Ĉ^{-1/2})·Ĉ^{1/2}, where Ĉ was the geometric (Fréchet) mean of the training-fold covariances. The resulting 3-dimensional tangent-space vector was classified by LDA or Logistic Regression. A nested-CV variant used outer LOSO with an inner GroupKFold(3) to tune the shrinkage coefficient.")
    add_para(doc, "(b) EEGNet (Lawhern et al., 2018). The raw 10-s window (2 × 1,280 float32) was fed directly to an EEGNet-style 2D-CNN with parameters F1=8, D=2, F2=16, kernel sizes (1,32) and (1,16), dropout 0.5, Adam optimiser at lr=10⁻³, batch size 64, 15 training epochs per fold. The spatial depthwise convolution (height 2, corresponding to the two EEG channels) is EEGNet's signature operation, and the comparison tested whether an end-to-end learned representation could outperform the lean handcrafted features at the 2-channel scale.")
    add_para(doc, "(c) Calibration-window sweep. A feature-LDA variant where the per-subject μ, σ were fit on only the first T seconds of the subject's session-1 EEG, for T ∈ {30, 60, 120, 180, 300}. This addressed the realistic deployment question of how much awake EEG the system must see before producing reliable predictions.")

    # ── 4.8 Cross-Dataset Validation Protocol ────────────────────────────────
    add_section(doc, "4.8", "Cross-Dataset Validation Protocol")
    add_para(doc, "To test whether the lean pipeline generalises beyond the DROZY cohort, two cross-dataset evaluations were run on SEED-VIG (Section 4.2.2):")
    add_para(doc, "(i) DROZY → SEED-VIG transfer. The lean 10-feature LDA was trained on the full DROZY dataset (all 10 subjects, 14,498 epochs) and evaluated on SEED-VIG (9,155 labelled epochs from 21 subjects). Per-SEED-VIG-subject z-score used the first 60 seconds of the SEED-VIG session as the awake calibration sample — the realistic deployment analogue of the DROZY session-1 calibration.")
    add_para(doc, "(ii) SEED-VIG-internal LOSO. A standalone LOSO evaluation was run on SEED-VIG using the identical lean feature pipeline, to provide a reference point for the transfer number and to assess the dataset's internal difficulty.")

    # ── 4.9 Proactive Prediction Protocol ────────────────────────────────────
    add_section(doc, "4.9", "Proactive (Advance) Prediction Protocol")
    add_para(doc, "The proactive prediction claim — that the system signals drowsiness before it manifests behaviourally — was evaluated on SEED-VIG under LOSO, taking advantage of that dataset's continuous PERCLOS timeline. For each subject, the lean LDA's posterior probability p(drowsy | epoch_t) was smoothed causally with a 30-second moving average (to avoid future-sample leakage) and the EEG onset time t_EEG was defined as the earliest epoch for which the smoothed probability remained above 0.5 for 30 consecutive seconds. The behavioural onset time t_behav was defined analogously: PERCLOS was causally smoothed over 30 seconds and t_behav was the earliest time at which the smoothed PERCLOS remained above 0.70 for 60 consecutive seconds. The per-subject lead time was Δt = t_behav − t_EEG (positive values indicate the EEG preceded the behaviour).")
    add_para(doc, "Rather than reporting the overall mean — which is sensitive to single-subject outliers and can mask high variance — the headline metrics were (a) the number of subjects with both onsets detectable, (b) the fraction of those subjects for which Δt > 0, (c) the median Δt, and (d) the inter-quartile range of Δt. This reporting scheme is consistent with the broader trend toward effect-size rather than point-estimate reporting in biomedical machine learning.")
    add_para(doc, "No separate alert tier (yellow/red/critical) was evaluated on DROZY because DROZY's binary session labels do not provide continuous drowsiness dynamics. Chapter 6 discusses how the alert tiers would be calibrated in a production deployment on top of the lean LDA posterior.")
