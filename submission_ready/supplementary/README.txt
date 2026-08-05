================================================================================
README -- SUPPLEMENTARY MATERIALS
================================================================================

Manuscript : Inter-Hemispheric Occipital Coherence for Subject-Independent
             Driver Drowsiness Monitoring and Advance Prediction
Authors    : M. R. Thalassery, S. S. Ali, A. R. Pal, A. Chemori,
             G. Murali Mohan
Journal    : IEEE Sensors Journal
Contact    : Dr. Abhishek Rudra Pal (corresponding author)
             School of Mechanical Engineering (SMEC),
             Vellore Institute of Technology (VIT) Chennai,
             Vandalur-Kelambakkam Road, Chennai 600127, Tamil Nadu, India
             abhishek.rudrapal@vit.ac.in


1. CONTENTS AND TOTAL SIZE
--------------------------------------------------------------------------------

Two supplementary items accompany this manuscript.

  (a) demo_v20.gif                          approx. 6.9 MB
      Animated playback of the pro-active algorithm running on the
      median-lead SEED-VIG subject. Referenced in the manuscript where the
      live-system demonstrator is discussed. Plays in any browser or image
      viewer; no software required.

  (b) supplementary_code_and_results.zip    approx. 0.8 MB compressed
      Complete analysis code and the archived numerical results behind
      every headline number in the paper. Uncompressed contents:

          reproduce.py            single-entry reproducer          8 KB
          requirements.txt        pinned Python dependencies       4 KB
          README.txt              this file                        8 KB
          scripts/                22 analysis scripts            340 KB
          results/                14 JSON result files           408 KB

Total supplementary payload: approximately 7.7 MB.

No raw EEG data is redistributed here. Both datasets used in this work are
third-party releases governed by their own data-use agreements (see §5).


2. PLATFORM AND ENVIRONMENT
--------------------------------------------------------------------------------

Language      Python 3.12 (3.10 and 3.11 also verified)
OS            Platform independent; developed and measured on Windows 11,
              also run on Ubuntu 22.04
Hardware      CPU only. No GPU and no CUDA dependency; the EEGNet baseline
              uses the PyTorch CPU wheel.
Reference     Intel Core i5-1240P @ 1.7 GHz, 12 logical cores, 16 GB RAM.
machine       All timings quoted below were measured on this machine.
Dependencies  numpy, scipy, scikit-learn, mne, matplotlib, torch (CPU),
              pyriemann. Exact pinned versions are in requirements.txt.
Disk          Approximately 2 GB free is needed for the intermediate
              feature caches that the reproducer writes.


3. SETUP
--------------------------------------------------------------------------------

Step 1 -- install the pinned dependencies:

    pip install -r requirements.txt

Step 2 -- obtain the two source datasets. Neither is redistributed in this
archive, consistent with their respective use agreements. Both are publicly
available from the originating institutions:

    DROZY     Universite de Liege. Massoz et al., IEEE WACV 2016.
              Access requires acceptance of the ULg licence.
    SEED-VIG  Shanghai Jiao Tong University, BCMI Lab.
              Zheng and Lu, J. Neural Eng. 2017.
              Access requires application to BCMI Lab.

Step 3 -- place the raw files in the layout the reproducer expects, in the
working directory from which you run it:

    DROZY_O1_O2/        extracted occipital EDF files from DROZY
    Raw_Data/           SEED-VIG raw .mat files
    perclos_labels/     SEED-VIG PERCLOS annotation .mat files

The helper script scripts/extract_O1_O2_channels.py produces DROZY_O1_O2/
from a full DROZY download.


4. HOW TO RUN, AND WHAT TO EXPECT
--------------------------------------------------------------------------------

    python reproduce.py --list        show the 17-step plan without running
    python reproduce.py               run every step
    python reproduce.py --only v17    run one named step

The reproducer is idempotent: any step whose output JSON, cache or figure
already exists is skipped, so an interrupted run can simply be restarted.

Expected output. Each step writes a publication_results_v*.json file into
the working directory and prints a one-line summary of the metrics it
computed. On completion the JSON files reproduce the archived copies in
results/ to within floating-point tolerance. The figures are regenerated
into publication_figures_v5/.

Expected wall-clock time on the reference machine:

    Feature extraction, DROZY 50-feature                      approx.  80 s
    Feature extraction, SEED-VIG 10-feature                   approx.  25 s
    All LOSO LDA variants combined                            approx.  30 s
    Riemannian covariance and tangent space                   approx.   3 min
    Phase-coherence extraction (PLV / ImCoh / wPLI)           approx. 140 s
    Advance-prediction grid sweep (v20)                       approx.  90 s
    EEGNet 10-fold LOSO baseline                              approx.  28 min
    -------------------------------------------------------------------
    Total excluding the EEGNet baseline                       approx.   5 min
    Total including the EEGNet baseline                       approx.  35 min

Step-to-script mapping used by reproduce.py, in dependency order:

    v3/v4/v5   publication_analysis.py        baselines, LDA z-score variants
    v6         riemannian_analysis.py         Riemannian TS, untuned
    v7         nested_cv_analysis.py          Riemannian TS, nested-CV tuned
    v8         calibration_analysis.py        calibration-window sweep
    v9         extended_features.py           50-feature extended LDA
    v11        ablation_analysis.py           feature-family ablation
    v12        seed_vig_validation.py         DROZY to SEED-VIG transfer
    v13        advance_prediction.py          uncontrolled lead-time evaluation
    v14        eegnet_baseline.py             EEGNet deep baseline
    v15        personal_calibration.py        per-driver calibration sweep
    v16        pooled_loso.py                 pooled 31-subject LOSO
    v17        hmm_smoothing.py               causal EMA and HMM smoothing
    v18        extended_coherence.py          phase-coherence negative ablation
    v19        ensemble_analysis.py           ensemble negative ablation
    v20        advance_prediction_v20.py      FPR-controlled advance prediction
    v21        reviewer_revision_analysis.py  coherence stats, per-subject CIs
    ROC        v17_roc.py                     monitoring ROC, operating points
    stats      v17_v20_stats.py               paired Wilcoxon, Cohen's d
    severity   v20_lead_vs_severity.py        lead time vs PERCLOS severity
    demo       live_demo_figure.py            live-demo figure and animation
    runtime    runtime_benchmark.py           56 ms per 10-second epoch claim
    figures    make_figures.py                all manuscript figures


5. WHICH RESULT FILE BACKS WHICH CLAIM
--------------------------------------------------------------------------------

A reviewer who wants to check a number without re-running anything can read
the corresponding JSON in results/ directly.

    Monitoring headline, F1 = 76.79        publication_results_v17.json
    ROC and operating points               publication_results_v17_roc.json
    Awake vs drowsy coherence statistics   publication_results_v21_reviewer.json
                                             (key: item1_coherence)
    Per-subject F1 / AUC / kappa and CIs   publication_results_v21_reviewer.json
                                             (key: item2_subjectwise)
    EMA smoothing latency                  publication_results_v21_reviewer.json
                                             (key: item3_latency)
    Feature-family ablation                publication_results_v11.json
    Paired Wilcoxon and Cohen's d          publication_results_v10b.json
    Cross-dataset transfer                 publication_results_v12.json
    Pooled 31-subject LOSO                 publication_results_v16.json
    Advance-prediction Pareto front        publication_results_v20.json
    Lead time vs PERCLOS severity          publication_results_v20_severity.json
    Phase-coherence negative ablation      publication_results_v18.json
    Ensemble negative ablation             publication_results_v19.json
    Per-driver calibration sweep           publication_results_v15.json
    Runtime, 56 ms per 10-second epoch     runtime_benchmark.json


6. LICENCE AND PUBLIC ARCHIVE
--------------------------------------------------------------------------------

The same code and results, together with the manuscript source, are released
publicly at:

    https://github.com/MuhammedRaslan/Pro-Active-Driver-Monitoring-System-Using-EEG

at the commit tagged paper-submission-v1. A Zenodo DOI is minted from that
release and added to the Reproducibility section of the manuscript.

Questions about this material should be directed to the corresponding
author at the address given at the top of this file.

================================================================================
