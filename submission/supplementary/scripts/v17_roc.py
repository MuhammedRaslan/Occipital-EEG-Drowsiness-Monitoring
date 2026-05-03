"""
Tier-1 polish #1: Monitoring ROC for the v17 EMA-smoothed classifier
====================================================================
Reports a full ROC curve for the deployment-headline model (v11 lean LDA
+ causal EMA smoothing, tau=600 s, continuous per-subject). In the v17
sweep we only reported F1 at threshold=0.5 — an obvious reviewer ask
for a safety paper is "what's the operating envelope?" This script
answers it.

Outputs:
  - publication_results_v17_roc.json  (ROC point cloud + 3 chosen ops)
  - publication_figures_v5/fig10_v17_roc.png

Chosen operating points (reviewer-facing):
  * HIGH-PRECISION (FPR<=5%): lowest-FA point in the cluster
  * BALANCED      (FPR<=10%): operating point of the F1 maximiser
  * HIGH-RECALL   (FPR<=20%): maximises TPR at that budget
"""

import os, sys, io, json, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    roc_curve, roc_auc_score, accuracy_score, f1_score,
    precision_score, recall_score, cohen_kappa_score,
)

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LEAN_CACHE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v17_roc.json")
FIG_DIR      = os.path.join(_SCRIPT_DIR, "publication_figures_v5")
FIG_PATH     = os.path.join(FIG_DIR, "fig10_v17_roc.png")
os.makedirs(FIG_DIR, exist_ok=True)

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC = 10
TAU_SEC   = 600   # v17 winner, continuous regime


def load_lean():
    z = np.load(LEAN_CACHE, allow_pickle=True)
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


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0:
        return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p)
    out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def metrics_at(y_true, y_score, thr):
    yp = (y_score >= thr).astype(int)
    return {
        "threshold": round(float(thr), 4),
        "accuracy":  round(accuracy_score(y_true, yp) * 100, 2),
        "f1_score":  round(f1_score(y_true, yp, average="weighted") * 100, 2),
        "precision": round(precision_score(y_true, yp, average="weighted", zero_division=0) * 100, 2),
        "recall":    round(recall_score(y_true, yp, average="weighted", zero_division=0) * 100, 2),
        "kappa":     round(cohen_kappa_score(y_true, yp), 4),
        "tpr":       round(float(np.sum((yp == 1) & (y_true == 1)) / max(1, np.sum(y_true == 1))), 4),
        "fpr":       round(float(np.sum((yp == 1) & (y_true == 0)) / max(1, np.sum(y_true == 0))), 4),
    }


def main():
    print(f"Timestamp: {datetime.now()}")
    X, y, subj = load_lean()
    Xz = per_subject_zscore(X, y, subj)

    # Step 1 — LOSO lean LDA posteriors (v11).
    p_loso = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        train = subj != held; test = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[train], y[train])
        p_loso[test] = clf.predict_proba(Xz[test])[:, 1]

    # Step 2 — v17 continuous EMA smoothing (one segment per subject, no resets).
    p_sm = np.empty_like(p_loso)
    for s in np.unique(subj):
        m = np.where(subj == s)[0]
        p_sm[m] = causal_ema(p_loso[m], tau_sec=TAU_SEC)

    # ROC on the smoothed posterior.
    fpr, tpr, thr = roc_curve(y, p_sm)
    auc = roc_auc_score(y, p_sm) * 100

    # Reviewer-facing operating points: pick thresholds within FPR budgets.
    def op_at_fpr_budget(budget):
        ok = fpr <= budget
        if not ok.any():
            return None
        # Among valid thresholds, pick the one with the highest TPR,
        # tie-breaking on lower FPR. `tpr` / `fpr` are monotone in thr
        # from sklearn, so the highest-TPR point under the budget is at
        # the largest index where fpr <= budget.
        idx = int(np.argmax(tpr[ok]))
        true_idx = np.where(ok)[0][idx]
        return float(thr[true_idx])

    thr_hi_p = op_at_fpr_budget(0.05)
    thr_bal  = op_at_fpr_budget(0.10)
    thr_hi_r = op_at_fpr_budget(0.20)

    # F1-maximum operating point is the traditional "best" in binary classification.
    f1s = np.array([f1_score(y, (p_sm >= t).astype(int), average="weighted") for t in thr])
    best_f1_idx = int(np.argmax(f1s))
    thr_f1max = float(thr[best_f1_idx])

    ops = {
        "high_precision_FPR5":   metrics_at(y, p_sm, thr_hi_p),
        "balanced_FPR10":        metrics_at(y, p_sm, thr_bal),
        "high_recall_FPR20":     metrics_at(y, p_sm, thr_hi_r),
        "F1_max":                metrics_at(y, p_sm, thr_f1max),
        "default_thr050":        metrics_at(y, p_sm, 0.50),
    }

    print()
    print(f"AUC (v17 smoothed posterior, DROZY LOSO) = {auc:.2f}")
    print()
    print("Reviewer-facing operating points:")
    for name, m in ops.items():
        print(f"  {name:25}  thr={m['threshold']:.3f}  "
              f"F1={m['f1_score']:5.2f}  acc={m['accuracy']:5.2f}  "
              f"TPR={m['tpr']:.3f}  FPR={m['fpr']:.3f}  kappa={m['kappa']:+.3f}")

    # Figure: ROC with the three chosen operating points highlighted.
    fig, ax = plt.subplots(figsize=(5.5, 5.0))
    ax.plot(fpr, tpr, "-", lw=2, color="#1f3b6e", label=f"v17 ROC (AUC = {auc:.2f}%)")
    ax.plot([0, 1], [0, 1], "--", color="0.6", lw=1, label="chance")
    labels = {
        "high_precision_FPR5":  ("o", "#1a7f3d", "high-precision (FPR<=5%)"),
        "balanced_FPR10":       ("s", "#c75f1e", "balanced (FPR<=10%)"),
        "high_recall_FPR20":    ("D", "#a02a2a", "high-recall (FPR<=20%)"),
    }
    for name, (mk, col, lbl) in labels.items():
        m = ops[name]
        ax.plot(m["fpr"], m["tpr"], mk, color=col, ms=9, mec="k", mew=0.6,
                label=f"{lbl}: TPR={m['tpr']:.2f}, F1={m['f1_score']:.1f}")
    ax.set_xlabel("False-positive rate (awake misclassified as drowsy)")
    ax.set_ylabel("True-positive rate (drowsy detected)")
    ax.set_title("Monitoring-track ROC — v11 lean LDA + v17 causal EMA (tau=600 s)\nDROZY LOSO, 10 subjects, 14498 epochs")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIG_PATH, dpi=200)
    plt.close(fig)
    print(f"  figure -> {FIG_PATH}")

    # Save the point cloud (downsampled for the JSON) + the chosen ops.
    sample = np.linspace(0, len(fpr) - 1, 200).astype(int)
    payload = {
        "timestamp":  datetime.now().isoformat(),
        "methodology": (
            "Full ROC of the v11 lean LDA + v17 causal EMA (tau=600 s, "
            "continuous per-subject) on DROZY LOSO. Operating points at "
            "three reviewer-facing FPR budgets (5%, 10%, 20%) plus the "
            "F1-max point and the default thr=0.5."
        ),
        "tau_smooth_sec": TAU_SEC,
        "auc_roc_smoothed": round(auc, 2),
        "operating_points": ops,
        "roc_curve_sample": {
            "fpr":       [round(float(x), 5) for x in fpr[sample]],
            "tpr":       [round(float(x), 5) for x in tpr[sample]],
            "threshold": [round(float(x), 5) for x in thr[sample]],
        },
        "n_epochs":  int(len(y)),
        "n_subjects": int(len(np.unique(subj))),
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  json   -> {RESULTS_FILE}")


if __name__ == "__main__":
    main()
