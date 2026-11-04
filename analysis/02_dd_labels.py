"""Drowsiness labels for the DD-Database from the drivers' own reports.

The DD-Database protocol asked volunteers to press an event button when they
felt drowsy. Each trial's annotation file starts with exactly one press in
its first 20 s (3-20 s in every trial), which is treated as a start marker.
All later presses ("genuine presses", onset >= 60 s) are self-reports.

Primary definition (fixed before evaluation):
  * calibration window: the first 300 s of each trial carries no label;
  * drowsy: an epoch that starts within PRE seconds before a genuine press
    (PRE = 120 s);
  * alert: an epoch at least GAP seconds from every genuine press
    (GAP = 600 s);
  * everything else is unlabelled (-1).
A grid of PRE x GAP values is written for the sensitivity analysis (S3).

Outputs: caches/dd_labels_v2.npz, results/dd_labels.json
"""
import os
import sys

import mne
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

mne.set_log_level("ERROR")
PRIMARY = (120, 600)
GRID_PRE = (60, 120, 180)
GRID_GAP = (300, 600, 900)
START_MARKER_MAX_S = 60


def presses(subj, trial):
    on = np.sort(np.asarray(mne.read_annotations(
        os.path.join(C.DD_DIR, f"{subj}_{trial}_annotations.edf")).onset, dtype=float))
    marker = on[on < START_MARKER_MAX_S]
    return marker, on[on >= START_MARKER_MAX_S]


def label(t, genuine, pre, gap):
    y = np.full(len(t), -1, dtype=int)
    for i, ti in enumerate(t):
        if ti < C.DD_CAL_SEC:
            continue
        if len(genuine) and np.any((genuine >= ti) & (genuine - ti <= pre)):
            y[i] = 1
        elif len(genuine) == 0 or np.min(np.abs(genuine - ti)) >= gap:
            y[i] = 0
    return y


def main():
    z = np.load(os.path.join(C.CACHES, "dd_features_v2.npz"), allow_pickle=True)
    subj, trial, t = z["subject"], z["trial"], z["t"]
    info, grid = {}, {}
    ylab = {f"{p}_{g}": np.full(len(t), -1, dtype=int) for p in GRID_PRE for g in GRID_GAP}
    for s in C.DD_SUBJECTS:
        for tr in (1, 2):
            marker, genuine = presses(s, tr)
            assert len(marker) == 1, (s, tr, marker)
            m = (subj == s) & (trial == tr)
            for key in ylab:
                p, g = map(int, key.split("_"))
                ylab[key][m] = label(t[m], genuine, p, g)
            yp = ylab[f"{PRIMARY[0]}_{PRIMARY[1]}"][m]
            info[f"{s}_{tr}"] = {
                "start_marker_s": float(marker[0]), "n_genuine_presses": int(len(genuine)),
                "presses_inside_calibration_window": [float(x) for x in genuine[genuine < C.DD_CAL_SEC]],
                "n_drowsy": int((yp == 1).sum()), "n_alert": int((yp == 0).sum()),
                "n_unlabelled": int((yp == -1).sum()),
            }
    for key, y in ylab.items():
        grid[key] = {"n_drowsy": int((y == 1).sum()), "n_alert": int((y == 0).sum()),
                     "subjects_with_both_classes": int(sum(
                         len(np.unique(y[(subj == s) & (y >= 0)])) == 2 for s in C.DD_SUBJECTS))}
    y = ylab[f"{PRIMARY[0]}_{PRIMARY[1]}"]
    per_subject = {s: {"n_drowsy": int(((subj == s) & (y == 1)).sum()),
                       "n_alert": int(((subj == s) & (y == 0)).sum())} for s in C.DD_SUBJECTS}

    # Reproduction check: the 14 Oct probe counted presses after 300 s only and
    # labelled 7,965 epochs (5,158 drowsy). Re-derive that variant here.
    yr = np.full(len(t), -1, dtype=int)
    for s in C.DD_SUBJECTS:
        for tr in (1, 2):
            _, genuine = presses(s, tr)
            m = (subj == s) & (trial == tr)
            yr[m] = label(t[m], genuine[genuine > 300], 120, 600)
    repro = {"labelled": int((yr >= 0).sum()), "drowsy": int((yr == 1).sum())}
    assert repro == {"labelled": 7965, "drowsy": 5158}, repro

    np.savez_compressed(os.path.join(C.CACHES, "dd_labels_v2.npz"), y=y,
                        **{f"y_{k}": v for k, v in ylab.items()})
    C.write_result("dd_labels", {
        "definition": {"calibration_window_s": C.DD_CAL_SEC, "start_marker_below_s": START_MARKER_MAX_S,
                       "drowsy_pre_press_window_s": PRIMARY[0], "alert_min_gap_s": PRIMARY[1]},
        "totals": {"n_drowsy": int((y == 1).sum()), "n_alert": int((y == 0).sum()),
                   "n_unlabelled": int((y == -1).sum())},
        "per_subject": per_subject, "per_trial": info, "sensitivity_grid": grid,
        "reproduction_check_probe_variant": repro,
    }, __file__)


if __name__ == "__main__":
    main()
