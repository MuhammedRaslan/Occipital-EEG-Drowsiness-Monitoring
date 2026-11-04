"""How long labeled states last, and what the SEED-VIG opening window holds.

Label runs (context for the smoothing results). A run is a stretch of
consecutive labeled epochs (no gap longer than one epoch) with the same label
inside one recording. For each dataset and class: the number of runs, the
median run duration, and the epoch-weighted median (the run length that a
typical epoch belongs to).

SEED-VIG calibration windows. Features exist only for epochs with
PERCLOS outside 0.35-0.70, so the opening window of a recording is the first
60 s of its retained epochs, which need not start at t = 0. For each recording:
when the window starts, how many epochs it holds, and how many are drowsy. The
headline is repeated without the test drivers whose window starts late.

Output: results/label_runs.json
"""
import os
import sys

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def runs(ds):
    out = {0: [], 1: []}
    lab = ds.y >= 0
    for r in np.unique(ds.recording[lab]):
        idx = np.where(lab & (ds.recording == r))[0]
        idx = idx[np.argsort(ds.t[idx])]
        y, t = ds.y[idx], ds.t[idx]
        start = 0
        for i in range(1, len(idx) + 1):
            if i == len(idx) or y[i] != y[start] or t[i] - t[i - 1] > C.EPOCH_SEC:
                out[int(y[start])].append(float(t[i - 1] - t[start] + C.EPOCH_SEC))
                start = i
    res = {}
    for k, name in ((0, "alert"), (1, "drowsy")):
        a = np.asarray(out[k])
        w = np.repeat(a, (a / C.EPOCH_SEC).astype(int))
        res[name] = {"n_runs": int(len(a)), "median_run_s": float(np.median(a)),
                     "epoch_weighted_median_run_s": float(np.median(w))}
    return res


def seed_windows(ds):
    rows = {}
    for r in np.unique(ds.recording):
        m = ds.recording == r
        t = ds.t[m]
        w = t < t.min() + ds.cal_sec
        rows[str(r)] = {"subject": str(ds.subject[m][0]), "first_retained_s": float(t.min()),
                        "n_epochs_in_window": int(w.sum()), "n_drowsy_in_window": int(ds.y[m][w].sum())}
    late = {k: v for k, v in rows.items() if v["first_retained_s"] > 0}
    late_test = sorted({v["subject"] for v in late.values()} & {str(s) for s in ds.test_subjects})
    p = C.loso_scores(ds.calibrated(C.LEAN10), ds.y, ds.subject, test_subjects=ds.test_subjects)
    keep = [s for s in ds.test_subjects if str(s) not in late_test]
    m = np.isin(ds.subject, keep)
    aucs = [100 * roc_auc_score(ds.y[ds.subject == s], p[ds.subject == s]) for s in keep]
    return {"per_recording": rows, "n_recordings": len(rows),
            "late_start_recordings": sorted(late, key=lambda k: late[k]["first_retained_s"]),
            "late_start_s": sorted(v["first_retained_s"] for v in late.values()),
            "all_drowsy_window_subjects": sorted((v["subject"] for v in rows.values()
                                                  if v["n_drowsy_in_window"] == v["n_epochs_in_window"]), key=int),
            "n_windows_under_6_epochs": sum(v["n_epochs_in_window"] < 6 for v in rows.values()),
            "late_start_test_subjects": late_test,
            "without_late_test_subjects": {"n_subjects": len(keep), "pooled_AUC": 100 * roc_auc_score(ds.y[m], p[m]),
                                           "subject_AUC_median": float(np.median(aucs))}}


def main():
    seed, dd = C.load_seed(), C.load_dd()
    res = {ds.name: runs(ds) for ds in (seed, dd)}
    for d, v in res.items():
        print(d, {k: (x["n_runs"], x["median_run_s"], x["epoch_weighted_median_run_s"]) for k, x in v.items()})
    win = seed_windows(seed)
    print({k: v for k, v in win.items() if k != "per_recording"})
    C.write_result("label_runs", {"definition": "consecutive labeled epochs with the same label, no gap > 10 s",
                                  "results": res, "seed_calibration_windows": win}, __file__)


if __name__ == "__main__":
    main()
