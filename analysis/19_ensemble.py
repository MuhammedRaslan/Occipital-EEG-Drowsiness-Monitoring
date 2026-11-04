"""Why a three-model ensemble does not help.

DD-Database, self-report labels. Members, all LOSO, label-free calibration:
  M1  lean-10 shrinkage LDA                      (10_monitoring.py)
  M2  Riemannian tangent space + LDA             (12_baselines_dd.py)
  M3  M1 smoothed by the causal EMA, tau chosen by nested LOSO (14_tau_sweep.py)
Combiners: simple average; stacked LDA on the three posteriors, fitted LOSO.
Diversity (Kuncheva & Whitaker 2003): correlation of posteriors and of
errors, Yule's Q, disagreement, double fault; the oracle; and each member's
accuracy on the epochs where the best member is wrong. All on labelled test
epochs, plus within-subject posterior correlations.

Output: results/ensemble.json
"""
import os
import sys

import numpy as np
from scipy.stats import pearsonr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def pair_stats(ca, cb, pa, pb, subject):
    n11, n00 = np.sum(ca & cb), np.sum(~ca & ~cb)
    n10, n01 = np.sum(ca & ~cb), np.sum(~ca & cb)
    within = [pearsonr(pa[subject == s], pb[subject == s])[0] for s in np.unique(subject)]
    return {"posterior_r": float(pearsonr(pa, pb)[0]), "posterior_r_within_subject_median": float(np.median(within)),
            "error_r": float(np.corrcoef((~ca).astype(float), (~cb).astype(float))[0, 1]),
            "yules_Q": float((n11 * n00 - n01 * n10) / (n11 * n00 + n01 * n10)),
            "disagreement": float((n01 + n10) / len(ca)), "double_fault": float(n00 / len(ca))}


def main():
    ds = C.load_dd()
    s1 = np.load(os.path.join(C.CACHES, "scores_v2.npz"))["DD-DatabaseLDA__lean10"]
    s2 = np.load(os.path.join(C.CACHES, "scores_baselines_dd.npz"))["Riemannian_TS__LDA"]
    s3 = np.load(os.path.join(C.CACHES, "scores_tau_nested.npz"))["DD_Database"]
    P = {"M1 lean-10 LDA": s1, "M2 Riemannian TS+LDA": s2, "M3 EMA (nested tau)": s3}

    stacked = np.full(len(ds.y), np.nan)
    S = np.stack(list(P.values()), axis=1)
    for s in ds.test_subjects:
        tr = (ds.y >= 0) & (ds.subject != s)
        te = ds.subject == s
        stacked[te] = C.lda().fit(S[tr], ds.y[tr]).predict_proba(S[te])[:, 1]
    combos = {"average": S.mean(axis=1), "stacked LDA (LOSO)": stacked}

    m = (ds.y >= 0) & ~np.isnan(S).any(axis=1)
    y, subj = ds.y[m], ds.subject[m]
    single = {k: C.evaluate(ds, v) for k, v in {**P, **combos}.items()}
    correct = {k: ((v[m] >= .5).astype(int) == y) for k, v in P.items()}
    keys = list(P)
    pairs = {f"{a} ~ {b}": pair_stats(correct[a], correct[b], P[a][m], P[b][m], subj)
             for i, a in enumerate(keys) for b in keys[i + 1:]}
    best = max(keys, key=lambda k: single[k]["subject_AUC_median"])
    wrong = ~correct[best]
    on_best_errors = {k: float(correct[k][wrong].mean() * 100) for k in keys if k != best}
    oracle = float(np.mean(np.any(np.stack([correct[k] for k in keys]), axis=0)) * 100)
    summary = {k: {"pooled_AUC": v["pooled"]["AUC"], "F1w": v["pooled"]["F1w"],
                   "subject_AUC_median": v["subject_AUC_median"],
                   "accuracy": float(((P.get(k, combos.get(k))[m] >= .5).astype(int) == y).mean() * 100)}
               for k, v in single.items()}
    for k, v in summary.items():
        print(f"{k:24} pooled AUC {v['pooled_AUC']:6.2f}  median subj AUC {v['subject_AUC_median']:5.1f}  acc {v['accuracy']:5.1f}")
    print("best member:", best, "| oracle accuracy", round(oracle, 1), "| accuracy of others on its errors", on_best_errors)
    for k, v in pairs.items():
        print(f"  {k}: r {v['posterior_r']:.2f} (within {v['posterior_r_within_subject_median']:.2f})  err r {v['error_r']:.2f}  Q {v['yules_Q']:.2f}  dis {v['disagreement']:.2f}  DF {v['double_fault']:.2f}")
    C.write_result("ensemble", {"dataset": "DD-Database (self-report labels)", "summary": summary, "pairs": pairs,
                                "best_member_by_subject_AUC": best, "oracle_accuracy": oracle,
                                "member_accuracy_on_best_member_errors": on_best_errors,
                                "n_epochs": int(m.sum())}, __file__)


if __name__ == "__main__":
    main()
