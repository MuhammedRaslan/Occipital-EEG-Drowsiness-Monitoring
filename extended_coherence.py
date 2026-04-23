"""
Extended Phase-Coherence Features (Phase 7c, v18)
=================================================
The v11 lean set already includes magnitude-squared coherence (`coh_theta`,
`coh_alpha`, `coh_beta`) between O1 and O2. Magnitude coherence mixes true
phase synchronisation with volume-conduction artefacts (instantaneous
zero-lag coupling that survives a common reference). This script adds three
phase-only coherence variants in each band:

  * Phase Locking Value (PLV) — magnitude of mean phase difference.
  * Imaginary part of coherency (ImCoh) — discards zero-lag coupling.
  * Weighted Phase Lag Index (wPLI) — robust against amplitude bias and
    insensitive to volume conduction.

That gives 3 metrics × 3 bands = 9 new features. Combined with the v11
lean set we get 19 features. Strict subject-out LOSO LDA is run on the
combined 19-feature matrix and compared to the v11 baseline (F1=62.08).

Output: publication_results_v18.json
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
from datetime import datetime
from scipy.signal import hilbert, butter, filtfilt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, cohen_kappa_score,
    precision_score, recall_score,
)

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RAW_CACHE    = os.path.join(_SCRIPT_DIR, "epochs_raw_cache.npz")
LEAN_CACHE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
PHASE_CACHE  = os.path.join(_SCRIPT_DIR, "features_phase_coh_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v18.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
FS = 128
BANDS = {
    "theta": (4.0,  8.0),
    "alpha": (8.0, 13.0),
    "beta":  (13.0, 30.0),
}


def load_lean():
    z = np.load(LEAN_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    return (z["X"][:, ix].astype(float),
            z["y"].astype(int),
            np.asarray(z["subjects"]))


def bandpass(x, lo, hi, fs=FS, order=4):
    """Zero-phase Butterworth bandpass on a 1D signal."""
    b, a = butter(order, [lo / (fs * 0.5), hi / (fs * 0.5)], btype="band")
    return filtfilt(b, a, x)


def epoch_phase_features(epoch_O1, epoch_O2):
    """Compute PLV, ImCoh, wPLI for one epoch in each band → 9 features.

    Both signals are bandpass-filtered, then the analytic signal is taken
    via Hilbert transform. Phase difference Δφ(t) = φ_O1(t) − φ_O2(t).

      PLV    = | mean_t exp(i Δφ) |
      ImCoh  = | imag(mean_t S12(t) / sqrt(mean S11 · mean S22)) |
                where S_xy = a_x · conj(a_y), with a = analytic signal
      wPLI   = | mean_t imag(S12) | / mean_t | imag(S12) |
    """
    feats = []
    for lo, hi in BANDS.values():
        x1 = bandpass(epoch_O1, lo, hi)
        x2 = bandpass(epoch_O2, lo, hi)
        a1 = hilbert(x1)
        a2 = hilbert(x2)
        # PLV: mean phase difference magnitude
        dphi = np.angle(a1) - np.angle(a2)
        plv = np.abs(np.mean(np.exp(1j * dphi)))
        # Cross-spectrum (sample-wise)
        s12 = a1 * np.conj(a2)
        s11 = a1 * np.conj(a1)
        s22 = a2 * np.conj(a2)
        denom = np.sqrt(np.mean(s11).real * np.mean(s22).real) + 1e-12
        imcoh = np.abs(np.mean(s12).imag / denom)
        # wPLI: weighted phase-lag index
        imag_s12 = s12.imag
        denom2 = np.mean(np.abs(imag_s12)) + 1e-12
        wpli = np.abs(np.mean(imag_s12)) / denom2
        feats.extend([plv, imcoh, wpli])
    return np.asarray(feats, dtype=float)


def compute_or_load_phase_features():
    """Cache the 9 phase features. Skip recompute if cache exists & matches."""
    if os.path.exists(PHASE_CACHE):
        z = np.load(PHASE_CACHE, allow_pickle=True)
        Xp = z["X"].astype(float)
        if Xp.shape == (14498, 9):
            print(f"  ✔ loaded cached phase features: {PHASE_CACHE}")
            return Xp
        print("  cache shape mismatch — recomputing")
    print("  computing phase features (PLV/ImCoh/wPLI × 3 bands) for 14498 epochs...")
    z = np.load(RAW_CACHE, allow_pickle=True)
    raw = z["X"].astype(np.float32)   # (n, 2, 1280)
    n = raw.shape[0]
    Xp = np.empty((n, 9), dtype=float)
    t0 = time.time()
    for i in range(n):
        Xp[i] = epoch_phase_features(raw[i, 0], raw[i, 1])
        if (i + 1) % 2000 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n - i - 1)
            print(f"    {i+1:5d}/{n}  elapsed={elapsed:5.1f}s  eta={eta:5.1f}s")
    np.savez_compressed(PHASE_CACHE, X=Xp,
                        feat_names=np.array([f"{m}_{b}" for b in BANDS for m in ("plv","imcoh","wpli")]))
    print(f"  cached → {PHASE_CACHE}  ({time.time()-t0:.1f}s total)")
    return Xp


def per_subject_zscore(X, y, subj):
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        awake = m & (y == 0)
        mu = X[awake].mean(axis=0); sd = X[awake].std(axis=0) + 1e-8
        Xz[m] = (X[m] - mu) / sd
    return Xz


def metrics_(y_true, y_pred, y_score=None):
    out = {
        "accuracy":  round(accuracy_score(y_true, y_pred) * 100, 2),
        "f1_score":  round(f1_score(y_true, y_pred, average="weighted") * 100, 2),
        "precision": round(precision_score(y_true, y_pred, average="weighted", zero_division=0) * 100, 2),
        "recall":    round(recall_score(y_true, y_pred, average="weighted", zero_division=0) * 100, 2),
        "kappa":     round(cohen_kappa_score(y_true, y_pred), 4),
    }
    if y_score is not None:
        try:
            out["auc_roc"] = round(roc_auc_score(y_true, y_score) * 100, 2)
        except ValueError:
            out["auc_roc"] = None
    return out


def loso(X, y, subj, label=""):
    """Strict subject-out LOSO with shrinkage LDA. Returns (concat, per_subject)."""
    Xz = per_subject_zscore(X, y, subj)
    y_true_all, y_pred_all, y_score_all = [], [], []
    per_subj = []
    for held in np.unique(subj):
        train = subj != held
        test  = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[train], y[train])
        sc = clf.decision_function(Xz[test])
        pr = clf.predict(Xz[test])
        m = metrics_(y[test], pr, sc)
        m["held_out"] = str(held)
        m["n_test"] = int(test.sum())
        per_subj.append(m)
        y_true_all.append(y[test])
        y_pred_all.append(pr)
        y_score_all.append(sc)
    y_true_all  = np.concatenate(y_true_all)
    y_pred_all  = np.concatenate(y_pred_all)
    y_score_all = np.concatenate(y_score_all)
    overall_concat = metrics_(y_true_all, y_pred_all, y_score_all)
    f1s = np.array([m["f1_score"] for m in per_subj], dtype=float)
    overall_mean = {
        "f1_score_mean": round(float(np.mean(f1s)), 2),
        "f1_score_std":  round(float(np.std (f1s)), 2),
    }
    print(f"  [{label:>16}]  concat F1={overall_concat['f1_score']:5.2f}  "
          f"AUC={overall_concat['auc_roc']:5.2f}  κ={overall_concat['kappa']:+.3f}  "
          f"meanF1={overall_mean['f1_score_mean']:5.2f}±{overall_mean['f1_score_std']:.2f}")
    return overall_concat, overall_mean, per_subj


def main():
    print(f"Timestamp: {datetime.now()}")
    X_lean, y, subj = load_lean()
    print(f"  lean X={X_lean.shape}  y_balance={np.bincount(y).tolist()}  subjects={len(np.unique(subj))}")
    Xp = compute_or_load_phase_features()
    print(f"  phase X={Xp.shape}")
    assert len(Xp) == len(X_lean), "epoch count mismatch"

    # Sanity: verify v11 lean baseline reproduces ~F1=62
    print()
    print("Baseline check (v11 lean LOSO):")
    base_concat, base_mean, base_per = loso(X_lean, y, subj, "lean (v11)")

    # Phase features alone
    print()
    print("Phase coherence features only (PLV/ImCoh/wPLI × 3 bands):")
    phase_concat, phase_mean, phase_per = loso(Xp, y, subj, "phase only")

    # Combined: lean + phase = 19 features
    print()
    print("Combined v11 lean ∪ phase coherence = 19 features:")
    Xc = np.hstack([X_lean, Xp])
    comb_concat, comb_mean, comb_per = loso(Xc, y, subj, "lean+phase")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Adds three phase-only coherence variants per band on top of the v11 "
            "lean 10-feature set: PLV (Lachaux 1999), imaginary coherence (Nolte "
            "2004), and wPLI (Vinck 2011), each computed in theta/alpha/beta "
            "bands from O1–O2. Phase variants are computed from the bandpass + "
            "Hilbert analytic signal of each epoch. LOSO LDA with subject_awake "
            "z-score, exactly matching the v11 protocol."
        ),
        "feature_set_lean": LEAN_NAMES,
        "feature_set_phase": [f"{m}_{b}" for b in BANDS for m in ("plv","imcoh","wpli")],
        "n_features_combined": 19,
        "lean_baseline":     {"concat": base_concat,  "mean": base_mean,  "per_subject": base_per},
        "phase_only":        {"concat": phase_concat, "mean": phase_mean, "per_subject": phase_per},
        "combined_19feat":   {"concat": comb_concat,  "mean": comb_mean,  "per_subject": comb_per},
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
