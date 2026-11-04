"""Alarm-level evaluation and the time-on-task check (exploratory).

1. Time on task. Drowsiness grows with time on task, so a clock alone may
   separate the labels. For each driver, the AUC of the time since the start
   of the recording is set beside the AUC of the lean-10 LDA, without
   smoothing and with the nested EMA, on both datasets.

2. Alarms (DD-Database only; the SEED-VIG timeline has gaps). After the
   calibration window, an alarm fires when the score is above a threshold,
   and fires again every 120 s while it stays there, so an alarm that never
   switches off is charged for every interval. A self-report counts as
   detected when an alarm fires in the 120 s before the press. A false
   alarm is one that fires in an alert-labeled epoch, and the rate is per
   hour of alert-labeled time. For each held-out driver the threshold is
   set on the out-of-sample scores of the other nine drivers (an inner LOSO,
   with the outer fold's time constant), to the highest hit rate whose false
   alarms stay at or below the target rate. The same is done for a trivial
   alarm whose score is the time on task.

Output: results/alarms.json
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
PRE_S = 120
REFIRE_S = 120
TARGETS_PER_H = (1.0, 2.0)


def chosen_taus(name):
    with open(os.path.join(C.RESULTS, "tau_sweep.json"), encoding="utf-8") as f:
        ch = json.load(f)["results"][name]["nested"]["chosen_tau_per_outer_subject"]
    return {s: v["tau"] for s, v in ch.items()}


def time_on_task(ds, p_raw, p_ema):
    out = {}
    for s in ds.test_subjects:
        m = (ds.subject == s) & (ds.y >= 0)
        y = ds.y[m]
        if len(np.unique(y)) < 2:
            continue
        out[s] = {"time": 100 * roc_auc_score(y, ds.t[m]), "eeg": 100 * roc_auc_score(y, p_raw[m]),
                  "eeg_ema": 100 * roc_auc_score(y, p_ema[m])}
    keys = sorted(out)
    summary = {k: float(np.median([out[s][k] for s in keys])) for k in ("time", "eeg", "eeg_ema")}
    summary["time_above_50"] = int(sum(out[s]["time"] > 50 for s in keys))
    summary["eeg_beats_time"] = int(sum(out[s]["eeg"] > out[s]["time"] for s in keys))
    summary["eeg_ema_beats_time"] = int(sum(out[s]["eeg_ema"] > out[s]["time"] for s in keys))
    summary["eeg_vs_time"] = C.paired_wilcoxon([out[s]["time"] for s in keys], [out[s]["eeg"] for s in keys])
    summary["eeg_ema_vs_time"] = C.paired_wilcoxon([out[s]["time"] for s in keys], [out[s]["eeg_ema"] for s in keys])
    summary["n"] = len(keys)
    return {"per_driver": out, "summary": summary}


def presses(recording):
    s, tr = recording.split("_")
    on = np.sort(np.asarray(mne.read_annotations(
        os.path.join(C.DD_DIR, f"{s}_{tr}_annotations.edf")).onset, dtype=float))
    return on[on >= C.DD_CAL_SEC]  # presses outside the calibration window (the start marker is < 60 s)


def events(ds, score, theta, recs, press):
    """Hits, presses, false alarms and alert hours over the given recordings."""
    hits = n_press = fa = 0
    alert_h = 0.0
    for r in recs:
        idx = np.where(ds.recording == r)[0]
        idx = idx[np.argsort(ds.t[idx])]
        t, y, sc = ds.t[idx], ds.y[idx], score[idx]
        fires, last = [], -np.inf
        for k in np.flatnonzero((sc > theta) & (t >= C.DD_CAL_SEC)):
            if t[k] - last >= REFIRE_S:
                fires.append(k)
                last = t[k]
        fires = np.asarray(fires, dtype=int)
        fa += int((y[fires] == 0).sum())
        alert_h += (y == 0).sum() * C.EPOCH_SEC / 3600
        ft = t[fires]
        for P in press[r]:
            n_press += 1
            hits += bool(np.any((ft >= P - PRE_S) & (ft < P)))
    return hits, n_press, fa, alert_h


def pick_threshold(ds, score, recs, press, target):
    cand = np.unique(np.quantile(score[np.isin(ds.recording, recs)], np.linspace(0.0, 0.999, 400)))
    best = (None, -1.0)
    for theta in cand:
        h, n, fa, ah = events(ds, score, theta, recs, press)
        if ah > 0 and fa / ah <= target and n and h / n > best[1]:
            best = (float(theta), h / n)
    return best[0] if best[0] is not None else float(np.max(score[np.isin(ds.recording, recs)]))


def alarms(ds, Xn, taus):
    press = {r: presses(r) for r in np.unique(ds.recording)}
    out = {}
    for target in TARGETS_PER_H:
        rows = {"time on task": [], "EEG": [], "EEG + EMA": []}
        for s in ds.test_subjects:
            others = [h for h in ds.test_subjects if h != s]
            recs_s = sorted(np.unique(ds.recording[ds.subject == s]))
            recs_o = sorted(np.unique(ds.recording[np.isin(ds.subject, others)]))
            outer = C.lda().fit(Xn[(ds.y >= 0) & (ds.subject != s)], ds.y[(ds.y >= 0) & (ds.subject != s)])
            p_out = np.full(len(ds.y), np.nan)
            p_out[ds.subject == s] = outer.predict_proba(Xn[ds.subject == s])[:, 1]
            p_in = np.full(len(ds.y), np.nan)
            for h in others:
                tr = (ds.y >= 0) & (ds.subject != s) & (ds.subject != h)
                p_in[ds.subject == h] = C.lda().fit(Xn[tr], ds.y[tr]).predict_proba(Xn[ds.subject == h])[:, 1]
            tau = taus[s]
            scores = {"time on task": (ds.t, ds.t), "EEG": (p_in, p_out),
                      "EEG + EMA": (C.smooth_by_recording(p_in, ds.t, ds.recording, tau),
                                    C.smooth_by_recording(p_out, ds.t, ds.recording, tau))}
            for name, (inner, test) in scores.items():
                theta = pick_threshold(ds, inner, recs_o, press, target)
                h, n, fa, ah = events(ds, test, theta, recs_s, press)
                rows[name].append({"driver": s, "hits": h, "presses": n, "false_alarms": fa, "alert_h": ah})
        out[f"{target:g} per hour"] = {}
        for name, rr in rows.items():
            H, N = sum(r["hits"] for r in rr), sum(r["presses"] for r in rr)
            FA, AH = sum(r["false_alarms"] for r in rr), sum(r["alert_h"] for r in rr)
            out[f"{target:g} per hour"][name] = {
                "hit_rate": 100 * H / N, "false_alarms_per_h": FA / AH, "hits": H, "presses": N,
                "per_driver_hit_rate": {r["driver"]: (100 * r["hits"] / r["presses"] if r["presses"] else None) for r in rr},
                "per_driver_false_alarms_per_h": {r["driver"]: (r["false_alarms"] / r["alert_h"] if r["alert_h"] else None) for r in rr}}
            v = out[f"{target:g} per hour"][name]
            print(f"target {target:g}/h  {name:13} hits {v['hit_rate']:5.1f}% ({H}/{N})  false alarms {v['false_alarms_per_h']:.2f}/h")
    return out


def main():
    res = {"rules": {"pre_press_window_s": PRE_S, "refire_s": REFIRE_S, "targets_per_h": list(TARGETS_PER_H),
                     "threshold": "set on inner-LOSO scores of the other drivers"}}
    for ds in (C.load_seed(), C.load_dd()):
        Xn = ds.calibrated(C.LEAN10)
        p = C.loso_scores(Xn, ds.y, ds.subject, test_subjects=ds.test_subjects)
        taus = chosen_taus(ds.name)
        p_ema = np.full(len(ds.y), np.nan)
        for s in ds.test_subjects:
            m = ds.subject == s
            p_ema[m] = C.smooth_by_recording(p, ds.t, ds.recording, taus[s])[m]
        tot = time_on_task(ds, p, p_ema)
        sm = tot["summary"]
        print(f"{ds.name}: median AUC time {sm['time']:.1f}, EEG {sm['eeg']:.1f}, EEG+EMA {sm['eeg_ema']:.1f}; "
              f"EEG beats time in {sm['eeg_beats_time']}/{sm['n']} (p={sm['eeg_vs_time']['p_two_sided']:.3f}), "
              f"EEG+EMA in {sm['eeg_ema_beats_time']}/{sm['n']} (p={sm['eeg_ema_vs_time']['p_two_sided']:.3f})")
        res[ds.name] = {"time_on_task": tot}
        if ds.name == "DD-Database":
            res[ds.name]["alarms"] = alarms(ds, Xn, taus)
    C.write_result("alarms", res, __file__)


if __name__ == "__main__":
    main()
