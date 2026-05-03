"""
reproduce.py
============
Single-entry reproducer for the IEEE Sensors submission.

Runs every analysis script that produced a `publication_results_v*.json`
referenced in the paper, in dependency order, then regenerates the
publication figures. Each step is skipped if its output file already
exists, so re-runs are cheap and you can stop/resume.

Usage
-----
    python reproduce.py              # run everything that's missing
    python reproduce.py --force      # re-run every step, overwriting outputs
    python reproduce.py --only v11   # run only the named version
    python reproduce.py --list       # list the planned steps and exit

Wall-clock budget on a laptop CPU (no GPU): ~1.5 hr if EEGNet (v14) is
included, ~5 min otherwise. EEGNet dominates because it is the only
deep-learning baseline; everything else is feature-extraction + LDA.

Pre-requisites
--------------
1. `pip install -r requirements.txt` (and the torch CPU wheel — see the
   comment block in requirements.txt).
2. The DROZY EDF files extracted to `DROZY_O1_O2/` (run
   `extract_O1_O2_channels.py` once if you only have the raw EDFs).
3. SEED-VIG `Raw_Data/` and `perclos_labels/` directories at the
   repository root (only needed for v12 / v13 / SEED-VIG figures).
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))


def _exists(*names: str) -> bool:
    return all(os.path.exists(os.path.join(ROOT, n)) for n in names)


# (label, script, list-of-output-files-that-mark-success)
STEPS: list[tuple[str, str, list[str]]] = [
    ("v3 / v4 / v5  baselines (GB, RF, LDA z-score variants)",
     "publication_analysis.py",
     ["publication_results_v3.json",
      "publication_results_v4.json",
      "publication_results_v5.json"]),

    ("v6  Riemannian tangent-space (untuned)",
     "riemannian_analysis.py",
     ["publication_results_v6.json"]),

    ("v7  Riemannian tangent-space (nested-CV tuned)",
     "nested_cv_analysis.py",
     ["publication_results_v7.json"]),

    ("v8  Calibration-window sweep (30/60/120/180/300 s)",
     "calibration_analysis.py",
     ["publication_results_v8.json"]),

    ("v9  Extended 50-feature LDA (DWT + ENT + SLOPE + COH + PAF)",
     "extended_features.py",
     ["publication_results_v9.json", "features_v9_cache.npz"]),

    ("v11 Feature-family ablation (PAPER HEADLINE — produces lean set)",
     "ablation_analysis.py",
     ["publication_results_v11.json"]),

    ("v12 SEED-VIG cross-dataset transfer + internal LOSO",
     "seed_vig_validation.py",
     ["publication_results_v12.json", "features_seed_vig_cache.npz"]),

    ("v13 Advance-prediction lead-time analysis on SEED-VIG",
     "advance_prediction.py",
     ["publication_results_v13.json"]),

    ("v14 EEGNet (Lawhern 2018) deep-learning baseline  [SLOW: ~28 min]",
     "eegnet_baseline.py",
     ["publication_results_v14.json", "epochs_raw_cache.npz"]),

    ("v15 Per-driver calibration sweep (cold-start vs personal LDA)",
     "personal_calibration.py",
     ["publication_results_v15.json"]),

    ("v16 Pooled DROZY+SEED-VIG 31-subject LOSO",
     "pooled_loso.py",
     ["publication_results_v16.json"]),

    ("v17 Causal posterior smoothing (EMA + HMM, deployment headline)",
     "hmm_smoothing.py",
     ["publication_results_v17.json"]),

    ("v18 Extended phase coherence (PLV / ImCoh / wPLI) — negative ablation",
     "extended_coherence.py",
     ["publication_results_v18.json", "features_phase_coh_cache.npz"]),

    ("v19 Posterior ensemble (lean + Riemannian + EMA) — negative result",
     "ensemble_analysis.py",
     ["publication_results_v19.json"]),

    ("v20 Advance-prediction v2 (FPR-controlled, per-subject calibrated, survival-framed)",
     "advance_prediction_v20.py",
     ["publication_results_v20.json"]),

    ("v10 Statistical-rigor harvest (paired Wilcoxon, Cohen's d)",
     "stat_analysis.py",
     ["publication_results_v10.json"]),

    ("Runtime benchmark (CPU ms/epoch for full feature set)",
     "runtime_benchmark.py",
     ["runtime_benchmark.json"]),

    ("Publication figures (writes to publication_figures_v5/)",
     "make_figures.py",
     [os.path.join("publication_figures_v5", "fig1_pipeline_progression.png")]),
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true",
                    help="Re-run every step even if its outputs exist.")
    ap.add_argument("--only", action="append", default=[],
                    help='Run only steps whose label contains this substring '
                         '(e.g. "v11", "EEGNet"). May be passed multiple times.')
    ap.add_argument("--list", action="store_true",
                    help="List the steps and their output files, then exit.")
    return ap.parse_args()


def matches(label: str, only: list[str]) -> bool:
    if not only:
        return True
    return any(needle.lower() in label.lower() for needle in only)


def run_step(script: str, label: str) -> tuple[bool, float]:
    print("─" * 78)
    print(f"  RUNNING: {label}")
    print(f"  $ python {script}")
    print("─" * 78, flush=True)
    t0 = time.time()
    rc = subprocess.call([sys.executable, os.path.join(ROOT, script)], cwd=ROOT)
    return rc == 0, time.time() - t0


def main() -> int:
    args = parse_args()

    if args.list:
        print("Reproducer plan (run order top → bottom):")
        for i, (label, script, outs) in enumerate(STEPS, 1):
            print(f"  {i:2d}. {label}")
            print(f"      script:  {script}")
            print(f"      outputs: {', '.join(outs)}")
        return 0

    skipped, ran, failed = [], [], []
    total_t = 0.0

    for label, script, outs in STEPS:
        if not matches(label, args.only):
            continue
        if not args.force and _exists(*outs):
            print(f"  ✔ already done — skipping: {label}")
            skipped.append(label)
            continue
        ok, dt = run_step(script, label)
        total_t += dt
        if ok:
            ran.append((label, dt))
            print(f"  ✔ done in {dt:.1f}s\n", flush=True)
        else:
            failed.append(label)
            print(f"  ✘ FAILED ({dt:.1f}s) — aborting reproducer.", flush=True)
            break

    print()
    print("=" * 78)
    print(f"  Summary:  {len(ran)} ran  |  {len(skipped)} skipped  |  {len(failed)} failed")
    print(f"  Wall clock for new work: {total_t:.1f}s")
    print("=" * 78)
    if ran:
        print("  Steps run:")
        for label, dt in ran:
            print(f"    - {label}  ({dt:.1f}s)")
    if failed:
        print("  Steps failed:")
        for label in failed:
            print(f"    - {label}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
