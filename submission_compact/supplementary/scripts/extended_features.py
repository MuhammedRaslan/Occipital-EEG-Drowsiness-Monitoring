"""
Extended Feature Set (Phase 2c, v9)
====================================
Adds 20 features to the 30-feature baseline of v5/v8:

  Per channel (× 2 = 16 new):
    - DWT sub-band energies from db4 decomposition (levels A5, D5, D4, D3, D2) → 5
    - Sample entropy (m=2, r=0.2)                                           → 1
    - Permutation entropy (order=3, normalized)                              → 1
    - 1/f aperiodic slope (log-log PSD regression, 2–40 Hz)                  → 1

  Cross-channel (4 new):
    - Peak alpha frequency delta (|PAF_O1 − PAF_O2|)                          → 1
    - Coherence mean in alpha band (8–13 Hz)                                  → 1
    - Coherence mean in theta band (4–8 Hz)                                   → 1
    - Coherence mean in beta band (13–30 Hz)                                  → 1

Total = 30 baseline + 20 extended = 50 features.

Evaluation: Feature-based LDA + LogReg with `subject_awake` full-session
normalization (matches v5), over LOSO — so it is directly comparable to
v5 (30 features) and v8 (30 features, 60 s calibration).

Output: publication_results_v9.json
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
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score, confusion_matrix,
)
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v9.json")
SUBJECTS     = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS           = 128
EPOCH_SEC    = 10
BANDS        = {"delta":(0.5,4), "theta":(4,8), "alpha":(8,13), "beta":(13,30)}


# ─── baseline 30 features (same as v3-v8) ───────────────────────────────
def band_power(sig, fs, band):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= band[0]) & (f <= band[1])
    return float(trapezoid(p[m], f[m])) if m.sum() > 0 else 0.0

def spectral_entropy(sig, fs, fmin=0.5, fmax=40):
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    p_norm = p[m] / (p[m].sum() + 1e-12)
    return float(sp_entropy(p_norm + 1e-12))

def hjorth_params(sig):
    d1 = np.diff(sig); d2 = np.diff(d1)
    activity   = np.var(sig)
    mobility   = np.sqrt(np.var(d1) / (activity + 1e-12))
    complexity = np.sqrt(np.var(d2) / (np.var(d1) + 1e-12)) / (mobility + 1e-12)
    return activity, mobility, complexity

def zcr(sig):
    return float(np.sum(np.diff(np.sign(sig)) != 0)) / len(sig)


# ─── new extended features ──────────────────────────────────────────────
def dwt_energies(sig):
    """db4 wavelet decomposition; return energy of A5, D5, D4, D3, D2 sub-bands."""
    coeffs = pywt.wavedec(sig, "db4", level=5)
    # coeffs = [A5, D5, D4, D3, D2, D1]
    energies = [float(np.sum(c**2)) for c in coeffs[:5]]   # drop D1 (noise)
    return energies

def aperiodic_slope(sig, fs, fmin=2.0, fmax=40.0):
    """1/f slope via log-log linear regression of PSD over [fmin, fmax].
    Returns the slope (negative for 1/f signals)."""
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    if m.sum() < 5:
        return 0.0
    lr = linregress(np.log10(f[m] + 1e-12), np.log10(p[m] + 1e-12))
    return float(lr.slope)

def peak_alpha_freq(sig, fs, fmin=8.0, fmax=13.0):
    """Peak alpha frequency: argmax of PSD in [fmin, fmax]."""
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    if not m.any():
        return 0.0
    return float(f[m][np.argmax(p[m])])

def band_coherence(o1, o2, fs, band):
    f, cxy = coherence(o1, o2, fs=fs, nperseg=min(int(fs*2), len(o1)))
    m = (f >= band[0]) & (f <= band[1])
    return float(np.mean(cxy[m])) if m.any() else 0.0


def feats_epoch(o1, o2, fs):
    feats = {}
    # Baseline per-channel (24)
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

        # Extended per-channel
        for k, e in enumerate(dwt_energies(sig)):
            feats[f"dwt_{k}_{ch_name}"] = e
        feats[f"sample_entropy_{ch_name}"] = float(ant.sample_entropy(sig, order=2))
        feats[f"perm_entropy_{ch_name}"]   = float(ant.perm_entropy(sig, order=3, normalize=True))
        feats[f"aperiodic_slope_{ch_name}"] = aperiodic_slope(sig, fs)

    # Baseline cross-channel (6)
    for bname in ["theta", "alpha", "beta"]:
        p1 = feats[f"{bname}_O1"]; p2 = feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    feats["mean_theta_alpha_ratio"] = (feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]

    # Extended cross-channel
    paf_o1 = peak_alpha_freq(o1, fs); paf_o2 = peak_alpha_freq(o2, fs)
    feats["paf_delta"] = abs(paf_o1 - paf_o2)
    feats["coh_theta"] = band_coherence(o1, o2, fs, BANDS["theta"])
    feats["coh_alpha"] = band_coherence(o1, o2, fs, BANDS["alpha"])
    feats["coh_beta"]  = band_coherence(o1, o2, fs, BANDS["beta"])
    return feats


def load_features(subject, session):
    path = os.path.join(DATA_DIR, f"{subject}_{session}_O1_O2.edf")
    if not os.path.exists(path):
        return None
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)
    data = raw.get_data() * 1e6
    fs = int(raw.info["sfreq"])
    ws = EPOCH_SEC * fs
    n = data.shape[1] // ws
    if n == 0:
        return None
    rows = []
    for i in range(n):
        fe = feats_epoch(data[0, i*ws:(i+1)*ws], data[1, i*ws:(i+1)*ws], fs)
        fe["subject"] = subject
        fe["session"] = session
        fe["label"]   = 0 if session == "1" else 1
        fe["time_s"]  = i * EPOCH_SEC
        rows.append(fe)
    return pd.DataFrame(rows)


# ─── main ────────────────────────────────────────────────────────────────
print("="*80); print("EXTENDED FEATURE SET (v9)"); print("="*80)
print(f"Timestamp: {datetime.now()}  | 50 features = 30 baseline + 20 extended")
print()

t0 = time.time()
dfs = []
for subj in SUBJECTS:
    for sess in ["1", "2"]:
        df = load_features(subj, sess)
        if df is None:
            print(f"  MISSING: {subj}_{sess}"); continue
        dfs.append(df)
        print(f"  {subj}_{sess}: {len(df)} epochs  ({time.time()-t0:.0f}s elapsed)")
df_all = pd.concat(dfs, ignore_index=True)
feat_cols = [c for c in df_all.columns if c not in ["subject","session","label","time_s"]]
print(f"\n  Total {len(df_all)} epochs | {len(feat_cols)} features  | load t={time.time()-t0:.1f}s")

# ─── per-subject awake full-session z-score (matches v5) ─────────────────
for subj in SUBJECTS:
    mask = df_all["subject"] == subj
    fit_mask = mask & (df_all["session"] == "1")
    if not fit_mask.any():
        continue
    mu  = df_all.loc[fit_mask, feat_cols].mean()
    sig = df_all.loc[fit_mask, feat_cols].std(ddof=0).replace(0.0, 1.0)
    df_all.loc[mask, feat_cols] = (df_all.loc[mask, feat_cols] - mu) / sig

X = df_all[feat_cols].values
y = df_all["label"].values
subj_arr = df_all["subject"].values

MODELS = {
    "LDA (shrinkage=auto)": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    "LogReg (C=1, bal)":    lambda: LogisticRegression(
        C=1.0, max_iter=2000, class_weight="balanced", random_state=42),
}

results = {}
for name, builder in MODELS.items():
    print(f"\n▶ {name}")
    all_t, all_p, all_pr = [], [], []
    per_subj = []
    for test_subj in SUBJECTS:
        tr = subj_arr != test_subj
        te = subj_arr == test_subj
        clf = builder()
        clf.fit(X[tr], y[tr])
        y_pred = clf.predict(X[te])
        try:
            y_pr = clf.predict_proba(X[te])[:, 1]
        except Exception:
            y_pr = y_pred.astype(float)
        acc = accuracy_score(y[te], y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc, "n": int(te.sum())})
        all_t.extend(y[te].tolist()); all_p.extend(y_pred.tolist())
        all_pr.extend(np.asarray(y_pr).tolist())
        print(f"   {test_subj}: {acc:5.2f}%")
    all_t = np.array(all_t); all_p = np.array(all_p); all_pr = np.array(all_pr, dtype=float)
    acc = accuracy_score(all_t, all_p)*100
    prec = precision_score(all_t, all_p, average="weighted", zero_division=0)*100
    rec  = recall_score(all_t, all_p, average="weighted", zero_division=0)*100
    f1   = f1_score(all_t, all_p, average="weighted", zero_division=0)*100
    kap  = cohen_kappa_score(all_t, all_p)
    try: auc = roc_auc_score(all_t, all_pr)*100
    except Exception: auc = 0.0
    cm = confusion_matrix(all_t, all_p)
    accs = [r["accuracy"] for r in per_subj]
    results[name] = {
        "accuracy": round(acc,2),
        "accuracy_mean": round(float(np.mean(accs)),2),
        "accuracy_std":  round(float(np.std(accs)),2),
        "accuracy_min":  round(float(np.min(accs)),2),
        "accuracy_max":  round(float(np.max(accs)),2),
        "precision": round(prec,2), "recall": round(rec,2),
        "f1_score": round(f1,2),   "auc_roc": round(auc,2),
        "kappa": round(float(kap),4),
        "confusion_matrix": cm.tolist(),
        "per_subject": per_subj,
    }
    print(f"  >> overall acc={acc:.2f}  f1={f1:.2f}  auc={auc:.2f}  kappa={kap:.4f}")

best_model = max(results, key=lambda k: results[k]["f1_score"])
payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": len(SUBJECTS),
        "epoch_duration_s": EPOCH_SEC,
        "n_features": len(feat_cols),
        "feature_names": feat_cols,
        "total_epochs": int(len(df_all)),
        "awake_epochs": int((y==0).sum()),
        "drowsy_epochs": int((y==1).sum()),
        "cross_validation": "Leave-One-Subject-Out (LOSO)",
        "normalization": "subject_awake (whole session-1)",
        "version": "v9",
    },
    "model_comparison": results,
    "best_model": best_model,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nBest: {best_model} -> F1={results[best_model]['f1_score']}")
print(f"Wrote {RESULTS_FILE}")
print(f"Total elapsed: {time.time()-t0:.1f}s")
