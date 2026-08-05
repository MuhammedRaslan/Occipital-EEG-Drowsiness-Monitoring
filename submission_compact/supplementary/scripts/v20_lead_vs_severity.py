"""
Tier-1 polish #3: Lead-time vs PERCLOS-severity curve
======================================================
v20 quoted the advance lead against a single behavioural onset rule
(PERCLOS > 0.70 sustained 60 s). That is LATE — it's "driver is
fighting sleep". The reviewer-honest framing is to show how the lead
time shrinks as we lower the behavioural threshold toward mild
drowsiness, because that is the real performance envelope.

For each PERCLOS threshold in {0.30, 0.40, 0.50, 0.60, 0.70} (with
the 60 s sustained-crossing rule), we:
  * Recompute behavioural onset per subject.
  * Keep the v20 EEG-onset rule fixed (per-subject pct_300 99th
    pctile, dwell=10s, tau=30s).
  * Report: proactive_rate, median lead, IQR lead, per-session
    false-alert rate (subjects with EEG onset but no behav onset).

This produces the "advance-prediction severity curve" figure.

Outputs:
  publication_results_v20_severity.json
  publication_figures_v5/fig11_lead_vs_severity.png
"""

import os, sys, io, json, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

warnings.filterwarnings("ignore")

# --- Two-column camera-ready figure geometry -------------------------------
# Authored at the IEEEtran two-column \columnwidth and placed 1:1, so the type
# sizes below are the sizes that reach the page. The previous 6.5 x 4.5 in
# geometry was sized for the one-column draft class and scales to 51 % here.
COL_W = 3.45
plt.rcParams.update({
    "font.size":       7,
    "axes.titlesize":  7.5,
    "axes.labelsize":  7,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 5.5,
})

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
# The dataset root has moved between machines (OneDrive -> plain Documents).
# Only perclos_labels/ is read here; the features come from SEED_CACHE.
SEED_DIR_CANDIDATES = [
    os.environ.get("SEED_VIG_DIR", ""),
    r"c:/Users/muham/Documents/#1_DMS/SEED-VIG",
    r"c:/Users/muham/OneDrive/Documents/#1_DMS/SEED-VIG",
]
SEED_DIR = next(
    (d for d in SEED_DIR_CANDIDATES
     if d and os.path.isdir(os.path.join(d, "perclos_labels"))),
    SEED_DIR_CANDIDATES[1],
)
LBL_DIR      = os.path.join(SEED_DIR, "perclos_labels")
SEED_CACHE   = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v20_severity.json")
FIG_DIR      = os.path.join(_SCRIPT_DIR, "publication_figures_v5")
FIG_PATH     = os.path.join(FIG_DIR, "fig11_lead_vs_severity.png")
os.makedirs(FIG_DIR, exist_ok=True)

EPOCH_SEC      = 10
BASELINE_SEC   = 60
CONTINUOUS_SEC = 60
# v20 winning operating point
V20_THR_PCT  = 99
V20_BASELINE = 300
V20_DWELL    = 10
V20_TAU      = 30
# Severity levels to sweep
PERCLOS_THRS = [0.30, 0.40, 0.50, 0.60, 0.70]


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0: return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p, dtype=float); out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def first_sustained_crossing(values, thr, sustain_steps):
    if sustain_steps <= 0: sustain_steps = 1
    n = len(values)
    if n < sustain_steps: return None
    for i in range(n - sustain_steps + 1):
        if np.all(values[i:i+sustain_steps] > thr):
            return i
    return None


def find_session_file_for_subject(subj_id):
    files = sorted(f for f in os.listdir(LBL_DIR) if f.endswith(".mat"))
    matches = [f for f in files if f.startswith(f"{subj_id}_")]
    return matches[0][:-4] if matches else None


def perclos_for_subject(file_basename):
    p = sio.loadmat(os.path.join(LBL_DIR, file_basename + ".mat"))["perclos"]
    return np.asarray(p).ravel()


def zscore_seed_cal(X, subj_arr, ts_arr, cal_sec=BASELINE_SEC):
    Xn = X.astype(float).copy()
    for s in np.unique(subj_arr):
        m = subj_arr == s
        fit = m & (ts_arr < cal_sec)
        if not fit.any():
            fit = m & (ts_arr < ts_arr[m].min() + cal_sec)
        mu = Xn[fit].mean(0); sd = Xn[fit].std(0); sd[sd == 0] = 1.0
        Xn[m] = (Xn[m] - mu) / sd
    return Xn


def build_timelines():
    z = np.load(SEED_CACHE, allow_pickle=True)
    X = z["X"]; y = z["y"]; subj = z["subject"]; ts = z["time_s"]
    subjects = sorted(np.unique(subj), key=lambda x: int(x))
    tl = {}
    for s in subjects:
        te = subj == s; tr = ~te
        if te.sum() < 10 or len(np.unique(y[tr])) < 2: continue
        Xtr = zscore_seed_cal(X[tr], subj[tr], ts[tr])
        Xte = zscore_seed_cal(X[te], subj[te], ts[te])
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xtr, y[tr])
        proba = clf.predict_proba(Xte)[:, 1]
        times = ts[te]; order = np.argsort(times)
        fbase = find_session_file_for_subject(s)
        if fbase is None: continue
        perclos = perclos_for_subject(fbase)
        perclos_t = np.arange(len(perclos)) * 8 + 4
        tl[str(s)] = {
            "t":       times[order],
            "p":       proba[order],
            "perclos": np.interp(times[order], perclos_t, perclos),
        }
    return tl


def sweep_severity(timelines):
    """For each PERCLOS threshold, recompute behav onset (v20 EEG onset fixed)."""
    results = {}
    for beh_thr in PERCLOS_THRS:
        rows = []
        for s, tl in timelines.items():
            t, p, pc = tl["t"], tl["p"], tl["perclos"]
            p_sm = causal_ema(p,  tau_sec=V20_TAU)
            pc_sm = causal_ema(pc, tau_sec=30)
            bl = p_sm[t < V20_BASELINE]
            if len(bl) < 3: bl = p_sm[:3]
            thr_eeg = min(float(np.percentile(bl, V20_THR_PCT)), 0.98)
            dwell = max(1, V20_DWELL // EPOCH_SEC)
            perc_dwell = max(1, CONTINUOUS_SEC // EPOCH_SEC)
            eeg_idx   = first_sustained_crossing(p_sm, thr_eeg, dwell)
            behav_idx = first_sustained_crossing(pc_sm, beh_thr, perc_dwell)
            rows.append({
                "subject": s,
                "eeg_t":   float(t[eeg_idx])   if eeg_idx   is not None else None,
                "behav_t": float(t[behav_idx]) if behav_idx is not None else None,
            })

        both  = [(r["behav_t"] - r["eeg_t"]) / 60.0 for r in rows
                 if r["eeg_t"] is not None and r["behav_t"] is not None]
        n_eeg_only  = sum(1 for r in rows if r["eeg_t"] is not None and r["behav_t"] is None)
        n_beh_only  = sum(1 for r in rows if r["eeg_t"] is None and r["behav_t"] is not None)
        n_neither   = sum(1 for r in rows if r["eeg_t"] is None and r["behav_t"] is None)
        n_info      = len(both) + n_eeg_only + n_beh_only
        pos_both    = sum(1 for l in both if l > 0)
        proactive   = (pos_both + n_eeg_only) / n_info if n_info > 0 else None
        per_sess_fa = n_eeg_only / len(rows) if rows else None
        leads = np.array(both) if both else np.array([])
        results[str(beh_thr)] = {
            "beh_thr": beh_thr,
            "n_both": len(both), "n_eeg_only": n_eeg_only,
            "n_behav_only": n_beh_only, "n_neither": n_neither,
            "proactive_rate":     round(proactive, 3) if proactive is not None else None,
            "per_session_fa":     round(per_sess_fa, 3),
            "median_lead_min":    round(float(np.median(leads)), 2) if len(leads) else None,
            "mean_lead_min":      round(float(np.mean(leads)), 2) if len(leads) else None,
            "iqr_lead_min":       [round(float(np.percentile(leads, 25)), 2) if len(leads) else None,
                                   round(float(np.percentile(leads, 75)), 2) if len(leads) else None],
            "min_lead_min":       round(float(np.min(leads)), 2) if len(leads) else None,
            "max_lead_min":       round(float(np.max(leads)), 2) if len(leads) else None,
            "paired_leads":       [round(float(x), 2) for x in leads.tolist()],
        }
    return results


def plot_curve(results, fig_path):
    thrs = sorted(float(t) for t in results.keys())
    medians = [results[str(t)]["median_lead_min"] for t in thrs]
    iqr_lo  = [results[str(t)]["iqr_lead_min"][0] for t in thrs]
    iqr_hi  = [results[str(t)]["iqr_lead_min"][1] for t in thrs]
    proact  = [results[str(t)]["proactive_rate"] for t in thrs]
    fa      = [results[str(t)]["per_session_fa"] for t in thrs]

    fig, ax1 = plt.subplots(figsize=(COL_W, COL_W * 0.92))
    color1 = "#1f3b6e"
    ax1.fill_between(thrs, iqr_lo, iqr_hi, alpha=0.18, color=color1,
                     label="Lead IQR (25-75%)")
    ax1.plot(thrs, medians, "o-", color=color1, lw=1.3, ms=3.5, label="Median lead (min)")
    ax1.axhline(0, color="0.6", lw=0.8, ls="--")
    ax1.set_xlabel("Behavioural PERCLOS threshold (sustained 60 s)")
    ax1.set_ylabel("EEG → PERCLOS lead time (min)", color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    color2 = "#a02a2a"
    ax2.plot(thrs, proact, "s--", color=color2, lw=1.1, ms=3.2,
             label="Proactive rate")
    ax2.plot(thrs, fa, "^:", color="#c75f1e", lw=1.0, ms=3.2,
             label="Per-session false-alert rate")
    ax2.set_ylabel("Rate", color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(0, 1.05)

    # Combined legend in the figure header. Four series plus a filled IQR band
    # leave no interior space at 3.45 in: in-axes at upper left it sat directly
    # on the flat proactive-rate line and hid it. A header legend also avoids
    # the axis-ordering trap, since ax2 is drawn over anything placed on ax1.
    l1, lbl1 = ax1.get_legend_handles_labels()
    l2, lbl2 = ax2.get_legend_handles_labels()
    fig.legend(l1 + l2, lbl1 + lbl2, loc="upper center",
               bbox_to_anchor=(0.5, 0.895), ncol=2, frameon=False,
               labelspacing=0.3, handlelength=1.6, handletextpad=0.5,
               columnspacing=1.2)

    # The second title line was one 82-character run, which overruns a 3.45 in
    # figure. The dropped detail ("of first 5 min") is stated in Sec. V.
    fig.suptitle("Advance-prediction envelope vs PERCLOS severity\n"
                 "v20 EEG rule fixed: 99th pctile, dwell 10 s, $\\tau$ = 30 s",
                 fontsize=7.5, y=0.995)
    # rect reserves room for the header legend only. tight_layout already
    # accounts for the suptitle itself, so reserving for the title here too
    # double-counts it and opens a dead band between legend and axes.
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(fig_path, dpi=400)
    plt.close(fig)


def main():
    print(f"Timestamp: {datetime.now()}")
    print("Building LOSO timelines...")
    tl = build_timelines()
    print(f"  -> {len(tl)} subjects")
    print()
    res = sweep_severity(tl)
    print("─── Lead-time vs PERCLOS severity ────────────────────────────────")
    print(f"  {'PERCLOS':>8}  {'n_both':>6}  {'n_eeg_only':>11}  {'n_beh_only':>11}  "
          f"{'proactive':>9}  {'per-sess FA':>11}  {'median lead':>12}  {'IQR':>18}")
    for thr_key in sorted(res.keys(), key=float):
        r = res[thr_key]
        iqr = r["iqr_lead_min"]
        iqr_str = f"[{iqr[0]:+5.1f}, {iqr[1]:+5.1f}]" if iqr[0] is not None else "    n/a"
        med = f"{r['median_lead_min']:+6.2f}" if r["median_lead_min"] is not None else "  n/a"
        print(f"  {float(thr_key):>8.2f}  {r['n_both']:>6}  {r['n_eeg_only']:>11}  "
              f"{r['n_behav_only']:>11}  {r['proactive_rate']:>9}  "
              f"{r['per_session_fa']:>11}  {med:>12}  {iqr_str:>18}")

    plot_curve(res, FIG_PATH)
    print(f"  figure -> {FIG_PATH}")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "methodology": (
            "Sweep of the behavioural onset threshold (PERCLOS > "
            f"{{{','.join(str(t) for t in PERCLOS_THRS)}}} sustained 60 s) "
            "with the v20 EEG-onset rule held constant (per-subject 99th-"
            "percentile threshold on 5-min baseline of causal-EMA-smoothed "
            "p(drowsy), tau=30 s, dwell=10 s). Produces the advance-"
            "prediction envelope: as the behavioural marker becomes more "
            "conservative (higher PERCLOS), the lead grows but the absolute "
            "number of paired onsets falls."
        ),
        "eeg_rule": {
            "threshold_mode": "per_subject_pct",
            "percentile":     V20_THR_PCT,
            "baseline_sec":   V20_BASELINE,
            "dwell_sec":      V20_DWELL,
            "tau_sec":        V20_TAU,
        },
        "perclos_sustain_sec": CONTINUOUS_SEC,
        "severity_sweep":      res,
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  json   -> {RESULTS_FILE}")


if __name__ == "__main__":
    main()
