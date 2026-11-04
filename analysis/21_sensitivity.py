"""Sensitivity analyses for the supplementary material.

  S3  DD-Database label definition: pre-press window {60,120,180} s x alert
      gap {300,600,900} s (lean-10 LDA, LOSO).
  S4  DD-Database without the 1-40 Hz band-pass (features from unfiltered
      originals), since SEED-VIG cannot be re-filtered here.
  S9  Feature-set choice by nested LOSO (lean-10 vs lean-7 chosen on the
      training subjects only), to check that dropping coherence is not a
      test-set selection.

Output: results/sensitivity.json
"""
import os
import sys

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def summary(ds, p):
    r = C.evaluate(ds, p)
    return {"pooled_AUC": r["pooled"]["AUC"], "F1w": r["pooled"]["F1w"], "subject_AUC_median": r["subject_AUC_median"],
            "subjects_AUC_above_50": r["subjects_AUC_above_50"], "n_subjects": r["n_subjects"]}


def nested_feature_set(ds):
    sets = {"lean10": C.LEAN10, "lean7": C.LEAN7}
    Xn = {k: ds.calibrated(v) for k, v in sets.items()}
    p = np.full(len(ds.y), np.nan)
    chosen = {}
    for s in ds.test_subjects:
        inner = [h for h in ds.test_subjects if h != s]
        best, best_auc = None, -1
        for k in sets:
            pin = C.loso_scores(Xn[k], np.where(ds.subject == s, -1, ds.y), ds.subject, test_subjects=inner)
            mm = (ds.y >= 0) & np.isin(ds.subject, inner) & ~np.isnan(pin)
            auc = roc_auc_score(ds.y[mm], pin[mm])
            if auc > best_auc:
                best, best_auc = k, auc
        chosen[s] = best
        tr = (ds.y >= 0) & (ds.subject != s)
        te = ds.subject == s
        p[te] = C.lda().fit(Xn[best][tr], ds.y[tr]).predict_proba(Xn[best][te])[:, 1]
    return summary(ds, p), chosen


def main():
    res = {"S3_label_grid": {}, "S4_unfiltered": {}, "S9_nested_feature_set": {}}
    lab = np.load(os.path.join(C.CACHES, "dd_labels_v2.npz"))
    for key in sorted(k for k in lab.files if k.startswith("y_")):
        ds = C.load_dd(label_key=key)
        ds.test_subjects = [s for s in C.DD_SUBJECTS if len(np.unique(ds.y[(ds.subject == s) & (ds.y >= 0)])) == 2]
        p = C.loso_scores(ds.calibrated(C.LEAN10), ds.y, ds.subject, test_subjects=ds.test_subjects)
        res["S3_label_grid"][key[2:]] = summary(ds, p)
        print("S3", key[2:], res["S3_label_grid"][key[2:]])

    ds = C.load_dd()
    z = np.load(os.path.join(C.CACHES, "dd_features_v2.npz"))
    ds_u = C.Dataset("DD-Database (unfiltered)", z["X10u"].astype(float), ds.y, ds.subject, ds.recording, ds.t,
                     ds.test_subjects, ds.cal_sec)
    for name, d in (("filtered 1-40 Hz (primary)", ds), ("unfiltered", ds_u)):
        p = C.loso_scores(d.calibrated(C.LEAN10), d.y, d.subject, test_subjects=d.test_subjects)
        res["S4_unfiltered"][name] = summary(d, p)
        print("S4", name, res["S4_unfiltered"][name])

    for d in (C.load_seed(), C.load_dd()):
        r, chosen = nested_feature_set(d)
        res["S9_nested_feature_set"][d.name] = {"result": r, "chosen_per_outer_subject": chosen}
        print("S9", d.name, r, "chosen:", sorted(set(chosen.values())))
    C.write_result("sensitivity", res, __file__)


if __name__ == "__main__":
    main()
