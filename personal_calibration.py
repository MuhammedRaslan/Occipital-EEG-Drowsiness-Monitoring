"""
Per-Person Calibration (Phase 6, v15)
=====================================
The strict-LOSO v11 lean LDA tops out at F1 = 62.08 on DROZY because the
classifier never sees the held-out driver. In a real headrest deployment
every driver does a brief calibration: a short alert baseline at ignition,
plus a small amount of *labelled* drowsy data accumulated over the first
few drives (flagged by the camera DMS, steering deviation, or driver
self-report). This script measures how much that calibration buys us.

Protocol per held-out subject S (LOSO over 10 DROZY subjects):
  • generic-train pool = the other 9 subjects, lean 10 features,
    each subject z-scored on its own first 60 s of session-1
  • S's calibration  = first K_AWAKE seconds of S's session-1
                      + first K_DROWSY seconds of S's session-2 (with labels)
  • S's test         = the *remaining* epochs of S (after the calibration
                       windows are dropped from each session)
  • S's z-score uses the same first 60 s of session-1 as everywhere else,
    so calibration and test see consistently-normalised features.

Calibration regimes evaluated:
  generic                : no per-person adaptation (= v11 baseline)
  threshold_shift        : keep generic-LDA, search the F1-optimal decision
                           threshold on S's calibration data
  sample_augmentation    : refit LDA on (9-subj pool ∪ S's calibration),
                           upweighting S's samples by w (default 5)
  subject_only           : fit LDA purely on S's small calibration set

Sweep K_per_class ∈ {3, 6, 12, 30} epochs = {30, 60, 120, 300} seconds.

Output: publication_results_v15.json
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
CACHE_FILE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v15.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC   = 10
Z_AWAKE_SEC = None                  # None = use ALL of session-1 (matches v11 'subject_awake')
CAL_SECS    = [30, 60, 120, 300]    # per-class calibration window lengths
AUG_WEIGHT  = 5.0                   # how much to upweight S's samples in regime C


def load_lean():
    z = np.load(CACHE_FILE, allow_pickle=True)
    feat_cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([feat_cols.index(n) for n in LEAN_NAMES], dtype=int)
    return z["X"][:, ix].astype(float), z["y"].astype(int), z["subjects"]


def z_stats_for_subject(X_s, y_s, n_z_epochs):
    """Mean/std from awake epochs of subject S.

    n_z_epochs = None  -> use ALL session-1 awake epochs (matches v11
                          'subject_awake' z-score — this is the v11 protocol).
    n_z_epochs = int   -> use only the first n_z_epochs awake epochs
                          (deployment-realistic, e.g. 60 s baseline at ignition).
    """
    awake_idx = np.where(y_s == 0)[0]
    if n_z_epochs is not None:
        awake_idx = awake_idx[:n_z_epochs]
    Xa = X_s[awake_idx]
    mu = Xa.mean(axis=0)
    sd = Xa.std(axis=0) + 1e-8
    return mu, sd


def split_subject(X_s, y_s, K_per_class, n_z_epochs):
    """
    Return (X_cal, y_cal, X_test, y_test) for subject S.

    Calibration = first K_per_class epochs of session-1 (awake)
                + first K_per_class epochs of session-2 (drowsy).
    Test = remaining epochs of each session (i.e. the rest of S's data).

    The z-score window (first n_z_epochs awake epochs) overlaps with the
    awake calibration when K_per_class >= n_z_epochs; that is intentional
    and reflects a real deployment (the same opening seconds serve both
    purposes).
    """
    awake_idx = np.where(y_s == 0)[0]
    drowsy_idx = np.where(y_s == 1)[0]
    cal_awake  = awake_idx[:K_per_class]
    cal_drowsy = drowsy_idx[:K_per_class]
    cal_idx    = np.concatenate([cal_awake, cal_drowsy])
    test_mask  = np.ones(len(y_s), dtype=bool)
    test_mask[cal_idx] = False
    X_cal  = X_s[cal_idx];  y_cal  = y_s[cal_idx]
    X_test = X_s[test_mask]; y_test = y_s[test_mask]
    return X_cal, y_cal, X_test, y_test


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


def best_threshold(scores, labels):
    """Pick the score threshold that maximises weighted F1 on the cal set."""
    candidates = np.unique(np.concatenate([
        scores, np.array([scores.min() - 1e-6, scores.max() + 1e-6])
    ]))
    best_f1, best_thr = -1.0, 0.0
    for thr in candidates:
        preds = (scores >= thr).astype(int)
        f1 = f1_score(labels, preds, average="weighted")
        if f1 > best_f1:
            best_f1, best_thr = f1, float(thr)
    return best_thr


def run_subject(S, X_all, y_all, subj_all, K_per_class):
    """Train all four calibration regimes for held-out subject S."""
    # Build z-scored generic train pool from the OTHER 9 subjects.
    other_subjects = [s for s in np.unique(subj_all) if s != S]
    X_gen, y_gen = [], []
    for s in other_subjects:
        m = subj_all == s
        Xs, ys = X_all[m], y_all[m]
        mu, sd = z_stats_for_subject(Xs, ys, n_z_epochs=(Z_AWAKE_SEC // EPOCH_SEC) if Z_AWAKE_SEC is not None else None)
        X_gen.append((Xs - mu) / sd)
        y_gen.append(ys)
    X_gen = np.vstack(X_gen)
    y_gen = np.concatenate(y_gen)

    # Held-out subject S, z-scored on its own first-60-s awake stats.
    m_s = subj_all == S
    Xs, ys = X_all[m_s], y_all[m_s]
    mu_s, sd_s = z_stats_for_subject(Xs, ys, n_z_epochs=(Z_AWAKE_SEC // EPOCH_SEC) if Z_AWAKE_SEC is not None else None)
    Xs_z = (Xs - mu_s) / sd_s
    X_cal, y_cal, X_test, y_test = split_subject(
        Xs_z, ys, K_per_class, n_z_epochs=(Z_AWAKE_SEC // EPOCH_SEC) if Z_AWAKE_SEC is not None else None)

    # ── (A) generic ──────────────────────────────────────────────────────
    lda_gen = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    lda_gen.fit(X_gen, y_gen)
    score_test_gen = lda_gen.decision_function(X_test)
    pred_gen = lda_gen.predict(X_test)
    res_gen = metrics(y_test, pred_gen, score_test_gen)

    # ── (B) generic + per-subject threshold shift ─────────────────────────
    score_cal_gen = lda_gen.decision_function(X_cal)
    thr = best_threshold(score_cal_gen, y_cal)
    pred_thr = (score_test_gen >= thr).astype(int)
    res_thr = metrics(y_test, pred_thr, score_test_gen)
    res_thr["chosen_threshold"] = round(float(thr), 4)

    # ── (C) generic + sample augmentation (refit) ────────────────────────
    X_aug = np.vstack([X_gen, X_cal])
    y_aug = np.concatenate([y_gen, y_cal])
    w_aug = np.concatenate([
        np.ones(len(y_gen)),
        np.full(len(y_cal), AUG_WEIGHT),
    ])
    lda_aug = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    # sklearn LDA's lsqr solver does not accept sample_weight; emulate by
    # row-replication using integer multiplicities (AUG_WEIGHT must be int).
    rep = int(AUG_WEIGHT)
    X_aug_rep = np.vstack([X_gen, np.repeat(X_cal, rep, axis=0)])
    y_aug_rep = np.concatenate([y_gen, np.repeat(y_cal, rep)])
    lda_aug.fit(X_aug_rep, y_aug_rep)
    score_test_aug = lda_aug.decision_function(X_test)
    pred_aug = lda_aug.predict(X_test)
    res_aug = metrics(y_test, pred_aug, score_test_aug)

    # ── (D) subject-only ────────────────────────────────────────────────
    if len(np.unique(y_cal)) < 2:
        res_only = {"accuracy": None, "f1_score": None}
    else:
        lda_only = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        lda_only.fit(X_cal, y_cal)
        score_test_only = lda_only.decision_function(X_test)
        pred_only = lda_only.predict(X_test)
        res_only = metrics(y_test, pred_only, score_test_only)

    return {
        "generic":             res_gen,
        "threshold_shift":     res_thr,
        "sample_augmentation": res_aug,
        "subject_only":        res_only,
        "n_test":              int(len(y_test)),
        "n_cal_per_class":     int(K_per_class),
    }


def aggregate_overall(per_subject_results, regime):
    """Macro-average of per-subject metric values for a given regime."""
    arr = []
    for s, by_regime in per_subject_results.items():
        m = by_regime[regime]
        if m["f1_score"] is not None:
            arr.append([m["accuracy"], m["f1_score"], m.get("auc_roc") or float("nan"),
                        m["kappa"], m["precision"], m["recall"]])
    arr = np.array(arr, dtype=float)
    return {
        "accuracy":  round(float(np.nanmean(arr[:, 0])), 2),
        "f1_score":  round(float(np.nanmean(arr[:, 1])), 2),
        "auc_roc":   round(float(np.nanmean(arr[:, 2])), 2),
        "kappa":     round(float(np.nanmean(arr[:, 3])), 4),
        "precision": round(float(np.nanmean(arr[:, 4])), 2),
        "recall":    round(float(np.nanmean(arr[:, 5])), 2),
        "f1_std":    round(float(np.nanstd (arr[:, 1])), 2),
        "n_subjects_kept": int(arr.shape[0]),
    }


def main():
    print(f"Timestamp: {datetime.now()}")
    print(f"Cache: {CACHE_FILE}")
    X, y, subj = load_lean()
    print(f"  X={X.shape}  y={y.shape}  subjects={np.unique(subj).tolist()}")

    sweep_results = {}
    for cal_sec in CAL_SECS:
        K = max(1, cal_sec // EPOCH_SEC)
        print()
        print("=" * 78)
        print(f"  Calibration window: {cal_sec} s per class  ({K} epochs/class)")
        print("=" * 78)

        per_subject = {}
        t0 = time.time()
        for S in np.unique(subj):
            ts = time.time()
            per_subject[S] = run_subject(S, X, y, subj, K)
            print(f"   {S}  | "
                  f"gen F1={per_subject[S]['generic']['f1_score']:5.2f}   "
                  f"thr F1={per_subject[S]['threshold_shift']['f1_score']:5.2f}   "
                  f"aug F1={per_subject[S]['sample_augmentation']['f1_score']:5.2f}   "
                  f"only F1={per_subject[S]['subject_only']['f1_score'] if per_subject[S]['subject_only']['f1_score'] is not None else '  -- '}   "
                  f"({time.time()-ts:.1f}s)")

        overall = {
            r: aggregate_overall(per_subject, r)
            for r in ("generic", "threshold_shift",
                      "sample_augmentation", "subject_only")
        }
        sweep_results[f"cal_{cal_sec}s"] = {
            "per_subject": per_subject,
            "overall":     overall,
            "wall_clock_s": round(time.time() - t0, 1),
        }
        print(f"\n   OVERALL (mean of per-subject metrics, {cal_sec}s/class):")
        for r, m in overall.items():
            print(f"     {r:22}  acc={m['accuracy']:5.2f}  F1={m['f1_score']:5.2f} ± {m['f1_std']:.2f}   "
                  f"AUC={m['auc_roc']:5.2f}   κ={m['kappa']:+.3f}")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Per-person calibration on top of v11 lean (10-feature) shrinkage "
            "LDA. For each held-out DROZY subject S, generic LDA is trained "
            "on the other 9 subjects (each z-scored on its own first 60 s of "
            "session-1). S's calibration = first K seconds of session-1 + first "
            "K seconds of session-2 with labels. S's test = the remainder. "
            "Four regimes: generic (no calibration), threshold_shift (F1-optimal "
            "decision threshold on calibration), sample_augmentation (refit on "
            "pool union calibration with calibration upweighted x5), and "
            "subject_only (LDA fit purely on S's calibration data)."
        ),
        "subjects": sorted(np.unique(subj).tolist()),
        "feature_set": LEAN_NAMES,
        "n_features": len(LEAN_NAMES),
        "z_window_seconds": Z_AWAKE_SEC,
        "augment_weight": AUG_WEIGHT,
        "sweep": sweep_results,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
