"""
Nested LOSO Hyperparameter Tuning (Phase 2a, v7)
=================================================
Outer loop : Leave-One-Subject-Out across 10 DROZY subjects.
Inner loop : GroupKFold(3) on the 9 training subjects -> GridSearchCV.

Pipelines evaluated (selected as the top performers from v5/v6):
  A. Riemannian TS + LogReg        (C grid)
  B. Riemannian TS + LDA           (shrinkage grid)
  C. Feature-based LDA, subject_awake norm (shrinkage grid)
  D. Feature-based LogReg, subject_awake norm (C grid)

Covariance / tangent-space transforms are computed once per outer fold
so the inner grid search is cheap — only the final classifier is refit
for each hyperparameter setting.

Output: publication_results_v7.json
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
from sklearn.model_selection import GroupKFold, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score, confusion_matrix,
)
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v7.json")

SUBJECTS   = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS         = 128
EPOCH_SEC  = 10
COV_EST    = "oas"
INNER_K    = 3
BANDS      = {"delta":(0.5,4), "theta":(4,8), "alpha":(8,13), "beta":(13,30)}


# ─── feature extraction (mirrors publication_analysis.py) ────────────────
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


def load_subject_session(subject, session):
    path = os.path.join(DATA_DIR, f"{subject}_{session}_O1_O2.edf")
    if not os.path.exists(path):
        return None, None
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)
    data = raw.get_data() * 1e6
    fs = int(raw.info["sfreq"])
    ws = EPOCH_SEC * fs
    n = data.shape[1] // ws
    if n == 0:
        return None, None
    raw_epochs = np.stack([data[:, i*ws:(i+1)*ws] for i in range(n)], axis=0)
    feat_rows = [feats_epoch(raw_epochs[i, 0], raw_epochs[i, 1], fs) for i in range(n)]
    return raw_epochs, pd.DataFrame(feat_rows)


# ─── load data (both raw epochs + hand-crafted features in one pass) ────
print("="*80)
print("NESTED LOSO HYPERPARAMETER TUNING (v7)")
print("="*80)
print(f"Timestamp: {datetime.now()}")
print(f"Epoch: {EPOCH_SEC}s @ {FS}Hz | Inner k-fold: {INNER_K}")
print()

print("Loading raw epochs + features...")
t0 = time.time()
raw_list, feat_list, y_list, subj_list, sess_list = [], [], [], [], []
for subj in SUBJECTS:
    for sess in ["1", "2"]:
        raws, feats = load_subject_session(subj, sess)
        if raws is None:
            print(f"  MISSING {subj}_{sess}"); continue
        n = raws.shape[0]
        raw_list.append(raws)
        feat_list.append(feats)
        label = 0 if sess == "1" else 1
        y_list.append(np.full(n, label, dtype=np.int64))
        subj_list.append(np.array([subj]*n))
        sess_list.append(np.array([sess]*n))
        print(f"  {subj}_{sess}: {n} epochs")

X_raw    = np.concatenate(raw_list, axis=0)            # (N, 2, ws)
df_feat  = pd.concat(feat_list, ignore_index=True)
y        = np.concatenate(y_list, axis=0)
subjects = np.concatenate(subj_list, axis=0)
sessions = np.concatenate(sess_list, axis=0)
feat_cols = list(df_feat.columns)

print(f"\n  Total: {X_raw.shape[0]} epochs | {len(feat_cols)} features | "
      f"{(y==0).sum()} awake / {(y==1).sum()} drowsy  | load t={time.time()-t0:.1f}s")


# ─── per-subject awake z-score normalization (for feature pipelines) ─────
df_feat_norm = df_feat.copy()
for subj in SUBJECTS:
    mask = subjects == subj
    fit_mask = mask & (sessions == "1")
    if not fit_mask.any():
        continue
    mu  = df_feat_norm.loc[fit_mask, feat_cols].mean()
    sig = df_feat_norm.loc[fit_mask, feat_cols].std(ddof=0).replace(0.0, 1.0)
    df_feat_norm.loc[mask, feat_cols] = (df_feat_norm.loc[mask, feat_cols] - mu) / sig
X_feat = df_feat_norm[feat_cols].values


# ─── pipeline definitions: inner CV only refits the final classifier ─────
# For Riemannian pipes we cache cov+TS per outer fold and only vary the clf.

GRIDS = {
    "TS+LogReg (Riemann, tuned)": {
        "type": "riemann",
        "param_name": "C",
        "grid": [0.01, 0.1, 1.0, 10.0],
        "build": lambda C: LogisticRegression(
            C=C, max_iter=2000, class_weight="balanced", random_state=42),
    },
    "TS+LDA (Riemann, tuned)": {
        "type": "riemann",
        "param_name": "shrinkage",
        "grid": ["auto", 0.0, 0.1, 0.5],
        "build": lambda s: LinearDiscriminantAnalysis(
            solver="lsqr", shrinkage=s if s != 0.0 else None),
    },
    "LDA (subject_awake, tuned)": {
        "type": "feature",
        "param_name": "shrinkage",
        "grid": ["auto", 0.0, 0.1, 0.5],
        "build": lambda s: LinearDiscriminantAnalysis(
            solver="lsqr", shrinkage=s if s != 0.0 else None),
    },
    "LogReg (subject_awake, tuned)": {
        "type": "feature",
        "param_name": "C",
        "grid": [0.01, 0.1, 1.0, 10.0],
        "build": lambda C: LogisticRegression(
            C=C, max_iter=2000, class_weight="balanced", random_state=42),
    },
}


def nested_loso(model_name, spec):
    print(f"\n▶ {model_name}  ({spec['param_name']} ∈ {spec['grid']})")
    t_m = time.time()
    all_true, all_pred, all_proba = [], [], []
    per_subj = []
    chosen_hparams = []

    for test_subj in SUBJECTS:
        tr_out = subjects != test_subj
        te_out = subjects == test_subj

        # Precompute representation once per outer fold
        if spec["type"] == "riemann":
            cov_est = Covariances(estimator=COV_EST)
            ts      = TangentSpace(metric="riemann")
            C_tr    = cov_est.fit_transform(X_raw[tr_out])
            Z_tr    = ts.fit_transform(C_tr)
            C_te    = cov_est.transform(X_raw[te_out])
            Z_te    = ts.transform(C_te)
            scaler  = StandardScaler().fit(Z_tr)
            Z_tr    = scaler.transform(Z_tr)
            Z_te    = scaler.transform(Z_te)
        else:
            scaler  = StandardScaler().fit(X_feat[tr_out])
            Z_tr    = scaler.transform(X_feat[tr_out])
            Z_te    = scaler.transform(X_feat[te_out])

        y_tr = y[tr_out]
        y_te = y[te_out]
        g_tr = subjects[tr_out]

        # Inner GroupKFold over train subjects to pick hyperparam
        gkf = GroupKFold(n_splits=INNER_K)
        best_param, best_score = None, -np.inf
        for p in spec["grid"]:
            fold_scores = []
            for inner_tr, inner_va in gkf.split(Z_tr, y_tr, groups=g_tr):
                clf = spec["build"](p)
                clf.fit(Z_tr[inner_tr], y_tr[inner_tr])
                s = f1_score(y_tr[inner_va], clf.predict(Z_tr[inner_va]),
                             average="weighted", zero_division=0)
                fold_scores.append(s)
            mean_s = float(np.mean(fold_scores))
            if mean_s > best_score:
                best_score, best_param = mean_s, p
        chosen_hparams.append({"test_subj": test_subj,
                               "best_" + spec["param_name"]: best_param,
                               "inner_f1": round(best_score * 100, 2)})

        # Refit on full outer-train with best hyperparam, evaluate on held-out subject
        clf = spec["build"](best_param)
        clf.fit(Z_tr, y_tr)
        y_pred = clf.predict(Z_te)
        try:
            y_proba = clf.predict_proba(Z_te)[:, 1]
        except Exception:
            y_proba = y_pred.astype(float)

        acc = accuracy_score(y_te, y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc,
                         "n": int(te_out.sum()),
                         "best_" + spec["param_name"]: best_param})
        all_true.extend(y_te.tolist())
        all_pred.extend(y_pred.tolist())
        all_proba.extend(np.asarray(y_proba).tolist())
        print(f"   {test_subj}: {acc:5.2f}%  (inner-best {spec['param_name']}={best_param})")

    all_true  = np.array(all_true)
    all_pred  = np.array(all_pred)
    all_proba = np.array(all_proba, dtype=float)

    acc = accuracy_score(all_true, all_pred) * 100
    prec = precision_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    rec  = recall_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    f1   = f1_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    kap  = cohen_kappa_score(all_true, all_pred)
    cm   = confusion_matrix(all_true, all_pred)
    try:
        auc = roc_auc_score(all_true, all_proba) * 100
    except Exception:
        auc = 0.0
    accs = [r["accuracy"] for r in per_subj]

    out = {
        "accuracy": round(acc, 2),
        "accuracy_mean": round(float(np.mean(accs)), 2),
        "accuracy_std":  round(float(np.std(accs)),  2),
        "accuracy_min":  round(float(np.min(accs)),  2),
        "accuracy_max":  round(float(np.max(accs)),  2),
        "precision": round(prec, 2), "recall": round(rec, 2),
        "f1_score":  round(f1, 2),   "auc_roc": round(auc, 2),
        "kappa": round(float(kap), 4),
        "confusion_matrix": cm.tolist(),
        "per_subject": per_subj,
        "inner_cv": chosen_hparams,
        "fit_time_s": round(time.time() - t_m, 1),
    }
    print(f"  >> overall acc={acc:.2f}  f1={f1:.2f}  auc={auc:.2f}  "
          f"kappa={kap:.4f}  t={out['fit_time_s']}s")
    return out


results = {}
for name, spec in GRIDS.items():
    results[name] = nested_loso(name, spec)

best_model = max(results, key=lambda k: results[k]["f1_score"])
payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": len(SUBJECTS),
        "epoch_duration_s": EPOCH_SEC,
        "total_epochs": int(X_raw.shape[0]),
        "awake_epochs": int((y == 0).sum()),
        "drowsy_epochs": int((y == 1).sum()),
        "cross_validation": "Nested LOSO (outer) + GroupKFold(3) (inner)",
        "selection_metric": "weighted F1",
        "version": "v7",
    },
    "model_comparison": results,
    "best_model": best_model,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nBest: {best_model} -> F1={results[best_model]['f1_score']}")
print(f"Wrote {RESULTS_FILE}")
print(f"Total elapsed: {time.time()-t0:.1f}s")
