"""Cross-dataset transfer in both directions.

Train shrinkage LDA on all labelled epochs of one dataset, test on the other,
with each dataset's own label-free calibration. AUC measures whether the
ranking transfers; F1 at threshold 0.5 measures whether the decision
threshold transfers. Both lean-10 and lean-7 (no coherence) are reported.

It also varies the length of the label-free calibration window (60, 120 and
300 s), one dataset at a time while the other keeps its standard window
(SEED-VIG 60 s, DD-Database 300 s), for the lean-10 LDA within each dataset
(LOSO) and across datasets.

Output: results/cross_dataset.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

WINDOWS_S = (60, 120, 300)


def summary(r):
    return {"pooled_AUC": r["pooled"]["AUC"], "BalAcc": r["pooled"]["BalAcc"],
            "subject_AUC_median": r["subject_AUC_median"],
            "subjects_AUC_above_50": r["subjects_AUC_above_50"], "n_subjects": r["n_subjects"]}


def window_sensitivity(seed, dd):
    out = {}
    for ds in (seed, dd):
        for w in WINDOWS_S:
            p = C.loso_scores(ds.calibrated(C.LEAN10, cal_sec=w), ds.y, ds.subject, test_subjects=ds.test_subjects)
            out[f"{ds.name} LOSO | {ds.name} window {w} s"] = summary(C.evaluate(ds, p))
    for varied in (dd, seed):
        for w in WINDOWS_S:
            Xd = dd.calibrated(C.LEAN10, cal_sec=w if varied is dd else None)
            Xs = seed.calibrated(C.LEAN10, cal_sec=w if varied is seed else None)
            for a, Xa, b, Xb in ((dd, Xd, seed, Xs), (seed, Xs, dd, Xd)):
                m = a.y >= 0
                p = C.lda().fit(Xa[m], a.y[m]).predict_proba(Xb)[:, 1]
                out[f"{a.name} -> {b.name} | {varied.name} window {w} s"] = summary(C.evaluate(b, p))
    for k, v in out.items():
        print(f"{k:58} AUC {v['pooled_AUC']:6.2f}  BalAcc {v['BalAcc']:6.2f}  median subj AUC {v['subject_AUC_median']:5.1f}")
    return out


def main():
    seed, dd = C.load_seed(), C.load_dd()
    res = {}
    for fs_name, cols in (("lean10", C.LEAN10), ("lean7", C.LEAN7)):
        Xs, Xd = seed.calibrated(cols), dd.calibrated(cols)
        for src, Xa, tgt, Xb in (("DD-Database", Xd, "SEED-VIG", Xs), ("SEED-VIG", Xs, "DD-Database", Xd)):
            a = dd if src == "DD-Database" else seed
            b = seed if tgt == "SEED-VIG" else dd
            m = a.y >= 0
            p = C.lda().fit(Xa[m], a.y[m]).predict_proba(Xb)[:, 1]
            r = C.evaluate(b, p)
            r.pop("bootstrap", None)
            res[f"{fs_name}: {src} -> {tgt}"] = r
            print(f"{fs_name}: {src:11} -> {tgt:11} AUC {r['pooled']['AUC']:6.2f}  F1w {r['pooled']['F1w']:6.2f}  "
                  f"BalAcc {r['pooled']['BalAcc']:6.2f}  median subj AUC {r['subject_AUC_median']:5.1f} "
                  f"({r['subjects_AUC_above_50']}/{r['n_subjects']} > 50)")
    C.write_result("cross_dataset", {"note": "no fine-tuning; each dataset uses its own label-free calibration",
                                     "results": res, "calibration_window_s": list(WINDOWS_S),
                                     "calibration_window_sensitivity": window_sensitivity(seed, dd)}, __file__)


if __name__ == "__main__":
    main()
