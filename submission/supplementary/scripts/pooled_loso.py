"""
Pooled DROZY + SEED-VIG LOSO (Phase 7a, v16)
============================================
Concatenates the lean 10-feature representation from DROZY (10 subjects,
14,498 epochs) with SEED-VIG (21 subjects, 9,155 epochs) and runs strict
Leave-One-Subject-Out across the union of 31 unique subjects.

Z-score is per-subject `subject_awake` (mean/std from each subject's
label==0 epochs); each fold trains a shrinkage LDA on the 30 other
subjects' z-scored features and tests on the held-out subject.

Reports both the concatenated F1 (one big confusion matrix over all
held-out predictions) and the mean per-subject F1 ± std, which are the
two metric flavours used elsewhere in this paper.

Output: publication_results_v16.json
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
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score,
)

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DROZY_CACHE  = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
SEED_CACHE   = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v16.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]


def load_drozy_lean():
    z = np.load(DROZY_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    X = z["X"][:, ix].astype(float)
    y = z["y"].astype(int)
    subj = np.array([f"DROZY-{s}" for s in z["subjects"]], dtype=object)
    return X, y, subj


def load_seed_lean():
    z = np.load(SEED_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_names"]]
    # SEED cache already in lean order, but be defensive.
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    X = z["X"][:, ix].astype(float)
    y = z["y"].astype(int)
    subj = np.array([f"SEED-{s}" for s in z["subject"]], dtype=object)
    return X, y, subj


def per_subject_zscore(X, y, subj):
    """Z-score each subject independently using its own awake (label==0) epochs."""
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        awake = m & (y == 0)
        if awake.sum() < 2:
            mu = X[m].mean(axis=0); sd = X[m].std(axis=0) + 1e-8
        else:
            mu = X[awake].mean(axis=0); sd = X[awake].std(axis=0) + 1e-8
        Xz[m] = (X[m] - mu) / sd
    return Xz


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
    Xd, yd, sd = load_drozy_lean()
    Xs, ys, ss = load_seed_lean()
    print(f"  DROZY  : X={Xd.shape}  y_balance={np.bincount(yd).tolist()}  subjects={len(np.unique(sd))}")
    print(f"  SEED   : X={Xs.shape}  y_balance={np.bincount(ys).tolist()}  subjects={len(np.unique(ss))}")

    X = np.vstack([Xd, Xs])
    y = np.concatenate([yd, ys])
    subj = np.concatenate([sd, ss])
    print(f"  POOLED : X={X.shape}  y_balance={np.bincount(y).tolist()}  subjects={len(np.unique(subj))}")

    # Per-subject z-score uses each subject's own awake epochs; safe to do
    # globally up-front because no z-stat ever crosses subject boundaries.
    Xz = per_subject_zscore(X, y, subj)

    all_subjects = np.unique(subj)
    per_subj = []
    y_true_all, y_pred_all, y_score_all = [], [], []

    print()
    print("=" * 84)
    print(f"  LOSO over {len(all_subjects)} pooled subjects (DROZY ∪ SEED-VIG), lean LDA")
    print("=" * 84)
    t0_total = time.time()
    for held in all_subjects:
        ts = time.time()
        train = subj != held
        test  = subj == held
        if test.sum() == 0 or len(np.unique(y[train])) < 2:
            continue
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[train], y[train])
        sc = clf.decision_function(Xz[test])
        pr = clf.predict(Xz[test])
        m = metrics(y[test], pr, sc)
        m["held_out"] = held
        m["n_test"] = int(test.sum())
        m["dataset"] = "DROZY" if held.startswith("DROZY-") else "SEED"
        per_subj.append(m)
        y_true_all.append(y[test])
        y_pred_all.append(pr)
        y_score_all.append(sc)
        print(f"   {held:<12}  n={test.sum():>5}  acc={m['accuracy']:5.2f}  F1={m['f1_score']:5.2f}  "
              f"AUC={m.get('auc_roc','--'):>5}  κ={m['kappa']:+.3f}  ({time.time()-ts:.1f}s)")

    y_true_all  = np.concatenate(y_true_all)
    y_pred_all  = np.concatenate(y_pred_all)
    y_score_all = np.concatenate(y_score_all)
    overall_concat = metrics(y_true_all, y_pred_all, y_score_all)

    f1s = np.array([m["f1_score"] for m in per_subj], dtype=float)
    accs = np.array([m["accuracy"] for m in per_subj], dtype=float)
    aucs = np.array([m["auc_roc"] if m.get("auc_roc") is not None else np.nan for m in per_subj], dtype=float)
    kaps = np.array([m["kappa"] for m in per_subj], dtype=float)
    overall_mean = {
        "accuracy_mean":  round(float(np.nanmean(accs)), 2),
        "accuracy_std":   round(float(np.nanstd (accs)), 2),
        "f1_score_mean":  round(float(np.nanmean(f1s)),  2),
        "f1_score_std":   round(float(np.nanstd (f1s)),  2),
        "auc_roc_mean":   round(float(np.nanmean(aucs)), 2),
        "kappa_mean":     round(float(np.nanmean(kaps)), 4),
    }

    # Per-dataset breakdown
    by_dataset = {}
    for d in ("DROZY", "SEED"):
        sel = [m for m in per_subj if m["dataset"] == d]
        if not sel: continue
        f = np.array([m["f1_score"] for m in sel])
        a = np.array([m["accuracy"] for m in sel])
        u = np.array([m["auc_roc"] if m.get("auc_roc") is not None else np.nan for m in sel])
        k = np.array([m["kappa"] for m in sel])
        by_dataset[d] = {
            "n_subjects": len(sel),
            "f1_mean":  round(float(f.mean()), 2),  "f1_std": round(float(f.std()), 2),
            "acc_mean": round(float(a.mean()), 2),
            "auc_mean": round(float(np.nanmean(u)), 2),
            "kappa_mean": round(float(k.mean()), 4),
        }

    print()
    print("=" * 84)
    print(f"  OVERALL (concatenated, n={len(y_true_all)} epochs):")
    for k, v in overall_concat.items():
        print(f"     {k:10}  {v}")
    print(f"  OVERALL (mean per-subject across {len(per_subj)} subjects):")
    for k, v in overall_mean.items():
        print(f"     {k:18}  {v}")
    print(f"  PER-DATASET:")
    for d, m in by_dataset.items():
        print(f"     {d:6}  n={m['n_subjects']:2}  F1={m['f1_mean']:5.2f}±{m['f1_std']:5.2f}  "
              f"acc={m['acc_mean']:5.2f}  AUC={m['auc_mean']:5.2f}  κ={m['kappa_mean']:+.3f}")
    print(f"  total wall-clock: {time.time()-t0_total:.1f}s")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Pooled DROZY + SEED-VIG, lean 10-feature shrinkage LDA, strict "
            "31-subject LOSO. Z-score is per-subject `subject_awake` (mean/std "
            "from each subject's label==0 epochs). Each fold trains LDA on 30 "
            "subjects and tests on 1; reported metrics are both concatenated "
            "(one confusion matrix over all held-out predictions) and mean "
            "per-subject F1 ± std."
        ),
        "feature_set": LEAN_NAMES,
        "n_subjects": len(all_subjects),
        "n_epochs": int(len(y)),
        "overall_concat": overall_concat,
        "overall_mean_per_subject": overall_mean,
        "by_dataset": by_dataset,
        "per_subject": per_subj,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
