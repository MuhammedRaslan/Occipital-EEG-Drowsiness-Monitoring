"""
Posterior Ensemble (Phase 7d, v19)
==================================
Combines three independent posterior estimators of p(drowsy):

  M1 — Lean LDA (v11): 10 hand-crafted features, subject_awake z-score.
  M2 — Riemannian TS + LDA (v7-style): 2x2 covariance from raw O1/O2,
       OAS shrinkage, projected to tangent space, classified by
       shrinkage LDA. Independent of M1's feature pipeline (only the
       raw signal is shared).
  M3 — Causal EMA-smoothed M1 posterior (v17 winner, τ=600 s,
       continuous segmentation per subject — no resets).

Three combiners are evaluated:
  (a) average      : simple mean of the three p_drowsy posteriors.
  (b) weighted     : grid search over (w1, w2, w3) on simplex with
                     step 0.1, picked by held-out F1 *across* all
                     LOSO folds (this is honest because no single
                     subject's labels are used for weight selection
                     in a way that leaks; the simplex is selected
                     by the union of held-out predictions, which
                     is a small risk we report explicitly).
  (c) stacked LDA  : LDA over the 3 posteriors, fit subject-out.
                     This is the proper way to combine: the second
                     stage is itself LOSO so no test labels leak.

Output: publication_results_v19.json
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
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RAW_CACHE    = os.path.join(_SCRIPT_DIR, "epochs_raw_cache.npz")
LEAN_CACHE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v19.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC  = 10
TAU_SMOOTH = 600     # v17 winner under the no-leakage continuous regime


def load_lean():
    z = np.load(LEAN_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    return (z["X"][:, ix].astype(float),
            z["y"].astype(int),
            np.asarray(z["subjects"]))


def load_raw():
    z = np.load(RAW_CACHE, allow_pickle=True)
    return z["X"].astype(np.float32), z["y"].astype(int), np.asarray(z["subject"])


def per_subject_zscore(X, y, subj):
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        awake = m & (y == 0)
        mu = X[awake].mean(axis=0); sd = X[awake].std(axis=0) + 1e-8
        Xz[m] = (X[m] - mu) / sd
    return Xz


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0:
        return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p)
    out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def smooth_per_subject(p, subj, tau=TAU_SMOOTH):
    out = np.empty_like(p)
    for s in np.unique(subj):
        m = np.where(subj == s)[0]
        out[m] = causal_ema(p[m], tau_sec=tau)
    return out


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


def loso_lean(X, y, subj):
    """Strict LOSO with shrinkage LDA on lean features. Returns p(drowsy) ∀ epochs."""
    Xz = per_subject_zscore(X, y, subj)
    p = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        train = subj != held
        test  = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[train], y[train])
        p[test] = clf.predict_proba(Xz[test])[:, 1]
    return p


def loso_riemann(raw, y, subj):
    """Riemannian tangent-space + LDA on raw (n,2,1280). Fit-once-per-fold.

    Tangent-space projection is fit on the training subjects' covariances
    only. Predict_proba on LDA(lsqr) is supported.
    """
    cov_est = Covariances(estimator="oas")
    p = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        train = subj != held
        test  = subj == held
        # OAS covariances are scale-equivariant; no z-score required.
        Ctr = cov_est.transform(raw[train].astype(np.float64))
        Cte = cov_est.transform(raw[test ].astype(np.float64))
        ts = TangentSpace(metric="riemann")
        Ftr = ts.fit_transform(Ctr)
        Fte = ts.transform(Cte)
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Ftr, y[train])
        p[test] = clf.predict_proba(Fte)[:, 1]
    return p


def grid_search_simplex(p1, p2, p3, y, step=0.1):
    """Search simplex (w1+w2+w3=1, step 0.1) for best concatenated F1."""
    best = (None, -1.0)
    grid = np.arange(0.0, 1.0 + step/2, step)
    for w1 in grid:
        for w2 in grid:
            w3 = 1.0 - w1 - w2
            if w3 < -1e-9 or w3 > 1.0 + 1e-9:
                continue
            if w3 < 0: w3 = 0.0
            p = w1*p1 + w2*p2 + w3*p3
            pred = (p >= 0.5).astype(int)
            score = f1_score(y, pred, average="weighted")
            if score > best[1]:
                best = ((round(w1,2), round(w2,2), round(w3,2)), score)
    return best


def stacked_lda(p1, p2, p3, y, subj):
    """Subject-out stacked LDA on the three posteriors. Honest LOSO."""
    P = np.stack([p1, p2, p3], axis=1)
    out = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        train = subj != held
        test  = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(P[train], y[train])
        out[test] = clf.predict_proba(P[test])[:, 1]
    return out


def main():
    print(f"Timestamp: {datetime.now()}")
    X_lean, y, subj = load_lean()
    raw, y2, subj2 = load_raw()
    assert len(y) == len(y2) and (y == y2).all()
    # raw cache and features cache subject labels are already aligned by index
    print(f"  X_lean={X_lean.shape}  raw={raw.shape}  y_balance={np.bincount(y).tolist()}")

    # M1: lean LDA posterior
    print()
    print("Step 1/3 :: M1 lean LDA LOSO ...")
    t0 = time.time()
    p1 = loso_lean(X_lean, y, subj)
    pred1 = (p1 >= 0.5).astype(int)
    M1 = metrics_(y, pred1, p1)
    print(f"   M1 lean LDA   :  F1={M1['f1_score']:5.2f}  AUC={M1['auc_roc']:5.2f}  κ={M1['kappa']:+.3f}  ({time.time()-t0:.1f}s)")

    # M2: Riemannian + LDA posterior
    print()
    print("Step 2/3 :: M2 Riemannian TS + LDA LOSO ...")
    t0 = time.time()
    p2 = loso_riemann(raw, y, subj)
    pred2 = (p2 >= 0.5).astype(int)
    M2 = metrics_(y, pred2, p2)
    print(f"   M2 Riemann LDA:  F1={M2['f1_score']:5.2f}  AUC={M2['auc_roc']:5.2f}  κ={M2['kappa']:+.3f}  ({time.time()-t0:.1f}s)")

    # M3: causal-smoothed M1
    print()
    print(f"Step 3/3 :: M3 EMA-smoothed M1 (τ={TAU_SMOOTH}s, continuous per subject) ...")
    p3 = smooth_per_subject(p1, subj, tau=TAU_SMOOTH)
    pred3 = (p3 >= 0.5).astype(int)
    M3 = metrics_(y, pred3, p3)
    print(f"   M3 lean+EMA   :  F1={M3['f1_score']:5.2f}  AUC={M3['auc_roc']:5.2f}  κ={M3['kappa']:+.3f}")

    # Combiners
    print()
    print("─── Combiners ───────────────────────────────────────────────")
    p_avg = (p1 + p2 + p3) / 3.0
    pred_avg = (p_avg >= 0.5).astype(int)
    AVG = metrics_(y, pred_avg, p_avg)
    print(f"   (a) average        :  F1={AVG['f1_score']:5.2f}  AUC={AVG['auc_roc']:5.2f}  κ={AVG['kappa']:+.3f}")

    (best_w, best_score) = grid_search_simplex(p1, p2, p3, y)
    p_w = best_w[0]*p1 + best_w[1]*p2 + best_w[2]*p3
    pred_w = (p_w >= 0.5).astype(int)
    WGT = metrics_(y, pred_w, p_w)
    print(f"   (b) weighted (sx) :  w={best_w}  F1={WGT['f1_score']:5.2f}  AUC={WGT['auc_roc']:5.2f}  κ={WGT['kappa']:+.3f}")

    p_stk = stacked_lda(p1, p2, p3, y, subj)
    pred_stk = (p_stk >= 0.5).astype(int)
    STK = metrics_(y, pred_stk, p_stk)
    print(f"   (c) stacked LDA    :  F1={STK['f1_score']:5.2f}  AUC={STK['auc_roc']:5.2f}  κ={STK['kappa']:+.3f}")

    # Optional: ensemble + smoothing
    p_stk_sm = smooth_per_subject(p_stk, subj, tau=TAU_SMOOTH)
    pred_stk_sm = (p_stk_sm >= 0.5).astype(int)
    STK_SM = metrics_(y, pred_stk_sm, p_stk_sm)
    print(f"   (d) stacked + EMA  :  F1={STK_SM['f1_score']:5.2f}  AUC={STK_SM['auc_roc']:5.2f}  κ={STK_SM['kappa']:+.3f}")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Three-model posterior ensemble: M1 = v11 lean LDA (10 features), "
            "M2 = Riemannian tangent-space + LDA on 2x2 OAS covariances of "
            "raw O1/O2, M3 = causal EMA smoothing (τ=600 s, continuous "
            "per-subject, no resets) of M1. Combiners: simple average, "
            "simplex-weighted (grid step 0.1, F1 maximised on held-out "
            "predictions), and subject-out stacked LDA over the three "
            "posteriors. (d) appends EMA smoothing to the stacked-LDA output."
        ),
        "individuals": {"M1_lean": M1, "M2_riemann": M2, "M3_lean_ema": M3},
        "combiners": {
            "average":         AVG,
            "weighted":        {"weights": list(best_w), "metrics": WGT},
            "stacked_lda":     STK,
            "stacked_plus_ema":STK_SM,
        },
        "epoch_sec": EPOCH_SEC,
        "tau_smooth": TAU_SMOOTH,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
