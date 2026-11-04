"""Prepare SEED-VIG from the cached lean features.

The cache (features_seed_vig_cache.npz) holds the 10 lean features of every
epoch whose mean PERCLOS is < 0.35 (awake, 0) or > 0.70 (drowsy, 1); the
recordings were processed file by file in sorted-filename order. Two subject
identifiers (4 and 5) have two recordings each. Their rows are contiguous and
the second recording starts where time_s resets, so each recording gets its
own identifier here and its own label-free calibration window. Recordings
sharing a subject identifier stay together in LOSO (conservative: the dataset
paper reports 23 subjects, the files use 21 identifiers).

Outputs: caches/seed_v2.npz, results/seed_prepare.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def main():
    z = np.load(C.SEED_CACHE, allow_pickle=True)
    names = [str(c) for c in z["feat_names"]]
    X = z["X"].astype(float)[:, [names.index(n) for n in C.LEAN]]
    y = z["y"].astype(int)
    subj = np.asarray(z["subject"]).astype(str)
    t = np.asarray(z["time_s"]).astype(float)

    rec = np.empty(len(y), dtype=object)
    splits = {}
    for s in np.unique(subj):
        idx = np.where(subj == s)[0]
        assert np.all(np.diff(idx) == 1), f"rows of subject {s} are not contiguous"
        resets = np.where(np.diff(t[idx]) < 0)[0]
        bounds = np.r_[0, resets + 1, len(idx)]
        for k in range(len(bounds) - 1):
            rec[idx[bounds[k]:bounds[k + 1]]] = f"{s}" if len(bounds) == 2 else f"{s}-{k + 1}"
        if len(resets):
            splits[s] = np.diff(bounds).tolist()
    rec = rec.astype(str)

    # Reproduction check: the published SEED-VIG internal LOSO (Table V) used
    # first-60-s calibration per subject identifier, i.e. without the split.
    Xn_unsplit = C.zscore_by_recording(X, subj, t, C.SEED_CAL_SEC)
    both = [s for s in np.unique(subj) if len(np.unique(y[subj == s])) == 2]
    p = C.loso_scores(Xn_unsplit, y, subj, test_subjects=both)
    m = ~np.isnan(p)
    repro = C.metrics(y[m], p[m])
    assert abs(repro["F1w"] - 71.25) < 0.01 and abs(repro["AUC"] - 70.98) < 0.01, repro

    np.savez_compressed(os.path.join(C.CACHES, "seed_v2.npz"), X=X, y=y, subject=subj, recording=rec, t=t)
    counts = {s: {"n_awake": int(((subj == s) & (y == 0)).sum()), "n_drowsy": int(((subj == s) & (y == 1)).sum())}
              for s in sorted(np.unique(subj), key=int)}
    C.write_result("seed_prepare", {
        "n_epochs": int(len(y)), "n_awake": int((y == 0).sum()), "n_drowsy": int((y == 1).sum()),
        "n_subject_ids": int(len(np.unique(subj))), "n_recordings": int(len(np.unique(rec))),
        "split_subjects_rows": splits,
        "subject_ids_with_both_classes": sorted(both, key=int), "n_test_subjects": len(both),
        "single_class_subject_ids": sorted([s for s in np.unique(subj) if s not in both], key=int),
        "per_subject_counts": counts,
        "reproduction_check_published_internal_loso": repro,
        "note": C.SEED_DIR_NOTE,
    }, __file__)


if __name__ == "__main__":
    main()
