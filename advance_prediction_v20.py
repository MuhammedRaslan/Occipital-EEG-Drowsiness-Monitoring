"""
Advance Prediction v2 (Phase 7e, v20)
======================================
Re-evaluates the "EEG flags drowsiness before the camera" claim under three
corrections to v13:

  (1) OPERATING-POINT SWEEP
      v13 used a single (threshold=0.5, dwell=30s) point. We sweep
      (threshold × dwell) and report the lead-time distribution at
      every point, so we can pick the deployment operating point
      honestly from the Pareto front of (positive-lead rate, FPR).

  (3) PER-SUBJECT CALIBRATED THRESHOLD
      v13's global threshold=0.5 ignores the fact that each driver's
      p(drowsy) has its own awake-baseline mean/std. We use the first
      60 s of each session's EEG p(drowsy) (definitionally awake by the
      SEED-VIG protocol — subjects were instructed to start alert) to
      estimate baseline μ_awake, σ_awake per driver, and flag when the
      smoothed posterior exceeds μ_awake + k σ_awake. k is swept too.

  (4) SURVIVAL-ANALYSIS FRAMING
      v13 dropped every subject where either behavioural OR EEG onset
      was never detected. That silently threw out the best evidence:
      if EEG flags while PERCLOS never reaches 0.70, we CAN NOT
      conclude "no lead" — we have a censored win. We now report:
        * n_eeg_only       — EEG onset, no behavioural onset: censored positive lead
        * n_behav_only     — behavioural onset, no EEG onset: censored negative
        * n_both           — both detected: true observed lead
        * n_neither        — neither: non-informative
      Median / mean lead are reported on the BOTH set (same as v13, honest),
      plus a separate "proactive-rate" = (n_both_positive + n_eeg_only) /
      n_informative, which is the realistic deployment metric:
      *what fraction of sessions does EEG flag drowsiness at or before
      the camera would?*

Output: publication_results_v20.json
"""

import os, sys, io, json, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import scipy.io as sio
from datetime import datetime
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SEED_DIR     = r"c:/Users/muham/OneDrive/Documents/#1_DMS/SEED-VIG"
LBL_DIR      = os.path.join(SEED_DIR, "perclos_labels")
SEED_CACHE   = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v20.json")

EPOCH_SEC      = 10
THR_DROWSY_BEH = 0.70
BASELINE_SEC   = 60        # first N s of each session for per-subject p-baseline
CONTINUOUS_SEC = 60        # perclos dwell

# Sweeps
GLOBAL_THR     = [0.40, 0.45, 0.50, 0.55, 0.60]
PER_SUBJ_K     = [1.0, 1.5, 2.0, 2.5, 3.0]   # σ above per-subject baseline
PER_SUBJ_PCT   = [90, 95, 99]                # percentile of baseline window
PCT_WINDOW_SEC = [120, 300]                  # baseline window for percentile threshold
DWELL_SEC      = [10, 20, 30, 60]
SMOOTH_SEC     = [30, 60, 120, 300, 600]     # causal EMA tau


# ── helpers ─────────────────────────────────────────────────────────────
def load_seed():
    z = np.load(SEED_CACHE, allow_pickle=True)
    return z["X"], z["y"], z["subject"], z["time_s"]


def zscore_seed_cal(X, subj_arr, ts_arr, cal_sec=BASELINE_SEC):
    Xn = X.astype(float).copy()
    for s in np.unique(subj_arr):
        m = subj_arr == s
        fit = m & (ts_arr < cal_sec)
        if not fit.any():
            fit = m & (ts_arr < ts_arr[m].min() + cal_sec)
        mu = Xn[fit].mean(axis=0)
        sd = Xn[fit].std(axis=0); sd[sd == 0] = 1.0
        Xn[m] = (Xn[m] - mu) / sd
    return Xn


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0:
        return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p, dtype=float)
    out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def first_sustained_crossing(values, thr, sustain_steps):
    if sustain_steps <= 0:
        sustain_steps = 1
    n = len(values)
    if n < sustain_steps:
        return None
    for i in range(n - sustain_steps + 1):
        if np.all(values[i:i+sustain_steps] > thr):
            return i
    return None


def perclos_for_subject(file_basename):
    p = sio.loadmat(os.path.join(LBL_DIR, file_basename + ".mat"))["perclos"]
    return np.asarray(p).ravel()


def find_session_file_for_subject(subj_id):
    files = sorted(f for f in os.listdir(LBL_DIR) if f.endswith(".mat"))
    matches = [f for f in files if f.startswith(f"{subj_id}_")]
    return matches[0][:-4] if matches else None


# ── build per-subject EEG & behav timelines (computed once) ────────────
def build_timelines():
    X, y, subj, ts = load_seed()
    subjects = sorted(np.unique(subj), key=lambda x: int(x))
    timelines = {}
    print(f"  LOSO-inferring p(drowsy) for {len(subjects)} subjects ...")
    for s in subjects:
        te = subj == s
        tr = ~te
        if te.sum() < 10 or len(np.unique(y[tr])) < 2:
            continue
        Xtr = zscore_seed_cal(X[tr], subj[tr], ts[tr])
        Xte = zscore_seed_cal(X[te], subj[te], ts[te])
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xtr, y[tr])
        proba = clf.predict_proba(Xte)[:, 1]
        times = ts[te]
        order = np.argsort(times)
        p_sorted = proba[order]
        t_sorted = times[order]
        fbase = find_session_file_for_subject(s)
        if fbase is None:
            continue
        perclos = perclos_for_subject(fbase)
        perclos_t = np.arange(len(perclos)) * 8 + 4
        perclos_resamp = np.interp(t_sorted, perclos_t, perclos)
        timelines[str(s)] = {
            "t":        t_sorted,
            "p":        p_sorted,
            "perclos":  perclos_resamp,
        }
    print(f"  ✔ built {len(timelines)} timelines")
    return timelines


# ── onset detection at one (thr_mode, thr_val, dwell, tau) operating pt ─
def detect_onsets(timelines, thr_mode, thr_val, dwell_sec, tau_sec, baseline_sec=None):
    """Returns list[dict] one row per subject with onset times or None.
    Also returns FPR-during-awake: fraction of epochs where the ground-truth
    label is clearly awake (perclos < 0.35) but the (smoothed) EEG posterior
    was above the threshold. This is the false-alarm rate that matters for a
    deployable proactive alert — a long lead time means nothing if EEG is
    alarming throughout the genuinely-awake portion of the session.
    """
    rows = []
    dwell_steps   = max(1, dwell_sec // EPOCH_SEC)
    perclos_steps = max(1, CONTINUOUS_SEC // EPOCH_SEC)
    for s, tl in timelines.items():
        t, p, pc = tl["t"], tl["p"], tl["perclos"]
        p_smooth = causal_ema(p, tau_sec=tau_sec)
        pc_smooth = causal_ema(pc, tau_sec=30)   # modest perclos smoothing

        if thr_mode == "global":
            thr_eeg = float(thr_val)
        elif thr_mode == "per_subject_k":
            baseline = p_smooth[t < BASELINE_SEC]
            if len(baseline) < 3:
                baseline = p_smooth[:3]
            mu = float(np.mean(baseline))
            sd = float(np.std(baseline))
            sd = max(sd, 1e-3)
            thr_eeg = mu + thr_val * sd
            thr_eeg = min(thr_eeg, 0.98)
        elif thr_mode == "per_subject_pct":
            bs = baseline_sec or 120
            baseline = p_smooth[t < bs]
            if len(baseline) < 3:
                baseline = p_smooth[:3]
            thr_eeg = float(np.percentile(baseline, thr_val))
            thr_eeg = min(thr_eeg, 0.98)
        else:
            raise ValueError(thr_mode)

        eeg_idx   = first_sustained_crossing(p_smooth,  thr_eeg, dwell_steps)
        behav_idx = first_sustained_crossing(pc_smooth, THR_DROWSY_BEH, perclos_steps)

        # FPR during awake: epochs where perclos is clearly awake (< 0.35)
        # but EEG posterior is above threshold.
        awake_mask = pc < 0.35
        n_awake = int(awake_mask.sum())
        if n_awake > 0:
            fp = int(((p_smooth > thr_eeg) & awake_mask).sum())
            fpr_awake = fp / n_awake
        else:
            fp = 0; fpr_awake = None

        # Sensitivity during drowsy: perclos > 0.70, EEG above threshold
        drowsy_mask = pc > 0.70
        n_drowsy = int(drowsy_mask.sum())
        if n_drowsy > 0:
            tp = int(((p_smooth > thr_eeg) & drowsy_mask).sum())
            sens_drowsy = tp / n_drowsy
        else:
            tp = 0; sens_drowsy = None

        rows.append({
            "subject":     s,
            "eeg_t":       float(t[eeg_idx])   if eeg_idx   is not None else None,
            "behav_t":     float(t[behav_idx]) if behav_idx is not None else None,
            "thr_eeg":     round(thr_eeg, 4),
            "fpr_awake":   round(fpr_awake, 4) if fpr_awake is not None else None,
            "sens_drowsy": round(sens_drowsy, 4) if sens_drowsy is not None else None,
            "n_awake":     n_awake,
            "n_drowsy":    n_drowsy,
        })
    return rows


def summarise(rows):
    n = len(rows)
    both   = [r for r in rows if r["eeg_t"] is not None and r["behav_t"] is not None]
    eeg_o  = [r for r in rows if r["eeg_t"] is not None and r["behav_t"] is None]
    bev_o  = [r for r in rows if r["eeg_t"] is None     and r["behav_t"] is not None]
    none_  = [r for r in rows if r["eeg_t"] is None     and r["behav_t"] is None]
    leads_sec = [r["behav_t"] - r["eeg_t"] for r in both]
    leads_min = [l / 60.0 for l in leads_sec]
    pos_both = sum(1 for l in leads_sec if l > 0)
    n_informative = len(both) + len(eeg_o) + len(bev_o)
    n_proactive = pos_both + len(eeg_o)
    proactive_rate = n_proactive / n_informative if n_informative > 0 else None

    fprs = [r["fpr_awake"]    for r in rows if r["fpr_awake"]    is not None]
    senss = [r["sens_drowsy"] for r in rows if r["sens_drowsy"] is not None]

    summary = {
        "n_total":             n,
        "n_both":              len(both),
        "n_eeg_only":          len(eeg_o),
        "n_behav_only":        len(bev_o),
        "n_neither":           len(none_),
        "n_informative":       n_informative,
        "n_both_positive":     pos_both,
        "n_proactive_sessions": n_proactive,
        "proactive_rate":      round(proactive_rate, 3) if proactive_rate is not None else None,
        "median_lead_min_both": round(float(np.median(leads_min)), 2) if leads_min else None,
        "mean_lead_min_both":   round(float(np.mean(leads_min)),   2) if leads_min else None,
        "iqr_lead_min_both": [
            round(float(np.percentile(leads_min, 25)), 2) if leads_min else None,
            round(float(np.percentile(leads_min, 75)), 2) if leads_min else None,
        ],
        "max_lead_min_both":    round(float(np.max(leads_min)), 2) if leads_min else None,
        "min_lead_min_both":    round(float(np.min(leads_min)), 2) if leads_min else None,
        # Epoch-level FPR/sensitivity pooled across subjects (awake=perclos<0.35, drowsy=perclos>0.70).
        "fpr_awake_mean":       round(float(np.mean(fprs)),  4) if fprs else None,
        "fpr_awake_median":     round(float(np.median(fprs)), 4) if fprs else None,
        "sens_drowsy_mean":     round(float(np.mean(senss)), 4) if senss else None,
    }
    return summary


def main():
    print("="*80); print("ADVANCE PREDICTION v2 (Phase 7e, v20)"); print("="*80)
    print(f"Timestamp: {datetime.now()}")
    if not os.path.exists(SEED_CACHE):
        print(f"ERROR: {SEED_CACHE} not found — run seed_vig_validation.py first.")
        sys.exit(1)

    timelines = build_timelines()

    sweep = {}  # sweep[thr_mode][thr_val][dwell][tau] = summary
    print()
    print("Sweep (threshold x dwell x tau)")
    for thr_mode, thr_grid in (("global", GLOBAL_THR), ("per_subject_k", PER_SUBJ_K)):
        sweep[thr_mode] = {}
        for thr_val in thr_grid:
            sweep[thr_mode][str(thr_val)] = {}
            for dwell in DWELL_SEC:
                sweep[thr_mode][str(thr_val)][str(dwell)] = {}
                for tau in SMOOTH_SEC:
                    rows = detect_onsets(timelines, thr_mode, thr_val, dwell, tau)
                    summary = summarise(rows)
                    sweep[thr_mode][str(thr_val)][str(dwell)][str(tau)] = summary
                    print(f"  [{thr_mode:14}] thr={thr_val:<5}  dwell={dwell:>3}s  "
                          f"tau={tau:>4}s  ->  proactive={summary['proactive_rate']}  "
                          f"med_lead={summary['median_lead_min_both']} min  "
                          f"FPR_awake={summary['fpr_awake_mean']}  "
                          f"sens_drowsy={summary['sens_drowsy_mean']}")

    # Per-subject percentile modes (nested under two baseline windows)
    for bs in PCT_WINDOW_SEC:
        mode_label = f"per_subject_pct_{bs}"
        sweep[mode_label] = {}
        for pct in PER_SUBJ_PCT:
            sweep[mode_label][str(pct)] = {}
            for dwell in DWELL_SEC:
                sweep[mode_label][str(pct)][str(dwell)] = {}
                for tau in SMOOTH_SEC:
                    rows = detect_onsets(timelines, "per_subject_pct", pct, dwell, tau, baseline_sec=bs)
                    summary = summarise(rows)
                    sweep[mode_label][str(pct)][str(dwell)][str(tau)] = summary
                    print(f"  [{mode_label:20}] pct={pct:<3}  dwell={dwell:>3}s  "
                          f"tau={tau:>4}s  ->  proactive={summary['proactive_rate']}  "
                          f"med_lead={summary['median_lead_min_both']} min  "
                          f"FPR_awake={summary['fpr_awake_mean']}  "
                          f"sens_drowsy={summary['sens_drowsy_mean']}")

    # Pick best operating point by a FPR-penalised proactive utility:
    #   utility = proactive_rate - 2 * FPR_awake_mean
    # A 1 % FPR reduces utility by 0.02; a 10 % FPR by 0.20 — roughly the
    # equivalent of losing one subject from the proactive set. Break ties
    # by median lead time (longer = better) then by sensitivity on drowsy.
    def score(cell):
        pr = cell["proactive_rate"] or 0
        fpr = cell["fpr_awake_mean"] or 0
        ml = cell["median_lead_min_both"] or -999
        sens = cell["sens_drowsy_mean"] or 0
        return (pr - 2.0 * fpr, ml, sens)

    best_by_mode = {}
    for mode in sweep:
        flat = []
        for thr, lvl2 in sweep[mode].items():
            for dwl, lvl3 in lvl2.items():
                for tau, cell in lvl3.items():
                    flat.append(((mode, thr, dwl, tau), cell))
        best = max(flat, key=lambda kv: score(kv[1]))
        best_by_mode[mode] = {"op": best[0], "summary": best[1]}

    # Overall-best: pick the highest score across both modes
    overall_best = max(best_by_mode.values(), key=lambda v: score(v["summary"]))

    print()
    print("─── Operating-point winners (utility = proactive − 2·FPR_awake) ─────")
    for mode, rec in best_by_mode.items():
        op = rec["op"]; s = rec["summary"]
        print(f"  {mode:14}  op={op}  proactive={s['proactive_rate']}  "
              f"med_lead={s['median_lead_min_both']}  FPR_awake={s['fpr_awake_mean']}  "
              f"sens={s['sens_drowsy_mean']}")
    print()
    print(f"  OVERALL BEST: {overall_best['op']}  "
          f"proactive={overall_best['summary']['proactive_rate']}  "
          f"med_lead={overall_best['summary']['median_lead_min_both']} min  "
          f"FPR_awake={overall_best['summary']['fpr_awake_mean']}")

    # Replay the overall-best point to get per-subject detail for the paper
    op = overall_best["op"]
    best_rows = detect_onsets(timelines, op[0], float(op[1]), int(op[2]), int(op[3]))
    per_subject_detail = []
    for r in best_rows:
        lead = (r["behav_t"] - r["eeg_t"]) / 60.0 if (r["eeg_t"] is not None and r["behav_t"] is not None) else None
        per_subject_detail.append({
            "subject":              r["subject"],
            "thr_eeg_used":         r["thr_eeg"],
            "eeg_onset_s":          r["eeg_t"],
            "behavioural_onset_s":  r["behav_t"],
            "lead_time_min":        round(lead, 2) if lead is not None else None,
            "status": ("both" if (r["eeg_t"] is not None and r["behav_t"] is not None)
                       else "eeg_only" if r["eeg_t"] is not None
                       else "behav_only" if r["behav_t"] is not None
                       else "neither"),
        })

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Advance-prediction revisit with three corrections to v13: "
            "(1) sweep the operating point (threshold × dwell × smoothing-τ); "
            "(3) add per-subject calibrated threshold = μ_baseline + k·σ_baseline "
            "using the first 60 s of each session's p(drowsy) as the awake "
            "baseline; (4) classify every session into {both-onset, EEG-only, "
            "behav-only, neither} and report a proactive_rate = "
            "(n_both_positive + n_eeg_only) / n_informative alongside the "
            "median lead time on the both-onset set. Survival framing avoids "
            "silently dropping subjects where EEG flagged but PERCLOS never "
            "crossed 0.70."
        ),
        "grids": {
            "global_threshold":  GLOBAL_THR,
            "per_subject_k":     PER_SUBJ_K,
            "dwell_sec":         DWELL_SEC,
            "smooth_sec_tau":    SMOOTH_SEC,
        },
        "constants": {
            "epoch_sec":         EPOCH_SEC,
            "behav_threshold":   THR_DROWSY_BEH,
            "behav_dwell_sec":   CONTINUOUS_SEC,
            "baseline_sec":      BASELINE_SEC,
        },
        "sweep":        sweep,
        "best_by_mode": best_by_mode,
        "overall_best": overall_best,
        "per_subject_at_best": per_subject_detail,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
