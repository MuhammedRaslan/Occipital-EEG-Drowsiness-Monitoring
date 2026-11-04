"""Calibration sensitivity, including a driver who is already drowsy.

Training subjects keep the standard label-free calibration. Only the held-out
subject's calibration window is moved:

  SEED-VIG (60-s windows): opening 60 s (standard); 60 s starting at 30 min;
      60 s starting at 60 min; the first six drowsy-labelled epochs
      (a driver who is drowsy while calibrating).
  DD-Database (300-s windows): opening 300 s (standard); 300 s starting at
      30 min; 300 s starting at 60 min; the 300 s ending at the first
      genuine button press after 300 s (calibrating during reported drowsiness).
A driver with too few retained epochs in a moved window keeps the standard one;
the JSON records how many drivers used the moved window. Also scores the two
DD-Database trials in which a driver really pressed during calibration.

Output: results/calibration.json
"""
import json
import os
import sys

import mne
import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

mne.set_log_level("ERROR")


def z_on(X, sel):
    sd = X[sel].std(0)
    sd[sd == 0] = 1.0
    return (X - X[sel].mean(0)) / sd


def first_press_after(subj_trial):
    s, tr = subj_trial.split("_")
    on = np.sort(mne.read_annotations(os.path.join(C.DD_DIR, f"{s}_{tr}_annotations.edf")).onset)
    on = on[on > C.DD_CAL_SEC]
    return float(on[0]) if len(on) else None


def window_mask(ds, rec_mask, variant):
    t = ds.t[rec_mask]
    w = ds.cal_sec
    if variant == "standard":
        return t < t.min() + w
    if variant.startswith("at_"):
        start = float(variant[3:])
        sel = (t >= start) & (t < start + w)
        return sel if sel.sum() >= 3 else None
    if variant == "drowsy_labelled":
        yy = ds.y[rec_mask]
        idx = np.where(yy == 1)[0]
        if len(idx) < 3:
            return None
        idx = idx[np.argsort(t[idx])][:6]
        sel = np.zeros(len(t), bool)
        sel[idx] = True
        return sel
    if variant == "before_first_press":
        tp = first_press_after(ds.recording[rec_mask][0])
        if tp is None:
            return None
        sel = (t >= tp - w) & (t < tp)
        return sel if sel.sum() >= 3 else None
    raise ValueError(variant)


def run(ds, variants, cols):
    base = ds.calibrated(cols)
    out = {}
    for v in variants:
        p = np.full(len(ds.y), np.nan)
        used = 0
        for s in ds.test_subjects:
            te = ds.subject == s
            tr = (ds.y >= 0) & ~te
            clf = C.lda().fit(base[tr], ds.y[tr])
            Xte = np.empty((te.sum(), len(cols)))
            ok = True
            recs = np.unique(ds.recording[te])
            te_idx = np.where(te)[0]
            for r in recs:
                rm = ds.recording[te_idx] == r
                sel = window_mask(ds, ds.recording == r, v)
                if sel is None:
                    sel = window_mask(ds, ds.recording == r, "standard")
                    ok = False
                Xte[rm] = z_on(ds.X[ds.recording == r][:, cols], sel)
            used += ok
            p[te] = clf.predict_proba(Xte)[:, 1]
        r = C.evaluate(ds, p)
        out[v] = {"pooled": r["pooled"], "subject_AUC_median": r["subject_AUC_median"],
                  "subjects_with_variant_window": used, "n_subjects": len(ds.test_subjects)}
    return out


def presses_during_calibration(ds):
    """The real cases: a driver pressed the button inside the calibration window.

    Scores those DD-Database trials and the same driver's other trial with the
    standard calibration. A trial with one labeled class has no AUC.
    """
    with open(os.path.join(C.RESULTS, "dd_labels.json"), encoding="utf-8") as f:
        trials = json.load(f)["per_trial"]
    p = C.loso_scores(ds.calibrated(C.LEAN10), ds.y, ds.subject, test_subjects=ds.test_subjects)

    def score(key):
        m = (ds.recording == key) & (ds.y >= 0)
        y = ds.y[m]
        return {"trial": key, "n_drowsy": int(y.sum()), "n_alert": int((y == 0).sum()),
                "AUC": 100 * roc_auc_score(y, p[m]) if len(np.unique(y)) == 2 else None}

    out = []
    for key, v in trials.items():
        if v["presses_inside_calibration_window"]:
            s, tr = key.split("_")
            out.append({"press_s": v["presses_inside_calibration_window"], "this_trial": score(key),
                        "other_trial": score(f"{s}_{3 - int(tr)}")})
    return out


def main():
    res = {}
    for ds, variants in ((C.load_seed(), ["standard", "at_1800", "at_3600", "drowsy_labelled"]),
                         (C.load_dd(), ["standard", "at_1800", "at_3600", "before_first_press"])):
        res[ds.name] = {}
        for fs_name, cols in (("lean10", C.LEAN10), ("lean7", C.LEAN7)):
            res[ds.name][fs_name] = run(ds, variants, cols)
            for v, r in res[ds.name][fs_name].items():
                print(f"{ds.name:12} {fs_name:6} {v:20} AUC {r['pooled']['AUC']:6.2f}  F1w {r['pooled']['F1w']:6.2f}  "
                      f"BalAcc {r['pooled']['BalAcc']:6.2f}  median subj AUC {r['subject_AUC_median']:5.1f}  "
                      f"({r['subjects_with_variant_window']}/{r['n_subjects']} used the variant window)")
    real = presses_during_calibration(C.load_dd())
    print("presses inside a calibration window:", real)
    C.write_result("calibration", {"note": "training subjects keep the standard calibration; only the held-out "
                                           "subject's window moves", "results": res,
                                   "dd_presses_during_calibration": real}, __file__)


if __name__ == "__main__":
    main()
