"""Why pooled and per-driver AUC disagree on the DD-Database.

A model whose mean score differs between drivers, in step with each driver's
drowsy share, gains pooled AUC without ranking better within any driver. For
the lean-10 LDA and the three raw-signal baselines this script gives:

1. the pooled AUC, and the pooled AUC after subtracting each driver's mean
   score (no driver offsets left);
2. the Spearman correlation, over drivers, between mean score and drowsy
   share;
3. a paired Wilcoxon test of each baseline's per-driver AUC against the
   lean-10 LDA, Holm-corrected over the three baselines.

Uses the LOSO scores saved by 10_monitoring.py and 12_baselines_dd.py.

Output: results/offsets.json
"""
import os
import sys

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BASELINES = {"Riemannian TS + LDA": "Riemannian_TS__LDA", "Riemannian TS + LogReg": "Riemannian_TS__LogReg",
             "EEGNet": "EEGNet"}


def offsets(ds, p):
    m = (ds.y >= 0) & np.isin(ds.subject, ds.test_subjects) & ~np.isnan(p)
    subs = [s for s in ds.test_subjects if len(np.unique(ds.y[m & (ds.subject == s)])) == 2]
    centred, mean, share, auc = p.copy(), [], [], {}
    for s in subs:
        k = m & (ds.subject == s)
        mean.append(float(p[k].mean()))
        share.append(float(ds.y[k].mean()))
        auc[s] = 100 * float(roc_auc_score(ds.y[k], p[k]))
        centred[k] -= p[k].mean()
    return {"pooled_AUC": 100 * roc_auc_score(ds.y[m], p[m]),
            "pooled_AUC_offsets_removed": 100 * roc_auc_score(ds.y[m], centred[m]),
            "rho_mean_score_drowsy_share": float(spearmanr(mean, share)[0]),
            "subject_AUC_median": float(np.median(list(auc.values()))), "subject_AUC": auc}


def main():
    ds = C.load_dd()
    lean = np.load(os.path.join(C.CACHES, "scores_v2.npz"), allow_pickle=True)[f"{ds.name}LDA__lean10"]
    base = np.load(os.path.join(C.CACHES, "scores_baselines_dd.npz"))
    res = {"Lean-10 LDA": offsets(ds, lean)}
    for name, key in BASELINES.items():
        res[name] = offsets(ds, base[key])
    ref = res["Lean-10 LDA"]["subject_AUC"]
    tests = {name: C.paired_wilcoxon([ref[s] for s in ref], [res[name]["subject_AUC"][s] for s in ref])
             for name in BASELINES}
    for name, p in zip(tests, C.holm([t["p_two_sided"] for t in tests.values()])):
        tests[name]["p_holm"] = p
    for name, r in res.items():
        t = tests.get(name)
        print(f"{name:24s} pooled {r['pooled_AUC']:5.1f}  offsets removed {r['pooled_AUC_offsets_removed']:5.1f}  "
              f"rho {r['rho_mean_score_drowsy_share']:+.2f}  median {r['subject_AUC_median']:5.1f}"
              + (f"  vs lean-10: {t['n_increase']} up, {t['n_decrease']} down, Holm p {t['p_holm']:.2f}" if t else ""))
    C.write_result("offsets", {"DD-Database": res, "versus_lean10": tests}, __file__)


if __name__ == "__main__":
    main()
