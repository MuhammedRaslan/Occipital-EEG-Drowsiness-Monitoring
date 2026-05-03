"""
Feature-Family Ablation (Phase 3a, v11)
========================================
Re-uses the 50-feature extraction from v9 (extended_features.py) and runs
Leave-One-Subject-Out LDA for each ablation of feature families. Tells
us which features are *actually* responsible for the v5->v9 jump from
53.3 F1 to 61.1 F1.

Feature families (totals in parens):
  BASE      = v5's 30 features: band powers, ratios, spectral entropy,
              Hjorth, ZCR, skewness, asymmetries, totals             (30)
  DWT       = db4 sub-band energies for O1, O2                         (10)
  ENT       = sample entropy + permutation entropy (both channels)    (4)
  SLOPE     = 1/f aperiodic slope (both channels)                      (2)
  COH       = band-coherence theta/alpha/beta + peak-alpha-freq delta  (4)

Ablations tested:
  ALL         : BASE + DWT + ENT + SLOPE + COH            (50 feats)
  BASE        : BASE only                                 (30 feats; replicates v5)
  DROP DWT    : ALL \\ DWT                                 (40)
  DROP ENT    : ALL \\ ENT                                 (46)
  DROP SLOPE  : ALL \\ SLOPE                               (48)
  DROP COH    : ALL \\ COH                                 (46)
  ONLY DWT    : DWT only                                   (10)
  ONLY ENT+SLOPE+COH : all the new families combined       (20)

Caches the 50-feature matrix to features_v9_cache.npz so the 15-min
extraction isn't redone on the next ablation pass.

Output: publication_results_v11.json
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import pandas as pd
import mne
import pywt
import antropy as ant
from scipy.signal import welch, coherence
from scipy.integrate import trapezoid
from scipy.stats import entropy as sp_entropy, skew, linregress
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score, confusion_matrix,
)
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")
CACHE_FILE   = os.path.join(_SCRIPT_DIR, "features_v9_cache.npz")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v11.json")
SUBJECTS     = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS           = 128
EPOCH_SEC    = 10
BANDS        = {"delta":(0.5,4), "theta":(4,8), "alpha":(8,13), "beta":(13,30)}


def band_power(sig, fs, band):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= band[0]) & (f <= band[1])
    return float(trapezoid(p[m], f[m])) if m.sum() > 0 else 0.0

def spectral_entropy(sig, fs):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= 0.5) & (f <= 40)
    p_norm = p[m] / (p[m].sum() + 1e-12)
    return float(sp_entropy(p_norm + 1e-12))

def hjorth_params(sig):
    d1 = np.diff(sig); d2 = np.diff(d1)
    activity   = np.var(sig)
    mobility   = np.sqrt(np.var(d1) / (activity + 1e-12))
    complexity = np.sqrt(np.var(d2) / (np.var(d1) + 1e-12)) / (mobility + 1e-12)
    return activity, mobility, complexity

def zcr(sig): return float(np.sum(np.diff(np.sign(sig)) != 0)) / len(sig)

def dwt_energies(sig):
    coeffs = pywt.wavedec(sig, "db4", level=5)
    return [float(np.sum(c**2)) for c in coeffs[:5]]

def aperiodic_slope(sig, fs, fmin=2.0, fmax=40.0):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    if m.sum() < 5: return 0.0
    lr = linregress(np.log10(f[m] + 1e-12), np.log10(p[m] + 1e-12))
    return float(lr.slope)

def peak_alpha_freq(sig, fs):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= 8.0) & (f <= 13.0)
    return float(f[m][np.argmax(p[m])]) if m.any() else 0.0

def band_coherence(o1, o2, fs, band):
    f, cxy = coherence(o1, o2, fs=fs, nperseg=min(int(fs*2), len(o1)))
    m = (f >= band[0]) & (f <= band[1])
    return float(np.mean(cxy[m])) if m.any() else 0.0


def feats_epoch(o1, o2, fs):
    feats = {}
    for ch_name, sig in [("O1", o1), ("O2", o2)]:
        for bname, brand in BANDS.items():
            feats[f"{bname}_{ch_name}"] = band_power(sig, fs, brand)
        th = feats[f"theta_{ch_name}"]; al = feats[f"alpha_{ch_name}"]; be = feats[f"beta_{ch_name}"]
        feats[f"theta_alpha_ratio_{ch_name}"] = th / (al + 1e-12)
        feats[f"slow_fast_ratio_{ch_name}"]   = (th + al) / (al + be + 1e-12)
        feats[f"spectral_entropy_{ch_name}"]  = spectral_entropy(sig, fs)
        a, m, c = hjorth_params(sig)
        feats[f"hjorth_activity_{ch_name}"]   = a
        feats[f"hjorth_mobility_{ch_name}"]   = m
        feats[f"hjorth_complexity_{ch_name}"] = c
        feats[f"zcr_{ch_name}"] = zcr(sig)
        feats[f"skewness_{ch_name}"] = float(skew(sig))
        for k, e in enumerate(dwt_energies(sig)):
            feats[f"dwt_{k}_{ch_name}"] = e
        feats[f"sample_entropy_{ch_name}"] = float(ant.sample_entropy(sig, order=2))
        feats[f"perm_entropy_{ch_name}"]   = float(ant.perm_entropy(sig, order=3, normalize=True))
        feats[f"aperiodic_slope_{ch_name}"] = aperiodic_slope(sig, fs)
    for bname in ["theta", "alpha", "beta"]:
        p1 = feats[f"{bname}_O1"]; p2 = feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    feats["mean_theta_alpha_ratio"] = (feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]
    feats["paf_delta"] = abs(peak_alpha_freq(o1, fs) - peak_alpha_freq(o2, fs))
    feats["coh_theta"] = band_coherence(o1, o2, fs, BANDS["theta"])
    feats["coh_alpha"] = band_coherence(o1, o2, fs, BANDS["alpha"])
    feats["coh_beta"]  = band_coherence(o1, o2, fs, BANDS["beta"])
    return feats


def extract_all():
    rows = []
    t0 = time.time()
    for subj in SUBJECTS:
        for sess in ["1", "2"]:
            path = os.path.join(DATA_DIR, f"{subj}_{sess}_O1_O2.edf")
            if not os.path.exists(path):
                continue
            raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
            raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)
            data = raw.get_data() * 1e6
            fs = int(raw.info["sfreq"])
            ws = EPOCH_SEC * fs
            n = data.shape[1] // ws
            for i in range(n):
                fe = feats_epoch(data[0, i*ws:(i+1)*ws], data[1, i*ws:(i+1)*ws], fs)
                fe["subject"] = subj
                fe["session"] = sess
                fe["label"]   = 0 if sess == "1" else 1
                fe["time_s"]  = i * EPOCH_SEC
                rows.append(fe)
            print(f"  {subj}_{sess}: {n} epochs  ({time.time()-t0:.0f}s)")
    return pd.DataFrame(rows)


# ─── load / build cache ─────────────────────────────────────────────────
print("="*80); print("FEATURE-FAMILY ABLATION (Phase 3a, v11)"); print("="*80)

if os.path.exists(CACHE_FILE):
    print(f"Loading cached features from {CACHE_FILE}")
    z = np.load(CACHE_FILE, allow_pickle=True)
    X_all    = z["X"]
    y        = z["y"]
    subjects = z["subjects"]
    feat_cols = list(z["feat_cols"])
    print(f"  shape={X_all.shape}  features={len(feat_cols)}  n_epochs={len(y)}")
else:
    print("Cache not found — extracting features (~15 min)...")
    df = extract_all()
    feat_cols = [c for c in df.columns if c not in ["subject","session","label","time_s"]]
    X_all    = df[feat_cols].values
    y        = df["label"].values.astype(np.int64)
    subjects = df["subject"].values
    np.savez(CACHE_FILE, X=X_all, y=y, subjects=subjects, feat_cols=np.array(feat_cols))
    print(f"  Saved cache. shape={X_all.shape}  features={len(feat_cols)}")


# ─── per-subject awake z-score on the full feature matrix ───────────────
# Apply subject-awake normalization once, over the full column set. Subsets
# then act on the already-normalized columns.
session_cache = {}
# We need "session" information. Since each subject contributes 2 sessions
# and labels are 0/1, we can reconstruct by using the first subject-session
# block boundary but easier: re-load the DF — it's cheap compared to feature
# extraction — only when cache is fresh we have it. Since the cache doesn't
# carry sessions, infer session from label (0 = awake, 1 = drowsy).
sessions = np.where(y == 0, "1", "2")

for subj in SUBJECTS:
    mask = subjects == subj
    fit_mask = mask & (sessions == "1")
    if not fit_mask.any():
        continue
    mu  = X_all[fit_mask].mean(axis=0)
    sig = X_all[fit_mask].std(axis=0, ddof=0)
    sig[sig == 0] = 1.0
    X_all[mask] = (X_all[mask] - mu) / sig


# ─── feature family indices ──────────────────────────────────────────────
def ixs(predicate):
    return [i for i, name in enumerate(feat_cols) if predicate(name)]

BASE_NAMES_PREFIXES = (
    "delta_", "theta_", "alpha_", "beta_",            # note: matches theta_alpha_ratio too
    "theta_alpha_ratio_", "slow_fast_ratio_",
    "spectral_entropy_", "hjorth_", "zcr_", "skewness_",
    "asymmetry_", "mean_theta_alpha_ratio", "total_",
)
# More defensive: explicit list of the v5 30 names
BASE_NAMES = [
    "delta_O1","theta_O1","alpha_O1","beta_O1",
    "theta_alpha_ratio_O1","slow_fast_ratio_O1","spectral_entropy_O1",
    "hjorth_activity_O1","hjorth_mobility_O1","hjorth_complexity_O1",
    "zcr_O1","skewness_O1",
    "delta_O2","theta_O2","alpha_O2","beta_O2",
    "theta_alpha_ratio_O2","slow_fast_ratio_O2","spectral_entropy_O2",
    "hjorth_activity_O2","hjorth_mobility_O2","hjorth_complexity_O2",
    "zcr_O2","skewness_O2",
    "asymmetry_theta","asymmetry_alpha","asymmetry_beta",
    "mean_theta_alpha_ratio","total_theta","total_alpha",
]
DWT_IX   = [i for i, n in enumerate(feat_cols) if n.startswith("dwt_")]
ENT_IX   = [i for i, n in enumerate(feat_cols)
            if n.startswith("sample_entropy_") or n.startswith("perm_entropy_")]
SLOPE_IX = [i for i, n in enumerate(feat_cols) if n.startswith("aperiodic_slope_")]
COH_IX   = [i for i, n in enumerate(feat_cols)
            if n.startswith("coh_") or n == "paf_delta"]
BASE_IX  = [feat_cols.index(n) for n in BASE_NAMES if n in feat_cols]

print(f"\n  BASE = {len(BASE_IX)}   DWT = {len(DWT_IX)}   "
      f"ENT = {len(ENT_IX)}   SLOPE = {len(SLOPE_IX)}   COH = {len(COH_IX)}")
assert len(BASE_IX) + len(DWT_IX) + len(ENT_IX) + len(SLOPE_IX) + len(COH_IX) == len(feat_cols), \
    "feature family bookkeeping mismatch"

ALL_IX = BASE_IX + DWT_IX + ENT_IX + SLOPE_IX + COH_IX

ABLATIONS = {
    "ALL (50)":               sorted(ALL_IX),
    "BASE only (30)":         sorted(BASE_IX),
    "DROP DWT (40)":          sorted(BASE_IX + ENT_IX + SLOPE_IX + COH_IX),
    "DROP ENT (46)":          sorted(BASE_IX + DWT_IX + SLOPE_IX + COH_IX),
    "DROP SLOPE (48)":        sorted(BASE_IX + DWT_IX + ENT_IX + COH_IX),
    "DROP COH (46)":          sorted(BASE_IX + DWT_IX + ENT_IX + SLOPE_IX),
    "ONLY DWT (10)":          sorted(DWT_IX),
    "ONLY ENT+SLOPE+COH (10)":sorted(ENT_IX + SLOPE_IX + COH_IX),
    "NEW FAMILIES (20)":      sorted(DWT_IX + ENT_IX + SLOPE_IX + COH_IX),
}


def eval_subset(ix_subset):
    Xs = X_all[:, ix_subset]
    all_t, all_p, all_pr = [], [], []
    per_subj = []
    for test_subj in SUBJECTS:
        tr = subjects != test_subj
        te = subjects == test_subj
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xs[tr], y[tr])
        y_pred = clf.predict(Xs[te])
        try: y_pr = clf.predict_proba(Xs[te])[:, 1]
        except Exception: y_pr = y_pred.astype(float)
        acc = accuracy_score(y[te], y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc, "n": int(te.sum())})
        all_t.extend(y[te].tolist()); all_p.extend(y_pred.tolist())
        all_pr.extend(np.asarray(y_pr).tolist())
    all_t = np.array(all_t); all_p = np.array(all_p); all_pr = np.array(all_pr, dtype=float)
    acc = accuracy_score(all_t, all_p)*100
    prec = precision_score(all_t, all_p, average="weighted", zero_division=0)*100
    rec  = recall_score(all_t, all_p, average="weighted", zero_division=0)*100
    f1   = f1_score(all_t, all_p, average="weighted", zero_division=0)*100
    kap  = cohen_kappa_score(all_t, all_p)
    try: auc = roc_auc_score(all_t, all_pr)*100
    except Exception: auc = 0.0
    return {
        "accuracy": round(acc,2),
        "precision": round(prec,2), "recall": round(rec,2),
        "f1_score": round(f1,2), "auc_roc": round(auc,2),
        "kappa": round(float(kap),4),
        "per_subject": per_subj,
        "n_features_used": len(ix_subset),
    }


print("\n" + "="*80)
print("RUNNING ABLATIONS")
print("="*80)
results = {}
for name, ix in ABLATIONS.items():
    t0 = time.time()
    r = eval_subset(ix)
    r["time_s"] = round(time.time() - t0, 1)
    results[name] = r
    print(f"  {name:28s}  n={r['n_features_used']:2d}  "
          f"acc={r['accuracy']:5.2f}  f1={r['f1_score']:5.2f}  "
          f"auc={r['auc_roc']:5.2f}  kappa={r['kappa']:+.4f}  "
          f"t={r['time_s']}s")

payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": len(SUBJECTS),
        "epoch_duration_s": EPOCH_SEC,
        "total_epochs": int(len(y)),
        "cross_validation": "LOSO, LDA (shrinkage=auto)",
        "normalization": "subject_awake (whole session-1)",
        "feature_family_counts": {
            "BASE": len(BASE_IX), "DWT": len(DWT_IX), "ENT": len(ENT_IX),
            "SLOPE": len(SLOPE_IX), "COH": len(COH_IX),
        },
        "version": "v11",
    },
    "ablations": results,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {RESULTS_FILE}")
