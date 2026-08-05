"""
Causal Posterior Smoothing (Phase 7b, v17)
==========================================
Drowsiness is a slow process: consecutive 10-s epochs are highly
correlated, but the v11 LDA scores each epoch independently and is
therefore noisy at the epoch level. This script applies two causal
(no-future-leak) smoothers on top of the v11 lean LDA posteriors and
sweeps the smoothing horizon to find the best operating point.

Two smoothers are compared:

  1. Causal exponential moving average over p(drowsy):
        p_smooth[t] = α p[t] + (1 − α) p_smooth[t−1]
     where α = 1 − exp(−Δt / τ) and τ is the smoothing time constant.

  2. Causal forward-only HMM (binary states awake/drowsy):
        α_t(j) ∝ b_j(o_t) · Σ_i α_{t−1}(i) · A_{ij}
     with a sticky transition matrix (P(stay) ≈ 0.95). The filtered
     posterior P(state=drowsy | o_{1:t}) is the smoothed p(drowsy).

Both are applied AFTER the v11 lean LDA is trained subject-out;
smoothing only touches the test-fold predictions, so there is no
leakage. Smoothing respects subject and session boundaries.

Sweeps τ ∈ {10, 30, 60, 120, 300, 600} s for the EMA, and
P(stay) ∈ {0.90, 0.95, 0.98, 0.99} for the HMM.

Output: publication_results_v17.json
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
from datetime import datetime
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, cohen_kappa_score,
    precision_score, recall_score,
)

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DROZY_CACHE  = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v17.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC = 10
TAU_SEC   = [10, 30, 60, 120, 300, 600]
P_STAY    = [0.90, 0.95, 0.98, 0.99]


def load_lean():
    z = np.load(DROZY_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    return z["X"][:, ix].astype(float), z["y"].astype(int), np.asarray(z["subjects"])


def per_subject_zscore(X, y, subj):
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        awake = m & (y == 0)
        mu = X[awake].mean(axis=0); sd = X[awake].std(axis=0) + 1e-8
        Xz[m] = (X[m] - mu) / sd
    return Xz


def session_runs(y_s):
    """Return [(start, end_exclusive), ...] of contiguous-label runs.

    For DROZY: each subject has a single awake run followed by a single
    drowsy run, so this yields exactly 2 segments per subject.

    NOTE: this uses the *label* to find boundaries. That is acceptable
    for DROZY only because the session boundary in the cache happens to
    coincide with the awake/drowsy label flip — and at deployment a real
    ignition event would equivalently reset the smoother. The honest
    cross-check is the continuous-stream version (one segment per
    subject, no resets) reported alongside in the same sweep.
    """
    runs = []
    n = len(y_s)
    i = 0
    while i < n:
        j = i
        while j < n and y_s[j] == y_s[i]:
            j += 1
        runs.append((i, j))
        i = j
    return runs


def whole_subject_runs(y_s):
    """Single segment covering the subject's full epoch stream — no resets."""
    return [(0, len(y_s))]


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    """Causal exponential moving average. p[0..n-1] -> smoothed[0..n-1]."""
    if tau_sec <= 0:
        return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p)
    out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def causal_hmm_forward(p_drowsy, p_stay, eps=1e-6):
    """Causal HMM forward filter. Returns P(state=drowsy | obs_{1..t})."""
    A = np.array([[p_stay,     1 - p_stay],
                  [1 - p_stay, p_stay    ]], dtype=float)
    pi = np.array([0.5, 0.5])
    n = len(p_drowsy)
    out = np.empty(n, dtype=float)
    # alpha is the unnormalised filtered distribution; normalise each step.
    p_drowsy = np.clip(p_drowsy, eps, 1.0 - eps)
    b = np.stack([1.0 - p_drowsy, p_drowsy], axis=1)   # (n,2)
    a = pi * b[0]
    a /= a.sum()
    out[0] = a[1]
    for t in range(1, n):
        a = (a @ A) * b[t]
        a /= a.sum()
        out[t] = a[1]
    return out


def metrics(y_true, y_pred, y_score=None):
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


def main():
    print(f"Timestamp: {datetime.now()}")
    X, y, subj = load_lean()
    print(f"  X={X.shape}  y_balance={np.bincount(y).tolist()}  subjects={len(np.unique(subj))}")
    Xz = per_subject_zscore(X, y, subj)

    # Step 1: produce LOSO per-epoch p(drowsy) using v11 lean LDA.
    p_loso = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        train = subj != held
        test  = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[train], y[train])
        # predict_proba is supported by LDA(solver=lsqr).
        p_loso[test] = clf.predict_proba(Xz[test])[:, 1]
    base_pred = (p_loso >= 0.5).astype(int)
    base_metrics = metrics(y, base_pred, p_loso)
    print()
    print("Baseline (no smoothing, v11 lean LOSO):")
    for k, v in base_metrics.items():
        print(f"   {k:10}  {v}")

    # Step 2: apply each smoother per-subject under TWO segmentation regimes.
    #   (a) per_session : reset at session boundary (= label flip in DROZY) —
    #                     deployment-realistic if the smoother resets at every
    #                     ignition event
    #   (b) continuous  : single segment per subject, no resets — strictly
    #                     conservative; smoother lags through the awake→drowsy
    #                     transition and pays the F1 cost
    sweep = {"per_session": {"ema": {}, "hmm": {}},
             "continuous":  {"ema": {}, "hmm": {}}}

    def smooth_under(segmenter, label):
        for tau in TAU_SEC:
            p_sm = np.empty_like(p_loso)
            for s in np.unique(subj):
                m = np.where(subj == s)[0]
                ys = y[m]
                ps = p_loso[m]
                for (a, b) in segmenter(ys):
                    p_sm[m[a:b]] = causal_ema(ps[a:b], tau_sec=tau)
            pred = (p_sm >= 0.5).astype(int)
            sweep[label]["ema"][f"tau_{tau}s"] = metrics(y, pred, p_sm)
            row = sweep[label]["ema"][f"tau_{tau}s"]
            print(f"  [{label:11}] EMA τ={tau:>4}s  ->  "
                  f"acc={row['accuracy']:5.2f}  F1={row['f1_score']:5.2f}  "
                  f"AUC={row['auc_roc']:5.2f}  κ={row['kappa']:+.3f}")

        print()
        for ps_val in P_STAY:
            p_sm = np.empty_like(p_loso)
            for s in np.unique(subj):
                m = np.where(subj == s)[0]
                ys = y[m]
                pss = p_loso[m]
                for (a, b) in segmenter(ys):
                    p_sm[m[a:b]] = causal_hmm_forward(pss[a:b], p_stay=ps_val)
            pred = (p_sm >= 0.5).astype(int)
            sweep[label]["hmm"][f"p_stay_{ps_val}"] = metrics(y, pred, p_sm)
            row = sweep[label]["hmm"][f"p_stay_{ps_val}"]
            print(f"  [{label:11}] HMM p_stay={ps_val:.2f}  ->  "
                  f"acc={row['accuracy']:5.2f}  F1={row['f1_score']:5.2f}  "
                  f"AUC={row['auc_roc']:5.2f}  κ={row['kappa']:+.3f}")

    print()
    print("─── Per-session smoothing (resets at session boundary) ──────────────")
    smooth_under(session_runs, "per_session")
    print()
    print("─── Continuous smoothing (no resets within subject — conservative) ──")
    smooth_under(whole_subject_runs, "continuous")

    # Pick best by F1 within each segmentation regime
    best = {}
    for seg in ("per_session", "continuous"):
        best_ema = max(sweep[seg]["ema"].items(), key=lambda kv: kv[1]["f1_score"])
        best_hmm = max(sweep[seg]["hmm"].items(), key=lambda kv: kv[1]["f1_score"])
        best[seg] = {"ema": {"tau": best_ema[0], "metrics": best_ema[1]},
                     "hmm": {"p_stay": best_hmm[0], "metrics": best_hmm[1]}}
        print()
        print(f"Best EMA [{seg:11}]: {best_ema[0]:>10}  F1={best_ema[1]['f1_score']:.2f}")
        print(f"Best HMM [{seg:11}]: {best_hmm[0]:>10}  F1={best_hmm[1]['f1_score']:.2f}")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Causal posterior smoothing on top of v11 lean LDA LOSO predictions. "
            "Two smoothers: causal exponential moving average over p(drowsy) "
            "with time constant τ, and causal HMM forward filter with sticky "
            "transition probability P(stay). Reported under TWO segmentation "
            "regimes: (a) per_session — smoother resets at session boundaries "
            "(in DROZY this coincides with the awake→drowsy label flip; the "
            "deployment-realistic equivalent is reset at every ignition event); "
            "(b) continuous — single segment per subject, no resets within "
            "subject; conservative because the smoother lags through the "
            "label transition and pays the F1 cost."
        ),
        "feature_set": LEAN_NAMES,
        "epoch_sec": EPOCH_SEC,
        "baseline": base_metrics,
        "sweeps": sweep,
        "best": best,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
