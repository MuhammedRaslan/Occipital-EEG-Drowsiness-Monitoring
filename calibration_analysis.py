"""
Calibration-Based Per-Subject Protocol (Phase 2b, v8)
======================================================
Deployment scenario: the driver sits quietly for CAL_SEC seconds at the
start of a drive; we use only that window to fit a per-subject z-score
scaler, then apply it to the rest of that subject's epochs. This is the
realistic counterpart to v5 (which used the whole awake session for
scaling) and is a direct test of "how much calibration data do we need?".

Pipeline:
  - Hand-crafted 30-feature vector per 10s epoch
  - For each held-out subject:
      * first CAL_SEC of session-1 epochs -> scaler(mean, std)
      * apply to all of the subject's epochs
      * training subjects (9) use their OWN full-awake-session scaler
  - Train/test with LDA + LogReg (best feature-based models from v5)
  - Sweep CAL_SEC over {30, 60, 120, 180, 300}

Output: publication_results_v8.json
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import pandas as pd
import mne
from scipy.signal import welch
from scipy.integrate import trapezoid
from scipy.stats import entropy as sp_entropy, skew
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
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v8.json")
SUBJECTS     = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS           = 128
EPOCH_SEC    = 10
CAL_SECONDS  = [30, 60, 120, 180, 300]   # calibration window durations
BANDS        = {"delta":(0.5,4), "theta":(4,8), "alpha":(8,13), "beta":(13,30)}


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

def feats_epoch(o1, o2, fs):
    feats = {}
    for ch_name, sig in [("O1", o1), ("O2", o2)]:
        for bname, brand in BANDS.items():
            feats[f"{bname}_{ch_name}"] = band_power(sig, fs, brand)
        th = feats[f"theta_{ch_name}"]; al = feats[f"alpha_{ch_name}"]; be = feats[f"beta_{ch_name}"]
        feats[f"theta_alpha_ratio_{ch_name}"] = th / (al + 1e-12)
        feats[f"slow_fast_ratio_{ch_name}"]   = (th + al) / (al + be + 1e-12)
        feats[f"spectral_entropy_{ch_name}"] = spectral_entropy(sig, fs)
        a, m, c = hjorth_params(sig)
        feats[f"hjorth_activity_{ch_name}"]   = a
        feats[f"hjorth_mobility_{ch_name}"]   = m
        feats[f"hjorth_complexity_{ch_name}"] = c
        feats[f"zcr_{ch_name}"] = zcr(sig)
        feats[f"skewness_{ch_name}"] = float(skew(sig))
    for bname in ["theta", "alpha", "beta"]:
        p1 = feats[f"{bname}_O1"]; p2 = feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    feats["mean_theta_alpha_ratio"] = (feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]
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


# ─── load everyone once ──────────────────────────────────────────────────
print("="*80); print("CALIBRATION-BASED PER-SUBJECT PROTOCOL (v8)"); print("="*80)
print(f"Timestamp: {datetime.now()}")
print(f"Epoch={EPOCH_SEC}s | Calibration durations: {CAL_SECONDS} sec")
print()

t0 = time.time()
dfs = []
for subj in SUBJECTS:
    for sess in ["1", "2"]:
        df = load_features(subj, sess)
        if df is None:
            print(f"  MISSING: {subj}_{sess}"); continue
        dfs.append(df)
        print(f"  {subj}_{sess}: {len(df)} epochs")
df_all = pd.concat(dfs, ignore_index=True)
feat_cols = [c for c in df_all.columns if c not in ["subject","session","label","time_s"]]
print(f"\n  Total {len(df_all)} epochs | {len(feat_cols)} features  | load t={time.time()-t0:.1f}s")


def apply_calibration(df, cal_sec):
    """Return a copy of df with per-subject z-score applied.

    Held-out subject (given each outer fold) would use *only* the first
    `cal_sec` seconds of session 1 as calibration.  But since the normalization
    is done up-front (before the LOSO loop) we apply the rule uniformly:
    EVERY subject's scaler is fit on the first cal_sec of session 1.

    This is consistent with both training and deployment using the same
    calibration recipe.
    """
    df = df.copy()
    n_cal_epochs = max(1, cal_sec // EPOCH_SEC)
    for subj in SUBJECTS:
        mask_all = df["subject"] == subj
        mask_cal = mask_all & (df["session"] == "1") & (df["time_s"] < cal_sec)
        if not mask_cal.any():
            # Subject has too few awake epochs — fall back to first n_cal_epochs of sess-1
            s1 = df[mask_all & (df["session"] == "1")].sort_values("time_s").head(n_cal_epochs)
            if s1.empty:
                continue
            mu  = s1[feat_cols].mean()
            sig = s1[feat_cols].std(ddof=0).replace(0.0, 1.0)
        else:
            mu  = df.loc[mask_cal, feat_cols].mean()
            sig = df.loc[mask_cal, feat_cols].std(ddof=0).replace(0.0, 1.0)
        df.loc[mask_all, feat_cols] = (df.loc[mask_all, feat_cols] - mu) / sig
    return df


def evaluate_loso(df_norm, model_builder, exclude_cal_sec=None):
    """Run LOSO; if exclude_cal_sec is set, drop those calibration epochs from
    the held-out subject's test set (so we don't score on data the scaler was fit on)."""
    X = df_norm[feat_cols].values
    y = df_norm["label"].values
    subj_arr = df_norm["subject"].values
    sess_arr = df_norm["session"].values
    t_arr    = df_norm["time_s"].values

    all_t, all_p, all_pr = [], [], []
    per_subj = []
    for test_subj in SUBJECTS:
        tr = subj_arr != test_subj
        te = (subj_arr == test_subj)
        if exclude_cal_sec is not None:
            # Exclude the first exclude_cal_sec seconds of session 1 for the test subject
            te = te & ~((sess_arr == "1") & (t_arr < exclude_cal_sec))

        clf = model_builder()
        clf.fit(X[tr], y[tr])
        y_pred = clf.predict(X[te])
        try:
            y_pr = clf.predict_proba(X[te])[:, 1]
        except Exception:
            y_pr = y_pred.astype(float)

        acc = accuracy_score(y[te], y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc, "n": int(te.sum())})
        all_t.extend(y[te].tolist()); all_p.extend(y_pred.tolist()); all_pr.extend(np.asarray(y_pr).tolist())

    all_t  = np.array(all_t); all_p = np.array(all_p); all_pr = np.array(all_pr, dtype=float)
    acc = accuracy_score(all_t, all_p)*100
    prec = precision_score(all_t, all_p, average="weighted", zero_division=0)*100
    rec  = recall_score(all_t, all_p, average="weighted", zero_division=0)*100
    f1   = f1_score(all_t, all_p, average="weighted", zero_division=0)*100
    kap  = cohen_kappa_score(all_t, all_p)
    try: auc = roc_auc_score(all_t, all_pr)*100
    except Exception: auc = 0.0
    cm = confusion_matrix(all_t, all_p)
    accs = [r["accuracy"] for r in per_subj]
    return {
        "accuracy": round(acc,2),
        "accuracy_mean": round(float(np.mean(accs)),2),
        "accuracy_std":  round(float(np.std(accs)),2),
        "accuracy_min":  round(float(np.min(accs)),2),
        "accuracy_max":  round(float(np.max(accs)),2),
        "precision": round(prec,2), "recall": round(rec,2),
        "f1_score":  round(f1,2),   "auc_roc": round(auc,2),
        "kappa": round(float(kap),4),
        "confusion_matrix": cm.tolist(),
        "per_subject": per_subj,
    }


# ─── model builders (unscaled; we do the scaling via calibration) ────────
# Features are already per-subject z-scored, so no StandardScaler here.
MODELS = {
    "LDA": lambda: LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    "LogReg": lambda: LogisticRegression(
        C=1.0, max_iter=2000, class_weight="balanced", random_state=42),
}

sweeps = {}
for cal_sec in CAL_SECONDS:
    print(f"\n--- Calibration window = {cal_sec}s "
          f"({max(1, cal_sec // EPOCH_SEC)} epochs) ---")
    t1 = time.time()
    df_norm = apply_calibration(df_all, cal_sec)
    bucket = {}
    for model_name, builder in MODELS.items():
        res = evaluate_loso(df_norm, builder, exclude_cal_sec=cal_sec)
        bucket[model_name] = res
        print(f"  {model_name:10s}  acc={res['accuracy']:5.2f}  f1={res['f1_score']:5.2f}  "
              f"auc={res['auc_roc']:5.2f}  kappa={res['kappa']:.4f}")
    bucket["_time_s"] = round(time.time() - t1, 1)
    sweeps[f"cal_{cal_sec}s"] = bucket

# ─── save ───────────────────────────────────────────────────────────────
payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": len(SUBJECTS),
        "epoch_duration_s": EPOCH_SEC,
        "total_epochs": int(len(df_all)),
        "awake_epochs": int((df_all['label']==0).sum()),
        "drowsy_epochs": int((df_all['label']==1).sum()),
        "cross_validation": "LOSO; held-out subject's calibration epochs excluded from scoring",
        "normalization": "per-subject z-score fit on first CAL_SEC of session-1 only",
        "calibration_sec_sweep": CAL_SECONDS,
        "version": "v8",
    },
    "sweeps": sweeps,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {RESULTS_FILE}")
print(f"Total elapsed: {time.time()-t0:.1f}s")
