"""
Tier-1 polish #2: Paired stat tests — v17 vs v11, v20 vs v13
=============================================================
Fresh paired Wilcoxon signed-rank + Cohen's d (paired) for the two
head-to-head comparisons reviewers will ask about.

  A) v17 (continuous EMA tau=600 s) vs v11 (no smoothing) — monitoring
     F1 per DROZY subject (10 subjects).
  B) v20 (per-subject pct_300 99th-pctile, dwell=10 s, tau=30 s)
     vs v13 (global thr=0.5, dwell=30 s, tau=30 s) — advance lead
     time per SEED-VIG subject.

For (B) the paired sample is the subset of subjects where BOTH v13
and v20 detect both onsets (behavioural + EEG), so that per-subject
leads are directly comparable. Detection-rate gain (v20 adds subjects
that v13 missed) is reported separately as a McNemar-style count,
because it's a qualitative change, not a paired continuous outcome.

Output: publication_results_v10b.json  (keeps the v10 file untouched)
"""

import os, sys, io, json, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import scipy.io as sio
from datetime import datetime
from scipy.stats import wilcoxon
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import f1_score, roc_auc_score

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
LEAN_CACHE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
SEED_CACHE   = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")
SEED_DIR     = r"c:/Users/muham/OneDrive/Documents/#1_DMS/SEED-VIG"
LBL_DIR      = os.path.join(SEED_DIR, "perclos_labels")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v10b.json")

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC      = 10
TAU_V17        = 600    # v17 continuous-regime winner
BASELINE_SEC   = 60
THR_DROWSY_BEH = 0.70
CONTINUOUS_SEC = 60

# v13 operating point (from advance_prediction.py)
V13_THR       = 0.50
V13_DWELL     = 30
V13_TAU       = 30

# v20 winning operating point (per_subject_pct_300, 99th pctile, dwell 10, tau 30)
V20_THR_PCT   = 99
V20_BASELINE  = 300
V20_DWELL     = 10
V20_TAU       = 30


# ─── Part A: v17 vs v11 per-subject monitoring F1 on DROZY ────────────
def part_A_v17_vs_v11():
    z = np.load(LEAN_CACHE, allow_pickle=True)
    cols = [str(c) for c in z["feat_cols"]]
    ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
    X = z["X"][:, ix].astype(float)
    y = z["y"].astype(int)
    subj = np.asarray(z["subjects"])

    # per-subject_awake z-score
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s; awake = m & (y == 0)
        mu = X[awake].mean(0); sd = X[awake].std(0) + 1e-8
        Xz[m] = (X[m] - mu) / sd

    # LOSO posterior
    p = np.empty(len(y), dtype=float)
    for held in np.unique(subj):
        tr = subj != held; te = subj == held
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xz[tr], y[tr])
        p[te] = clf.predict_proba(Xz[te])[:, 1]

    # v11 (no smoothing) and v17 (continuous EMA per subject)
    p17 = np.empty_like(p)
    for s in np.unique(subj):
        m = np.where(subj == s)[0]
        p_sub = p[m]
        alpha = 1.0 - np.exp(-EPOCH_SEC / TAU_V17)
        out = np.empty_like(p_sub)
        out[0] = p_sub[0]
        for t in range(1, len(p_sub)):
            out[t] = alpha * p_sub[t] + (1 - alpha) * out[t - 1]
        p17[m] = out

    subjects = sorted(np.unique(subj))
    f11 = []; f17 = []; a11 = []; a17 = []
    for s in subjects:
        m = subj == s
        yt = y[m]
        f11.append(f1_score(yt, (p[m]   >= 0.5).astype(int), average="weighted") * 100)
        f17.append(f1_score(yt, (p17[m] >= 0.5).astype(int), average="weighted") * 100)
        try:
            a11.append(roc_auc_score(yt, p[m])   * 100)
            a17.append(roc_auc_score(yt, p17[m]) * 100)
        except ValueError:
            a11.append(np.nan); a17.append(np.nan)

    f11 = np.array(f11); f17 = np.array(f17)
    diff = f17 - f11
    W, p_w = wilcoxon(f17, f11, zero_method="wilcox", alternative="greater")
    # Paired Cohen's d: mean(diff) / sd(diff)
    d = float(np.mean(diff)) / (float(np.std(diff, ddof=1)) + 1e-12)

    out = {
        "comparison": "v17 (continuous EMA tau=600s) vs v11 (no smoothing) — per-subject monitoring F1 on DROZY",
        "n_subjects":      int(len(subjects)),
        "per_subject_F1": {
            "subjects":   [str(x) for x in subjects],
            "f1_v11":     [round(float(x), 2) for x in f11],
            "f1_v17":     [round(float(x), 2) for x in f17],
            "delta":      [round(float(x), 2) for x in diff],
            "auc_v11":    [round(float(x), 2) for x in a11],
            "auc_v17":    [round(float(x), 2) for x in a17],
        },
        "mean_f1_v11":      round(float(np.mean(f11)), 2),
        "mean_f1_v17":      round(float(np.mean(f17)), 2),
        "mean_delta":       round(float(np.mean(diff)), 2),
        "sd_delta":         round(float(np.std(diff, ddof=1)), 2),
        "wilcoxon_W":       round(float(W), 4),
        "wilcoxon_p":       round(float(p_w), 6),
        "cohens_d_paired":  round(float(d), 3),
        "alternative":      "greater (v17 > v11)",
        "notes": (
            "One-sided paired Wilcoxon signed-rank; per-subject F1 at "
            "threshold=0.5. n=10 DROZY subjects. The paired Cohen's d "
            "uses mean(diff)/sd(diff); for small n this is descriptive, "
            "not inferential."
        ),
    }
    return out


# ─── Part B: v20 vs v13 paired lead time on SEED-VIG ──────────────────
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


def part_B_v20_vs_v13():
    z = np.load(SEED_CACHE, allow_pickle=True)
    X = z["X"]; y = z["y"]; subj = z["subject"]; ts = z["time_s"]
    subjects = sorted(np.unique(subj), key=lambda x: int(x))

    # LOSO predict over 21 subjects (same recipe as v13 / v20)
    per = {}
    for s in subjects:
        te = subj == s; tr = ~te
        if te.sum() < 10 or len(np.unique(y[tr])) < 2:
            continue
        Xtr = zscore_seed_cal(X[tr], subj[tr], ts[tr])
        Xte = zscore_seed_cal(X[te], subj[te], ts[te])
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xtr, y[tr])
        proba = clf.predict_proba(Xte)[:, 1]
        times = ts[te]
        order = np.argsort(times)
        p_sorted = proba[order]; t_sorted = times[order]
        fbase = find_session_file_for_subject(s)
        if fbase is None: continue
        perclos = perclos_for_subject(fbase)
        perclos_t = np.arange(len(perclos)) * 8 + 4
        perclos_resamp = np.interp(t_sorted, perclos_t, perclos)
        per[str(s)] = {"t": t_sorted, "p": p_sorted, "perclos": perclos_resamp}

    def detect(tl, thr_mode, dwell_sec, tau_sec):
        t, p, pc = tl["t"], tl["p"], tl["perclos"]
        p_sm = causal_ema(p, tau_sec=tau_sec)
        pc_sm = causal_ema(pc, tau_sec=30)
        if thr_mode == "v13":
            thr_eeg = V13_THR
        else:
            bl = p_sm[t < V20_BASELINE]
            if len(bl) < 3: bl = p_sm[:3]
            thr_eeg = min(float(np.percentile(bl, V20_THR_PCT)), 0.98)
        dwell = max(1, dwell_sec // EPOCH_SEC)
        perc_dwell = max(1, CONTINUOUS_SEC // EPOCH_SEC)
        eeg_idx = first_sustained_crossing(p_sm,  thr_eeg, dwell)
        behav_idx = first_sustained_crossing(pc_sm, THR_DROWSY_BEH, perc_dwell)
        return (float(t[eeg_idx])   if eeg_idx   is not None else None,
                float(t[behav_idx]) if behav_idx is not None else None)

    per_subj_rows = []
    for s, tl in per.items():
        e13, b13 = detect(tl, "v13", V13_DWELL, V13_TAU)
        e20, b20 = detect(tl, "v20", V20_DWELL, V20_TAU)
        # behav onset should be identical (same rule); sanity-check and pick v20's
        b = b20 if b20 is not None else b13
        lead13 = (b - e13) / 60.0 if (e13 is not None and b is not None) else None
        lead20 = (b - e20) / 60.0 if (e20 is not None and b is not None) else None
        per_subj_rows.append({
            "subject": s, "lead13_min": lead13, "lead20_min": lead20,
            "both_v13": e13 is not None and b is not None,
            "both_v20": e20 is not None and b is not None,
        })

    # Paired set: subjects where both protocols detected both onsets
    paired = [(r["lead13_min"], r["lead20_min"]) for r in per_subj_rows
              if r["both_v13"] and r["both_v20"]]
    l13 = np.array([a for a, _ in paired])
    l20 = np.array([b for _, b in paired])
    diff = l20 - l13
    if len(paired) > 0 and np.any(diff != 0):
        W, p_w = wilcoxon(l20, l13, zero_method="wilcox", alternative="greater")
    else:
        W, p_w = float("nan"), float("nan")
    d_paired = float(np.mean(diff)) / (float(np.std(diff, ddof=1)) + 1e-12) if len(paired) > 1 else float("nan")

    # Detection counts (categorical; not a paired continuous test)
    n_v13_only  = sum(1 for r in per_subj_rows if r["both_v13"] and not r["both_v20"])
    n_v20_only  = sum(1 for r in per_subj_rows if r["both_v20"] and not r["both_v13"])
    n_both_det  = sum(1 for r in per_subj_rows if r["both_v13"] and r["both_v20"])
    n_neither   = sum(1 for r in per_subj_rows if (not r["both_v13"]) and (not r["both_v20"]))

    out = {
        "comparison": "v20 (pct_300, 99th pctile, dwell=10s, tau=30s) vs v13 (thr=0.5, dwell=30s, tau=30s) — advance lead time on SEED-VIG",
        "n_subjects_tested": int(len(per_subj_rows)),
        "n_paired_both_detected": int(n_both_det),
        "n_v20_only_detected":    int(n_v20_only),
        "n_v13_only_detected":    int(n_v13_only),
        "n_neither_detected":     int(n_neither),
        "paired_leads_min_v13":   [round(float(x), 2) for x in l13],
        "paired_leads_min_v20":   [round(float(x), 2) for x in l20],
        "paired_mean_v13":        round(float(np.mean(l13)), 2) if len(l13) else None,
        "paired_mean_v20":        round(float(np.mean(l20)), 2) if len(l20) else None,
        "paired_mean_delta":      round(float(np.mean(diff)), 2) if len(diff) else None,
        "paired_sd_delta":        round(float(np.std(diff, ddof=1)), 2) if len(diff) > 1 else None,
        "wilcoxon_W":             round(float(W), 4) if not np.isnan(W) else None,
        "wilcoxon_p":             round(float(p_w), 6) if not np.isnan(p_w) else None,
        "cohens_d_paired":        round(float(d_paired), 3) if not np.isnan(d_paired) else None,
        "alternative":            "greater (v20 > v13 lead time)",
        "per_subject":            per_subj_rows,
        "notes": (
            "One-sided paired Wilcoxon signed-rank on the lead times of "
            "subjects where both v13 and v20 detected both onsets. "
            "Subjects that v20 detects but v13 misses count as a categorical "
            "gain in detection (n_v20_only) and are reported but not "
            "included in the paired continuous test."
        ),
    }
    return out


def main():
    print(f"Timestamp: {datetime.now()}")
    print()
    print("─── Part A: v17 vs v11 (DROZY monitoring F1) ─────────────────────")
    A = part_A_v17_vs_v11()
    print(f"  n = {A['n_subjects']}  mean F1:  v11 = {A['mean_f1_v11']}   v17 = {A['mean_f1_v17']}  "
          f"Δ = +{A['mean_delta']} ± {A['sd_delta']}")
    print(f"  one-sided Wilcoxon p = {A['wilcoxon_p']:.6f}   paired Cohen's d = {A['cohens_d_paired']}")

    print()
    print("─── Part B: v20 vs v13 (SEED-VIG advance lead) ───────────────────")
    B = part_B_v20_vs_v13()
    print(f"  n subjects tested = {B['n_subjects_tested']}")
    print(f"  paired (both detect) = {B['n_paired_both_detected']}  "
          f"v20-only gain = {B['n_v20_only_detected']}  v13-only loss = {B['n_v13_only_detected']}")
    if B["paired_mean_v20"] is not None:
        print(f"  paired mean lead:  v13 = {B['paired_mean_v13']} min   v20 = {B['paired_mean_v20']} min  "
              f"Δ = +{B['paired_mean_delta']} ± {B['paired_sd_delta']} min")
        print(f"  one-sided Wilcoxon p = {B['wilcoxon_p']:.6f}   paired Cohen's d = {B['cohens_d_paired']}")

    payload = {
        "timestamp": datetime.now().isoformat(),
        "comparisons": {"v17_vs_v11": A, "v20_vs_v13": B},
        "methodology": (
            "Fresh paired-sample tests for the two Phase 7 headline "
            "comparisons. Part A: per-subject F1 on DROZY (n=10) for the "
            "v17 EMA smoother against the unsmoothed v11 baseline, "
            "one-sided Wilcoxon signed-rank (alternative='greater'), "
            "paired Cohen's d = mean(diff)/sd(diff). Part B: paired advance "
            "lead times on SEED-VIG for v20 (per-subject 99th-pctile "
            "threshold, dwell=10s, tau=30s) vs v13 (global thr=0.5, "
            "dwell=30s, tau=30s), restricted to the subset of subjects "
            "where both protocols detect both onsets; subjects gained by "
            "v20's more sensitive threshold are reported separately."
        ),
    }
    with open(RESULTS_FILE, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
