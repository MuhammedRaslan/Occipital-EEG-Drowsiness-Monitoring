"""Subject-independent monitoring on both datasets.

Primary pipeline (pre-specified in the reviewed paper): the 10 lean features,
shrinkage LDA, label-free calibration. Reported alongside it:
  * feature families and leave-one-family-out sets (incl. "no coherence");
  * on the DD-Database, the published 50-feature extended set and its families;
  * other classifiers on the same lean features, with fixed hyperparameters.
Every alternative is compared with the primary pipeline on per-subject AUC
(paired Wilcoxon, Holm-adjusted within each dataset).

Outputs: results/monitoring.json, caches/scores_v2.npz
"""
import os
import sys

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

FAM = C.FAMILIES
LEAN_SETS = {
    "lean10": C.LEAN10,
    "no_COH (lean7)": C.LEAN7,
    "no_ENT": [i for i in C.LEAN10 if i not in FAM["ENT"]],
    "no_SLOPE": [i for i in C.LEAN10 if i not in FAM["SLOPE"]],
    "no_PAF": [i for i in C.LEAN10 if i not in FAM["PAF"]],
    "ENT_only": FAM["ENT"], "SLOPE_only": FAM["SLOPE"], "PAF_only": FAM["PAF"], "COH_only": FAM["COH"],
}
CLASSIFIERS = {
    "LogReg": lambda: LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced"),
    "RandomForest": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=0, n_jobs=-1),
    "GradBoost": lambda: GradientBoostingClassifier(random_state=0),
}


def ext_families(cols):
    def idx(pred):
        return [i for i, c in enumerate(cols) if pred(c)]
    dwt = idx(lambda c: c.startswith("dwt_"))
    ent = idx(lambda c: c.startswith(("sample_entropy", "perm_entropy")))
    slope = idx(lambda c: c.startswith("aperiodic_slope"))
    paf = idx(lambda c: c == "paf_delta")
    coh = idx(lambda c: c.startswith("coh_"))
    base = [i for i in range(len(cols)) if i not in dwt + ent + slope + paf + coh]
    assert len(base) == 30 and len(dwt) == 10 and len(cols) == 50
    return {"ext50": list(range(50)), "ext50_no_COH": [i for i in range(50) if i not in coh],
            "BASE30_only": base, "DWT10_only": dwt}


def run_dataset(ds, include_ext):
    out = {"configs": {}, "comparisons_vs_lean10_LDA": {}}
    scores = {}
    subj_auc = {}

    def add(name, p):
        r = C.evaluate(ds, p)
        out["configs"][name] = r
        subj_auc[name] = r["per_subject"]
        scores[name] = p

    for name, cols in LEAN_SETS.items():
        add(f"LDA | {name}", C.loso_scores(ds.calibrated(cols), ds.y, ds.subject, test_subjects=ds.test_subjects))
    for cname, mk in CLASSIFIERS.items():
        add(f"{cname} | lean10", C.loso_scores(ds.calibrated(C.LEAN10), ds.y, ds.subject, make_model=mk,
                                                test_subjects=ds.test_subjects))
    if include_ext:
        for name, cols in ext_families(ds.ext_cols).items():
            add(f"LDA | {name}", C.loso_scores(ds.calibrated(cols, ext=True), ds.y, ds.subject,
                                               test_subjects=ds.test_subjects))

    ref = subj_auc["LDA | lean10"]
    names = [n for n in subj_auc if n != "LDA | lean10"]
    tests = {}
    for n in names:
        common_s = sorted(set(ref) & set(subj_auc[n]))
        tests[n] = C.paired_wilcoxon([ref[s]["AUC"] for s in common_s], [subj_auc[n][s]["AUC"] for s in common_s])
    adj = C.holm([tests[n]["p_two_sided"] for n in names])
    for n, a in zip(names, adj):
        tests[n]["p_holm"] = a
    out["comparisons_vs_lean10_LDA"] = tests
    return out, scores


def main():
    seed, dd = C.load_seed(), C.load_dd()
    res, cache = {}, {}
    for ds, ext in ((seed, False), (dd, True)):
        r, sc = run_dataset(ds, ext)
        res[ds.name] = r
        for k in ("LDA | lean10", "LDA | no_COH (lean7)"):
            cache[f"{ds.name}|{k}"] = sc[k]
        p = r["configs"]["LDA | lean10"]
        print(f"{ds.name}: lean10 LDA pooled AUC {p['pooled']['AUC']:.2f} F1w {p['pooled']['F1w']:.2f} "
              f"| median subject AUC {p['subject_AUC_median']:.1f} | "
              f"lean7 AUC {r['configs']['LDA | no_COH (lean7)']['pooled']['AUC']:.2f}")
    np.savez_compressed(os.path.join(C.CACHES, "scores_v2.npz"),
                        **{k.replace(" ", "_").replace("|", "").replace("(", "").replace(")", ""): v
                           for k, v in cache.items()})
    C.write_result("monitoring", {
        "primary_pipeline": "lean-10 features, shrinkage LDA (lsqr, Ledoit-Wolf), label-free calibration",
        "calibration": {"SEED-VIG": "first 60 s of each recording", "DD-Database": "first 300 s of each trial"},
        "classifier_hyperparameters": "fixed a priori: LogReg C=1 balanced; RF 300 trees min_leaf 5; GB sklearn defaults",
        "results": res}, __file__)


if __name__ == "__main__":
    main()
