"""
Advance Prediction (Phase 5, v13)
=================================
Re-validate the "predicts drowsiness X minutes before behavioural onset" claim
under LOSO, using the v11 lean LDA on SEED-VIG (continuous perclos).

Approach
--------
1. Re-extract per-epoch features for SEED-VIG (use cache from Phase 4).
2. Per subject, train v11 lean LDA via LOSO (leave-this-subject-out across
   the 23 SEED-VIG subjects).
3. For each subject, get the continuous p(drowsy) timeline at 10-s resolution
   AND the underlying perclos timeline at 8-s resolution (resampled to 10s).
4. Define behavioural drowsy onset = first time perclos crosses THR_DROWSY
   (after at least CONTINUOUS_SEC of being above the threshold, to avoid
   transient spikes).
5. Define EEG drowsy onset = first time the smoothed p(drowsy) exceeds 0.5
   for SMOOTH_WIN seconds in a row.
6. Lead time = behavioural onset − EEG onset (positive ⇒ EEG predicts ahead).

Output: publication_results_v13.json + a per-subject lead-time table.
Honest framing: a single subject's lead time is not a system-level claim;
the headline metric is the median lead time and the % of subjects with
positive lead time.
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
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v13.json")

EPOCH_SEC      = 10
THR_DROWSY     = 0.70
PROB_THR       = 0.5
CONTINUOUS_SEC = 60   # perclos must stay above THR_DROWSY for this long to count as "true onset"
SMOOTH_WIN     = 30   # seconds — both p(drowsy) and perclos smoothed before onset detection


def load_seed():
    z = np.load(SEED_CACHE, allow_pickle=True)
    return z["X"], z["y"], z["subject"], z["time_s"]


def zscore_seed_cal(X, subj_arr, ts_arr, cal_sec=60):
    Xn = X.astype(float).copy()
    for s in np.unique(subj_arr):
        m = subj_arr == s
        fit = m & (ts_arr < cal_sec)
        if not fit.any():
            fit = m & (ts_arr < ts_arr[m].min() + cal_sec)
        mu = Xn[fit].mean(axis=0)
        sd = Xn[fit].std(axis=0)
        sd[sd == 0] = 1.0
        Xn[m] = (Xn[m] - mu) / sd
    return Xn


def smooth(x, win):
    """Causal moving average (no future leak)."""
    if win <= 1: return x.copy()
    out = np.empty_like(x, dtype=float)
    for i in range(len(x)):
        lo = max(0, i - win + 1)
        out[i] = np.mean(x[lo:i+1])
    return out


def first_sustained_crossing(values, thr, sustain_steps):
    """Earliest index i such that values[i:i+sustain_steps] are all > thr.
       Returns None if never sustained."""
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
    """Load perclos timeline (885 samples at 1/8 Hz)."""
    p = sio.loadmat(os.path.join(LBL_DIR, file_basename + ".mat"))["perclos"]
    return np.asarray(p).ravel()


def find_session_file_for_subject(subj_id):
    """SEED-VIG raw_data filenames begin with the subject id followed by '_'.
       Use the first such file (each subject typically has one session in our cache)."""
    files = sorted(f for f in os.listdir(LBL_DIR) if f.endswith(".mat"))
    matches = [f for f in files if f.startswith(f"{subj_id}_")]
    return matches[0][:-4] if matches else None


# ─── main ────────────────────────────────────────────────────────────────
print("="*80); print("ADVANCE PREDICTION (Phase 5, v13)"); print("="*80)
print(f"Timestamp: {datetime.now()}")
print()

if not os.path.exists(SEED_CACHE):
    print(f"ERROR: {SEED_CACHE} not found — run seed_vig_validation.py first.")
    sys.exit(1)

X, y, subj, ts = load_seed()
subjects = sorted(np.unique(subj), key=lambda x: int(x))
print(f"  loaded {len(X)} epochs × {X.shape[1]} features  | {len(subjects)} subjects")

per_subject_rows = []

for s in subjects:
    test_mask  = subj == s
    train_mask = ~test_mask
    if test_mask.sum() < 10 or len(np.unique(y[test_mask])) < 2:
        continue

    Xtr = zscore_seed_cal(X[train_mask], subj[train_mask], ts[train_mask])
    Xte = zscore_seed_cal(X[test_mask],  subj[test_mask],  ts[test_mask])
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(Xtr, y[train_mask])
    proba = clf.predict_proba(Xte)[:, 1]
    times = ts[test_mask]
    order = np.argsort(times)
    proba_sorted = proba[order]
    times_sorted = times[order]

    # smoothed EEG p(drowsy) timeline at 10s steps
    smooth_steps = max(1, SMOOTH_WIN // EPOCH_SEC)
    proba_smooth = smooth(proba_sorted, smooth_steps)

    # behavioural perclos timeline at 8s — resample to 10s by linear interp
    fbase = find_session_file_for_subject(s)
    if fbase is None: continue
    perclos = perclos_for_subject(fbase)
    perclos_t = np.arange(len(perclos)) * 8 + 4   # midpoint of each 8s window
    perclos_resamp = np.interp(times_sorted, perclos_t, perclos)
    perclos_smooth = smooth(perclos_resamp, smooth_steps)

    # find onsets
    sustain_perclos = max(1, CONTINUOUS_SEC // EPOCH_SEC)
    sustain_proba   = max(1, SMOOTH_WIN     // EPOCH_SEC)

    behav_idx = first_sustained_crossing(perclos_smooth, THR_DROWSY, sustain_perclos)
    eeg_idx   = first_sustained_crossing(proba_smooth,   PROB_THR,   sustain_proba)

    behav_t = float(times_sorted[behav_idx]) if behav_idx is not None else None
    eeg_t   = float(times_sorted[eeg_idx])   if eeg_idx   is not None else None
    lead_s  = (behav_t - eeg_t) if (behav_t is not None and eeg_t is not None) else None

    per_subject_rows.append({
        "subject":          s,
        "n_epochs":         int(test_mask.sum()),
        "behavioural_onset_s": behav_t,
        "eeg_onset_s":         eeg_t,
        "lead_time_s":         lead_s,
    })
    lead_str = "n/a" if lead_s is None else f"{lead_s/60:+.2f} min"
    print(f"  subj {s:>2}  behav={behav_t}  eeg={eeg_t}  lead={lead_str}")

# headline summary
leads = [r["lead_time_s"] for r in per_subject_rows
         if r["lead_time_s"] is not None]
positive = [l for l in leads if l > 0]
n_with_both = len(leads)
n_total = len(per_subject_rows)
summary = {
    "n_subjects_total":          n_total,
    "n_subjects_with_both_onsets": n_with_both,
    "n_subjects_lead_positive":    len(positive),
    "median_lead_min":  round(float(np.median(leads))/60, 2) if leads else None,
    "mean_lead_min":    round(float(np.mean(leads))/60, 2)   if leads else None,
    "iqr_lead_min": [
        round(float(np.percentile(leads, 25))/60, 2) if leads else None,
        round(float(np.percentile(leads, 75))/60, 2) if leads else None,
    ],
    "max_lead_min":     round(float(np.max(leads))/60, 2)   if leads else None,
    "min_lead_min":     round(float(np.min(leads))/60, 2)   if leads else None,
}

print()
print("HEADLINE")
for k, v in summary.items():
    print(f"  {k:<32} {v}")

payload = {
    "timestamp":   datetime.now().isoformat(),
    "methodology": (
        f"v11 lean LDA, LOSO across SEED-VIG subjects. EEG onset = first time "
        f"causal-smoothed (window={SMOOTH_WIN}s) p(drowsy) > {PROB_THR} for "
        f"{SMOOTH_WIN}s. Behavioural onset = first time causal-smoothed perclos "
        f"> {THR_DROWSY} for {CONTINUOUS_SEC}s. Lead = behav_onset − eeg_onset."
    ),
    "summary":     summary,
    "per_subject": per_subject_rows,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {RESULTS_FILE}")
