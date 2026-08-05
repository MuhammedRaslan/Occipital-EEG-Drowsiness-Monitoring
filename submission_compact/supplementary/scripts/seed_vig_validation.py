"""
SEED-VIG cross-dataset validation (Phase 4, v12)
================================================
Apply the v11 lean pipeline (10 features: ENT+SLOPE+COH on O1/O2) trained on
DROZY to SEED-VIG drivers, and also run a SEED-VIG LOSO baseline.

SEED-VIG: 23 sessions × 17 channels × 200 Hz, ~118 min each.
We extract O1 (idx 14) and O2 (idx 16), resample 200→128 Hz to match DROZY,
epoch in 10-s non-overlapping windows, and assign each epoch a perclos label
(mean over the epoch). Binary labels:
    perclos < 0.35  → awake (0)
    perclos > 0.70  → drowsy (1)
    in-between epochs are dropped.

Two evaluations:
  A) DROZY → SEED-VIG transfer:
        - Train v11 lean LDA on the FULL DROZY dataset (10 subjects × 50 epochs)
        - Use cached features_v9_cache.npz for the lean 10 columns
        - Per-SEED-VIG-subject z-score using their first 60 s as calibration awake
        - Score per-subject and overall
  B) SEED-VIG LOSO with v11 lean features:
        - Standalone benchmark for the dataset

Output: publication_results_v12.json
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import scipy.io as sio
from scipy.signal import resample_poly
import pandas as pd
import antropy as ant
from scipy.signal import welch, coherence
from scipy.stats import linregress
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score, confusion_matrix,
)
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SEED_DIR     = r"c:/Users/muham/OneDrive/Documents/#1_DMS/SEED-VIG"
RAW_DIR      = os.path.join(SEED_DIR, "Raw_Data")
LBL_DIR      = os.path.join(SEED_DIR, "perclos_labels")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v12.json")
DROZY_CACHE  = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
SEED_CACHE   = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")

FS_TARGET    = 128
EPOCH_SEC    = 10
LBL_HZ       = 1/8     # one perclos value per 8s
THR_AWAKE    = 0.35
THR_DROWSY   = 0.70
CAL_SEC      = 60      # awake calibration window inside SEED-VIG session
BANDS        = {"theta":(4,8), "alpha":(8,13), "beta":(13,30)}

O1_IDX, O2_IDX = 14, 16   # zero-based in SEED-VIG 17-channel ordering


# ─── lean 10-feature extractor (matches the ENT+SLOPE+COH ablation) ────
def aperiodic_slope(sig, fs, fmin=2.0, fmax=40.0):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    if m.sum() < 5: return 0.0
    lr = linregress(np.log10(f[m] + 1e-12), np.log10(p[m] + 1e-12))
    return float(lr.slope)

def peak_alpha_freq(sig, fs, fmin=8.0, fmax=13.0):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    return float(f[m][np.argmax(p[m])]) if m.any() else 0.0

def band_coherence(o1, o2, fs, band):
    f, cxy = coherence(o1, o2, fs=fs, nperseg=min(int(fs*2), len(o1)))
    m = (f >= band[0]) & (f <= band[1])
    return float(np.mean(cxy[m])) if m.any() else 0.0

# Lean feature names (same order as the v11 ablation index)
LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]

def lean_feats(o1, o2, fs):
    f = {}
    f["sample_entropy_O1"]  = float(ant.sample_entropy(o1, order=2))
    f["sample_entropy_O2"]  = float(ant.sample_entropy(o2, order=2))
    f["perm_entropy_O1"]    = float(ant.perm_entropy(o1, order=3, normalize=True))
    f["perm_entropy_O2"]    = float(ant.perm_entropy(o2, order=3, normalize=True))
    f["aperiodic_slope_O1"] = aperiodic_slope(o1, fs)
    f["aperiodic_slope_O2"] = aperiodic_slope(o2, fs)
    paf1 = peak_alpha_freq(o1, fs); paf2 = peak_alpha_freq(o2, fs)
    f["paf_delta"]          = abs(paf1 - paf2)
    f["coh_theta"]          = band_coherence(o1, o2, fs, BANDS["theta"])
    f["coh_alpha"]          = band_coherence(o1, o2, fs, BANDS["alpha"])
    f["coh_beta"]           = band_coherence(o1, o2, fs, BANDS["beta"])
    return f


# ─── extract / cache SEED-VIG lean features ─────────────────────────────
def extract_seed_vig():
    if os.path.exists(SEED_CACHE):
        print(f"  loading SEED-VIG cache {SEED_CACHE}")
        z = np.load(SEED_CACHE, allow_pickle=True)
        return (z["X"], z["y"], z["subject"], z["time_s"])

    files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".mat"))
    print(f"  {len(files)} SEED-VIG sessions")
    X_rows, y_rows, subj_rows, t_rows = [], [], [], []
    t0 = time.time()
    for fi, fn in enumerate(files):
        subject = fn.split("_")[0]   # numeric subject id (1..23)
        raw = sio.loadmat(os.path.join(RAW_DIR, fn))
        eeg = raw["EEG"][0, 0]
        data = eeg["data"]   # (N_samples, 17)
        sr = int(np.asarray(eeg["sample_rate"]).ravel()[0])
        # extract O1, O2; resample 200 → 128 Hz
        o1 = resample_poly(data[:, O1_IDX], FS_TARGET, sr)
        o2 = resample_poly(data[:, O2_IDX], FS_TARGET, sr)
        # perclos labels (885 × 1) at 1/8 Hz → spans 7080 s
        perclos = np.asarray(sio.loadmat(os.path.join(LBL_DIR, fn))["perclos"]).ravel()
        ws = EPOCH_SEC * FS_TARGET
        n_epochs = len(o1) // ws
        kept = 0
        for i in range(n_epochs):
            t_start = i * EPOCH_SEC
            t_end   = t_start + EPOCH_SEC
            # perclos windows are 8s wide starting at 0,8,16,...
            i0 = int(np.floor(t_start / 8))
            i1 = int(np.ceil(t_end / 8))
            if i1 > len(perclos): break
            p_mean = float(np.mean(perclos[i0:i1]))
            if p_mean < THR_AWAKE:   lbl = 0
            elif p_mean > THR_DROWSY: lbl = 1
            else:                    continue
            seg1 = o1[i*ws:(i+1)*ws]; seg2 = o2[i*ws:(i+1)*ws]
            f = lean_feats(seg1, seg2, FS_TARGET)
            X_rows.append([f[n] for n in LEAN_NAMES])
            y_rows.append(lbl)
            subj_rows.append(subject)
            t_rows.append(t_start)
            kept += 1
        print(f"  [{fi+1:>2}/{len(files)}] {fn:<35}  kept {kept:>4}  ({time.time()-t0:5.0f}s)")

    X = np.asarray(X_rows, dtype=float)
    y = np.asarray(y_rows, dtype=int)
    subj = np.asarray(subj_rows)
    ts = np.asarray(t_rows, dtype=int)
    np.savez_compressed(SEED_CACHE, X=X, y=y, subject=subj, time_s=ts,
                        feat_names=np.array(LEAN_NAMES))
    print(f"  saved cache: shape={X.shape}  awake={(y==0).sum()}  drowsy={(y==1).sum()}")
    return X, y, subj, ts


# ─── load DROZY lean features from the v11 cache ─────────────────────────
def load_drozy_lean():
    z = np.load(DROZY_CACHE, allow_pickle=True)
    feat_names = list(z["feat_cols"])
    ix = [feat_names.index(n) for n in LEAN_NAMES]
    y = z["y"]
    # cache has no session column — infer: label 0 → session "1", label 1 → session "2"
    sess = np.where(y == 0, "1", "2")
    return (z["X"][:, ix], y, z["subjects"], np.zeros(len(y), dtype=int), sess)


# ─── per-subject z-score: full-session awake (DROZY) / first-60s (SEED) ──
def zscore_drozy_awake(X, subj_arr, sess_arr):
    Xn = X.astype(float).copy()
    for s in np.unique(subj_arr):
        m = subj_arr == s
        fit = m & (sess_arr == "1")
        if not fit.any(): continue
        mu = Xn[fit].mean(axis=0)
        sd = Xn[fit].std(axis=0)
        sd[sd == 0] = 1.0
        Xn[m] = (Xn[m] - mu) / sd
    return Xn

def zscore_seed_cal(X, subj_arr, ts_arr, cal_sec=CAL_SEC):
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


# ─── metrics helper ─────────────────────────────────────────────────────
def metrics(y, p, pr):
    return {
        "n":        int(len(y)),
        "n_awake":  int((y == 0).sum()),
        "n_drowsy": int((y == 1).sum()),
        "accuracy": round(accuracy_score(y, p) * 100, 2),
        "precision":round(precision_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "recall":   round(recall_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "f1_score": round(f1_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "auc_roc":  round(roc_auc_score(y, pr) * 100, 2) if len(np.unique(y)) > 1 else None,
        "kappa":    round(cohen_kappa_score(y, p), 4),
        "confusion_matrix": confusion_matrix(y, p).tolist(),
    }


# ─── main ────────────────────────────────────────────────────────────────
print("="*80); print("SEED-VIG CROSS-DATASET VALIDATION (Phase 4, v12)"); print("="*80)
print(f"Timestamp: {datetime.now()}  |  lean features = {len(LEAN_NAMES)} (ENT+SLOPE+COH)")
print()

# A) extract / load SEED-VIG features
print("STEP 1 — SEED-VIG feature extraction")
X_seed, y_seed, subj_seed, ts_seed = extract_seed_vig()
print(f"  shape={X_seed.shape}  subjects={len(np.unique(subj_seed))}  "
      f"awake={(y_seed==0).sum()}  drowsy={(y_seed==1).sum()}")
print()

# B) load DROZY lean features
print("STEP 2 — DROZY lean features (from v11 cache)")
X_dro, y_dro, subj_dro, ts_dro, sess_dro = load_drozy_lean()
print(f"  shape={X_dro.shape}  subjects={len(np.unique(subj_dro))}")
print()

# C) DROZY → SEED-VIG transfer
print("STEP 3 — DROZY → SEED-VIG transfer with v11 lean LDA")
Xn_dro  = zscore_drozy_awake(X_dro,  subj_dro,  sess_dro)
Xn_seed = zscore_seed_cal(X_seed, subj_seed, ts_seed)
clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
clf.fit(Xn_dro, y_dro)
y_pred = clf.predict(Xn_seed)
y_proba = clf.predict_proba(Xn_seed)[:, 1]
overall_transfer = metrics(y_seed, y_pred, y_proba)
print(f"  OVERALL  acc={overall_transfer['accuracy']}  f1={overall_transfer['f1_score']}  "
      f"auc={overall_transfer['auc_roc']}  kappa={overall_transfer['kappa']}  "
      f"n={overall_transfer['n']}  (awake={overall_transfer['n_awake']}, drowsy={overall_transfer['n_drowsy']})")

per_subject_transfer = []
for s in sorted(np.unique(subj_seed), key=lambda x: int(x)):
    m = subj_seed == s
    if m.sum() < 5 or len(np.unique(y_seed[m])) < 2:
        continue
    mt = metrics(y_seed[m], y_pred[m], y_proba[m])
    per_subject_transfer.append({"subject": s, **mt})
    print(f"   - subj {s:>2}  n={mt['n']:>4}  acc={mt['accuracy']:>5}  f1={mt['f1_score']:>5}  "
          f"auc={mt['auc_roc']}")
print()

# D) SEED-VIG LOSO standalone
print("STEP 4 — SEED-VIG LOSO standalone (v11 lean LDA)")
all_y, all_p, all_pr = [], [], []
per_subject_loso = []
for s in sorted(np.unique(subj_seed), key=lambda x: int(x)):
    test = subj_seed == s
    train = ~test
    if test.sum() < 5 or len(np.unique(y_seed[test])) < 2:
        continue
    Xtr_z = zscore_seed_cal(X_seed[train], subj_seed[train], ts_seed[train])
    Xte_z = zscore_seed_cal(X_seed[test],  subj_seed[test],  ts_seed[test])
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(Xtr_z, y_seed[train])
    p  = clf.predict(Xte_z)
    pr = clf.predict_proba(Xte_z)[:, 1]
    mt = metrics(y_seed[test], p, pr)
    per_subject_loso.append({"subject": s, **mt})
    all_y.append(y_seed[test]); all_p.append(p); all_pr.append(pr)
    print(f"   - subj {s:>2}  n={mt['n']:>4}  acc={mt['accuracy']:>5}  f1={mt['f1_score']:>5}  "
          f"auc={mt['auc_roc']}")
overall_loso = metrics(np.concatenate(all_y), np.concatenate(all_p), np.concatenate(all_pr))
print(f"  OVERALL  acc={overall_loso['accuracy']}  f1={overall_loso['f1_score']}  "
      f"auc={overall_loso['auc_roc']}  kappa={overall_loso['kappa']}")
print()

# E) save
payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": (
        "v11 lean 10-feature LDA (ENT+SLOPE+COH on O1/O2) trained on full DROZY then "
        "applied to SEED-VIG (23 sessions, 17-ch @ 200 Hz). Per-SEED-VIG-subject "
        "z-score uses first 60 s as awake calibration. perclos<0.35 → awake, "
        "perclos>0.70 → drowsy, in-between dropped."
    ),
    "drozy_to_seed_transfer": {
        "overall": overall_transfer,
        "per_subject": per_subject_transfer,
    },
    "seed_vig_loso": {
        "overall": overall_loso,
        "per_subject": per_subject_loso,
    },
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"Wrote {RESULTS_FILE}")
