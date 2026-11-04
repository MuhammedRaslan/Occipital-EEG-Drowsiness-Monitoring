"""Per-subject ROC curves, precision and recall.

Uses the LOSO scores of the primary pipeline (lean-10 LDA) and the no-
coherence variant, saved by 10_monitoring.py. Writes per-subject ROC curves
(downsampled to 60 points) and the per-subject table for Fig. 3 / Table S1.

Output: results/per_subject.json
"""
import os
import sys

import numpy as np
from sklearn.metrics import roc_curve

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

KEYS = {"lean10": "LDA__lean10", "lean7": "LDA__no_COH_lean7"}


def curve(y, p, n=60):
    fpr, tpr, _ = roc_curve(y, p)
    grid = np.linspace(0, 1, n)
    return {"fpr": grid.tolist(), "tpr": np.interp(grid, fpr, tpr).tolist()}


def main():
    sc = np.load(os.path.join(C.CACHES, "scores_v2.npz"), allow_pickle=True)
    res = {}
    for ds in (C.load_seed(), C.load_dd()):
        res[ds.name] = {}
        for fs_name, key in KEYS.items():
            p = sc[f"{ds.name}{key}"]
            m = (ds.y >= 0) & np.isin(ds.subject, ds.test_subjects) & ~np.isnan(p)
            curves = {s: curve(ds.y[m & (ds.subject == s)], p[m & (ds.subject == s)]) for s in ds.test_subjects
                      if len(np.unique(ds.y[m & (ds.subject == s)])) == 2}
            res[ds.name][fs_name] = {"pooled_curve": curve(ds.y[m], p[m]), "subject_curves": curves,
                                     "per_subject": C.per_subject(ds.y[m], p[m], ds.subject[m])}
        rows = res[ds.name]["lean10"]["per_subject"]
        weak = {s: round(v["AUC"], 1) for s, v in rows.items() if v["AUC"] < 55}
        print(f"{ds.name}: {len(rows)} subjects; AUC < 55: {weak}")
    C.write_result("per_subject", {"pipelines": {"lean10": "lean-10 LDA", "lean7": "lean-7 (no coherence) LDA"},
                                   "results": res}, __file__)


if __name__ == "__main__":
    main()
