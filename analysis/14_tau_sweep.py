"""Temporal smoothing: tau sweep with nested selection.

The causal EMA uses the true time step between epochs (gaps decay memory) and
restarts at every recording. Two analyses per dataset, lean-10 LDA:

  * fixed-tau sweep: pooled and per-subject metrics for each tau;
  * nested selection: for each held-out subject, tau is chosen by an inner
    LOSO over the training subjects (maximising inner pooled AUC; ties go
    to the smaller tau) and then applied to the held-out subject.

Outputs: results/tau_sweep.json, caches/scores_tau_nested.npz
"""
import os
import sys

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

TAUS = [0, 10, 30, 60, 120, 300, 600, 900, 1200]


def smoothed(ds, p, tau):
    return C.smooth_by_recording(p, ds.t, ds.recording, tau)


def inner_choice(ds, Xn, outer):
    train_subjects = [s for s in np.unique(ds.subject) if s != outer]
    inner_test = [s for s in train_subjects if s in ds.test_subjects]
    p = np.full(len(ds.y), np.nan)
    for h in inner_test:
        tr = (ds.y >= 0) & (ds.subject != h) & (ds.subject != outer)
        te = ds.subject == h
        p[te] = C.lda().fit(Xn[tr], ds.y[tr]).predict_proba(Xn[te])[:, 1]
    m_eval = (ds.y >= 0) & np.isin(ds.subject, inner_test) & ~np.isnan(p)
    best, best_auc = None, -1
    for tau in TAUS:
        ps = smoothed(ds, p, tau)
        auc = roc_auc_score(ds.y[m_eval], ps[m_eval])
        if auc > best_auc + 1e-9:
            best, best_auc = tau, auc
    return best, best_auc


def run(ds):
    Xn = ds.calibrated(C.LEAN10)
    p = C.loso_scores(Xn, ds.y, ds.subject, test_subjects=ds.test_subjects)
    sweep = {}
    for tau in TAUS:
        r = C.evaluate(ds, smoothed(ds, p, tau))
        r.pop("bootstrap", None)
        sweep[str(tau)] = {"pooled": r["pooled"], "subject_AUC_median": r["subject_AUC_median"],
                           "subjects_AUC_above_50": r["subjects_AUC_above_50"]}
    chosen, p_nested = {}, np.full(len(ds.y), np.nan)
    for s in ds.test_subjects:
        tau, inner_auc = inner_choice(ds, Xn, s)
        chosen[s] = {"tau": tau, "inner_AUC": 100 * inner_auc}
        m = ds.subject == s
        p_nested[m] = smoothed(ds, p, tau)[m]
    nested = C.evaluate(ds, p_nested)
    unsmoothed = C.evaluate(ds, p)
    subj_ref, subj_nest = unsmoothed["per_subject"], nested["per_subject"]
    common_s = sorted(set(subj_ref) & set(subj_nest))
    test = C.paired_wilcoxon([subj_ref[s]["AUC"] for s in common_s], [subj_nest[s]["AUC"] for s in common_s])
    return {"fixed_tau_sweep": sweep, "nested": {"chosen_tau_per_outer_subject": chosen,
                                                  "chosen_tau_values": sorted({v["tau"] for v in chosen.values()}),
                                                  "result": nested,
                                                  "vs_unsmoothed_per_subject_AUC": test}}, p_nested


def main():
    res, cache = {}, {}
    for ds in (C.load_seed(), C.load_dd()):
        r, pn = run(ds)
        res[ds.name] = r
        cache[ds.name.replace("-", "_")] = pn
        best_fixed = max(r["fixed_tau_sweep"].items(), key=lambda kv: kv[1]["pooled"]["AUC"])
        print(f"{ds.name}: unsmoothed AUC {r['fixed_tau_sweep']['0']['pooled']['AUC']:.2f}; best fixed tau "
              f"{best_fixed[0]} s AUC {best_fixed[1]['pooled']['AUC']:.2f}; nested AUC "
              f"{r['nested']['result']['pooled']['AUC']:.2f} (taus chosen {r['nested']['chosen_tau_values']})")
    np.savez_compressed(os.path.join(C.CACHES, "scores_tau_nested.npz"), **cache)
    C.write_result("tau_sweep", {"taus_s": TAUS, "smoother": "causal EMA, true time step, restart per recording",
                                 "selection": "inner LOSO on training subjects, max pooled AUC, ties to smaller tau",
                                 "results": res}, __file__)


if __name__ == "__main__":
    main()
