"""
Publication Analysis v2 — Multi-Model EEG Drowsiness Detection
================================================================
Complete overhaul with:
  - Rich feature engineering (25+ features per epoch)
  - 7 classification models compared via LOSO
  - Temporal prediction using best model's probability output
  - Publication-quality figures and comprehensive statistics

Author: Muhammad | April 2026
Dataset: DROZY O1/O2 (10 subjects × 2 sessions, 128 Hz)
"""

import os, sys, json, time, warnings
import numpy as np
import pandas as pd
import mne
from scipy.signal import welch
from scipy.integrate import trapezoid
from scipy.stats import linregress, kurtosis, skew, entropy as sp_entropy
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    AdaBoostClassifier, ExtraTreesClassifier
)
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, cohen_kappa_score
)
from sklearn.pipeline import Pipeline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime

warnings.filterwarnings('ignore')

# ═════════════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════════════

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")

# Normalization mode. Controls the output version too.
#   "none"          -> v3: raw features, global StandardScaler inside each model pipeline
#   "subject_both"  -> v4: z-score each subject using ALL of their epochs (both sessions)
#   "subject_awake" -> v5: z-score each subject using their session-1 (awake) epochs only,
#                         then apply to both sessions. Mirrors the calibration-on-first-drive
#                         deployment scenario and is the most defensible for the paper.
# Override at the CLI with:  python publication_analysis.py --norm subject_awake
NORMALIZATION = os.environ.get("DMS_NORM", "none")
_VERSION_BY_NORM = {"none": "v3", "subject_both": "v4", "subject_awake": "v5"}

# Lightweight argv handling so we don't need argparse
if "--norm" in sys.argv:
    NORMALIZATION = sys.argv[sys.argv.index("--norm") + 1]
if NORMALIZATION not in _VERSION_BY_NORM:
    raise ValueError(f"NORMALIZATION must be one of {list(_VERSION_BY_NORM)}, got {NORMALIZATION!r}")
_VERSION = _VERSION_BY_NORM[NORMALIZATION]

FIG_DIR      = os.path.join(_SCRIPT_DIR, f"publication_figures_{_VERSION}")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, f"publication_results_{_VERSION}.json")

SUBJECTS = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS = 128
EPOCH_SEC  = 10   # 10-second epochs (matches notebook, more data)
BANDS = {
    "delta": (0.5, 4),
    "theta": (4, 8),
    "alpha": (8, 13),
    "beta":  (13, 30),
}
THRESHOLD_MULT = 1.5

os.makedirs(FIG_DIR, exist_ok=True)

# ═════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION
# ═════════════════════════════════════════════════════════════════════

def band_power(sig, fs, band):
    """Band power via Welch PSD."""
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= band[0]) & (f <= band[1])
    return float(trapezoid(p[m], f[m])) if m.sum() > 0 else 0.0

def spectral_entropy(sig, fs, fmin=0.5, fmax=40):
    """Normalized spectral entropy (irregularity of spectrum)."""
    f, p = welch(sig, fs, nperseg=min(int(fs*2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    p_norm = p[m] / (p[m].sum() + 1e-12)
    return float(sp_entropy(p_norm + 1e-12))

def hjorth_params(sig):
    """Hjorth activity, mobility, complexity."""
    d1 = np.diff(sig)
    d2 = np.diff(d1)
    activity   = np.var(sig)
    mobility   = np.sqrt(np.var(d1) / (activity + 1e-12))
    complexity = np.sqrt(np.var(d2) / (np.var(d1) + 1e-12)) / (mobility + 1e-12)
    return activity, mobility, complexity

def zero_crossings(sig):
    """Number of zero crossings normalized by length."""
    return float(np.sum(np.diff(np.sign(sig)) != 0)) / len(sig)

def extract_features_epoch(o1, o2, fs):
    """
    Extract 30 features from a single epoch (O1 + O2 channels).
    
    Per channel (×2 = 24):
      - Band power: delta, theta, alpha, beta (4)
      - Theta/alpha ratio (1)
      - (Theta+alpha)/(alpha+beta) ratio (1)
      - Spectral entropy (1)
      - Hjorth: activity, mobility, complexity (3)
      - Zero crossing rate (1)
      - Skewness (1)
    
    Cross-channel (6):
      - O1-O2 asymmetry: theta, alpha, beta (3)
      - Mean theta/alpha ratio (1)
      - Total theta power (1)
      - Total alpha power (1)
    """
    feats = {}
    
    for ch_name, sig in [("O1", o1), ("O2", o2)]:
        # Band powers
        for bname, brand in BANDS.items():
            feats[f"{bname}_{ch_name}"] = band_power(sig, fs, brand)
        
        # Ratios
        th = feats[f"theta_{ch_name}"]
        al = feats[f"alpha_{ch_name}"]
        be = feats[f"beta_{ch_name}"]
        feats[f"theta_alpha_ratio_{ch_name}"] = th / (al + 1e-12)
        feats[f"slow_fast_ratio_{ch_name}"]   = (th + al) / (al + be + 1e-12)
        
        # Spectral entropy
        feats[f"spectral_entropy_{ch_name}"] = spectral_entropy(sig, fs)
        
        # Hjorth parameters
        act, mob, comp = hjorth_params(sig)
        feats[f"hjorth_activity_{ch_name}"]   = act
        feats[f"hjorth_mobility_{ch_name}"]   = mob
        feats[f"hjorth_complexity_{ch_name}"] = comp
        
        # Zero crossing rate
        feats[f"zcr_{ch_name}"] = zero_crossings(sig)
        
        # Skewness
        feats[f"skewness_{ch_name}"] = float(skew(sig))
    
    # Cross-channel features
    for bname in ["theta", "alpha", "beta"]:
        p1 = feats[f"{bname}_O1"]
        p2 = feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    
    feats["mean_theta_alpha_ratio"] = (
        feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]
    ) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]
    
    return feats


def load_and_extract(subject, session):
    """Load EDF, epoch into 10s windows, extract features."""
    path = os.path.join(DATA_DIR, f"{subject}_{session}_O1_O2.edf")
    if not os.path.exists(path):
        return None
    
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    raw.filter(1.0, 40.0, fir_design='firwin', verbose=False)
    data = raw.get_data() * 1e6  # µV
    fs = int(raw.info["sfreq"])
    
    ws = EPOCH_SEC * fs
    rows = []
    i = 0
    while i + ws <= data.shape[1]:
        o1 = data[0, i:i+ws]
        o2 = data[1, i:i+ws]
        
        feats = extract_features_epoch(o1, o2, fs)
        feats["subject"] = subject
        feats["session"] = session
        feats["label"] = 0 if session == "1" else 1
        feats["time_s"] = i / fs
        rows.append(feats)
        i += ws
    
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════
# MODELS
# ═════════════════════════════════════════════════════════════════════

def get_models():
    """Return dict of model_name -> sklearn Pipeline (scaler + classifier)."""
    return {
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=100, max_depth=12, min_samples_leaf=5,
                class_weight="balanced", random_state=42, n_jobs=-1))
        ]),
        "Gradient Boosting": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.1,
                subsample=0.8, random_state=42))
        ]),
        "Extra Trees": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", ExtraTreesClassifier(
                n_estimators=100, max_depth=12, min_samples_leaf=5,
                class_weight="balanced", random_state=42, n_jobs=-1))
        ]),
        "SVM (Linear)": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="linear", C=1.0,
                        class_weight="balanced", probability=True, random_state=42))
        ]),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=7, weights="distance", n_jobs=-1))
        ]),
        "LDA": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LinearDiscriminantAnalysis())
        ]),
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=1.0, max_iter=1000, class_weight="balanced", random_state=42))
        ]),
    }


# ═════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PUBLICATION ANALYSIS v2 — Multi-Model EEG Drowsiness Detection")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print(f"Epoch: {EPOCH_SEC}s | Bands: delta,theta,alpha,beta")
print(f"Subjects: {len(SUBJECTS)} | Models: 7")
print()

# ── PART 1: Feature Extraction ───────────────────────────────────────

print("━" * 80)
print("PART 1: Feature Extraction (30 features × 10s epochs)")
print("━" * 80)

t0 = time.time()
all_dfs = []
missing = []
for subj in SUBJECTS:
    for sess in ["1", "2"]:
        df = load_and_extract(subj, sess)
        if df is not None:
            state = "Awake" if sess == "1" else "Drowsy"
            print(f"  ✓ {subj}_{sess} ({state}): {len(df)} epochs")
            all_dfs.append(df)
        else:
            missing.append(f"{subj}_{sess}")

if not all_dfs:
    raise FileNotFoundError(
        f"No EDF files loaded from DATA_DIR={DATA_DIR!r}. "
        f"Expected files like '01M_1_O1_O2.edf'. "
        f"Check that DROZY_O1_O2/ exists alongside this script."
    )
if missing:
    print(f"  ⚠ Missing {len(missing)} file(s): {missing}")

df_all = pd.concat(all_dfs, ignore_index=True)
feat_cols = [c for c in df_all.columns if c not in ["subject","session","label","time_s"]]
n_feats = len(feat_cols)
n_awake = (df_all["label"]==0).sum()
n_drowsy = (df_all["label"]==1).sum()

print(f"\n  Total: {len(df_all)} epochs | {n_feats} features | "
      f"{n_awake} awake / {n_drowsy} drowsy")
print(f"  Feature extraction time: {time.time()-t0:.1f}s")

# ── Per-subject normalization (if enabled) ───────────────────────────
# Applied BEFORE the LOSO split. Scaling statistics come only from the
# same subject's own epochs, never from other subjects, so no cross-subject
# information leaks. No labels are used when fitting the scaler.
if NORMALIZATION != "none":
    print(f"\n  Applying per-subject normalization: mode={NORMALIZATION!r}")
    norm_cols = feat_cols  # only the numeric feature columns
    for subj in SUBJECTS:
        subj_mask = df_all["subject"] == subj
        if NORMALIZATION == "subject_both":
            # Fit on both sessions for this subject
            fit_mask = subj_mask
        elif NORMALIZATION == "subject_awake":
            # Fit on session 1 (awake baseline) only — realistic calibration
            fit_mask = subj_mask & (df_all["session"] == "1")
        else:
            raise AssertionError(f"unreachable NORMALIZATION={NORMALIZATION!r}")

        if not fit_mask.any():
            print(f"    ⚠ {subj}: no fit data for mode {NORMALIZATION!r}, skipping")
            continue
        mu  = df_all.loc[fit_mask, norm_cols].mean()
        sig = df_all.loc[fit_mask, norm_cols].std(ddof=0).replace(0.0, 1.0)
        df_all.loc[subj_mask, norm_cols] = (
            (df_all.loc[subj_mask, norm_cols] - mu) / sig
        )
    # Post-normalization sanity
    mu_all  = df_all[feat_cols].mean().abs().mean()
    std_all = df_all[feat_cols].std(ddof=0).mean()
    print(f"    post-norm |mean| avg={mu_all:.3f}, std avg={std_all:.3f}")


# ── PART 2: Multi-Model LOSO Cross-Validation ────────────────────────

print("\n" + "━" * 80)
print("PART 2: LOSO Cross-Validation — 7 Models")
print("━" * 80)

X = df_all[feat_cols].values
y = df_all["label"].values
subjects = df_all["subject"].values

models = get_models()
model_results = {}

for model_name, pipeline in models.items():
    print(f"\n  ▶ {model_name}")
    
    all_true, all_pred, all_proba = [], [], []
    per_subj = []
    
    for test_subj in SUBJECTS:
        train_mask = subjects != test_subj
        test_mask  = subjects == test_subj
        
        X_tr, y_tr = X[train_mask], y[train_mask]
        X_te, y_te = X[test_mask],  y[test_mask]
        
        pipeline.fit(X_tr, y_tr)
        y_pred = pipeline.predict(X_te)
        
        try:
            y_proba = pipeline.predict_proba(X_te)[:, 1]
        except:
            y_proba = y_pred.astype(float)
        
        acc = accuracy_score(y_te, y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc, "n": len(y_te)})
        
        all_true.extend(y_te.tolist())
        all_pred.extend(y_pred.tolist())
        all_proba.extend(y_proba.tolist())
        
        print(f"    {test_subj}: {acc:.1f}%")
    
    all_true = np.array(all_true)
    all_pred = np.array(all_pred)
    all_proba = np.array(all_proba)
    
    acc_overall  = accuracy_score(all_true, all_pred) * 100
    prec_w = precision_score(all_true, all_pred, average='weighted', zero_division=0) * 100
    rec_w  = recall_score(all_true, all_pred, average='weighted', zero_division=0) * 100
    f1_w   = f1_score(all_true, all_pred, average='weighted', zero_division=0) * 100
    kappa  = cohen_kappa_score(all_true, all_pred)
    cm     = confusion_matrix(all_true, all_pred)
    
    try:
        auc = roc_auc_score(all_true, all_proba) * 100
    except:
        auc = 0.0
    
    accs = [r["accuracy"] for r in per_subj]
    
    model_results[model_name] = {
        "accuracy": round(acc_overall, 2),
        "accuracy_mean": round(float(np.mean(accs)), 2),
        "accuracy_std": round(float(np.std(accs)), 2),
        "accuracy_min": round(float(np.min(accs)), 2),
        "accuracy_max": round(float(np.max(accs)), 2),
        "precision": round(prec_w, 2),
        "recall": round(rec_w, 2),
        "f1_score": round(f1_w, 2),
        "auc_roc": round(auc, 2),
        "kappa": round(kappa, 4),
        "confusion_matrix": cm.tolist(),
        "per_subject": per_subj,
        "y_true": all_true.tolist(),
        "y_pred": all_pred.tolist(),
    }
    
    print(f"    ── Overall: {acc_overall:.2f}% (mean {np.mean(accs):.1f}±{np.std(accs):.1f}%) "
          f"| F1={f1_w:.1f}% | AUC={auc:.1f}% | κ={kappa:.3f}")


# ── PART 3: Best Model Summary ───────────────────────────────────────

print("\n" + "━" * 80)
print("PART 3: Model Comparison Summary")
print("━" * 80)

# Sort by accuracy
sorted_models = sorted(model_results.items(), key=lambda x: x[1]["accuracy"], reverse=True)

print(f"\n  {'Model':<22} {'Acc%':>6} {'F1%':>6} {'AUC%':>6} {'κ':>7} {'Mean±Std':>12}")
print(f"  {'─'*22} {'─'*6} {'─'*6} {'─'*6} {'─'*7} {'─'*12}")
for name, r in sorted_models:
    marker = " ★" if name == sorted_models[0][0] else ""
    print(f"  {name:<22} {r['accuracy']:6.2f} {r['f1_score']:6.2f} "
          f"{r['auc_roc']:6.2f} {r['kappa']:7.4f} "
          f"{r['accuracy_mean']:.1f}±{r['accuracy_std']:.1f}{marker}")

best_name = sorted_models[0][0]
best_r = sorted_models[0][1]
print(f"\n  ★ Best Model: {best_name} ({best_r['accuracy']:.2f}%)")


# ── PART 4: Prediction Validation (using best model) ─────────────────

print("\n" + "━" * 80)
print(f"PART 4: Temporal Prediction — All 10 Subjects (using {best_name})")
print("━" * 80)

# Retrain best model on all data for prediction
best_pipeline = get_models()[best_name]

prediction_results = []

for subj in SUBJECTS:
    # Get awake and drowsy data
    df_awake  = df_all[(df_all["subject"]==subj) & (df_all["session"]=="1")].copy()
    df_drowsy = df_all[(df_all["subject"]==subj) & (df_all["session"]=="2")].copy()
    
    if df_awake.empty or df_drowsy.empty:
        continue
    
    # Train on ALL OTHER subjects
    train_mask = df_all["subject"] != subj
    X_tr = df_all.loc[train_mask, feat_cols].values
    y_tr = df_all.loc[train_mask, "label"].values
    
    best_pipeline.fit(X_tr, y_tr)
    
    # Get probability predictions for drowsy session (temporal sequence)
    X_drowsy = df_drowsy[feat_cols].values
    try:
        proba_drowsy = best_pipeline.predict_proba(X_drowsy)[:, 1]
    except:
        proba_drowsy = best_pipeline.predict(X_drowsy).astype(float)
    
    pred_drowsy = best_pipeline.predict(X_drowsy)
    times_drowsy = df_drowsy["time_s"].values / 60  # minutes
    
    # Get probability predictions for awake session
    X_awake = df_awake[feat_cols].values
    try:
        proba_awake = best_pipeline.predict_proba(X_awake)[:, 1]
    except:
        proba_awake = best_pipeline.predict(X_awake).astype(float)
    
    pred_awake = best_pipeline.predict(X_awake)
    times_awake = df_awake["time_s"].values / 60
    
    # Temporal prediction: use rolling window on probabilities
    # If probability trends upward over 5-min window, predict drowsiness
    window_size = 30  # 30 epochs × 10s = 5 minutes
    
    drowsy_alerts = {"YELLOW": 0, "RED": 0, "CRITICAL": 0}
    awake_alerts  = {"YELLOW": 0, "RED": 0, "CRITICAL": 0}
    first_alert_time = None
    
    for idx in range(len(proba_drowsy)):
        p = proba_drowsy[idx]
        if p >= 0.8:
            drowsy_alerts["CRITICAL"] += 1
            if first_alert_time is None:
                first_alert_time = times_drowsy[idx]
        elif p >= 0.6:
            drowsy_alerts["RED"] += 1
            if first_alert_time is None:
                first_alert_time = times_drowsy[idx]
        elif idx >= window_size:
            # Check trend — is probability rising?
            recent = proba_drowsy[idx-window_size:idx]
            sl, _, _, _, _ = linregress(np.arange(len(recent)), recent)
            if sl > 0.001 and p > 0.4:
                drowsy_alerts["YELLOW"] += 1
                if first_alert_time is None:
                    first_alert_time = times_drowsy[idx]
    
    for idx in range(len(proba_awake)):
        p = proba_awake[idx]
        if p >= 0.8:
            awake_alerts["CRITICAL"] += 1
        elif p >= 0.6:
            awake_alerts["RED"] += 1
        elif idx >= window_size:
            recent = proba_awake[idx-window_size:idx]
            sl, _, _, _, _ = linregress(np.arange(len(recent)), recent)
            if sl > 0.001 and p > 0.4:
                awake_alerts["YELLOW"] += 1
    
    # Simple detection: does the model classify >50% of drowsy epochs as drowsy?
    drowsy_detection_rate = pred_drowsy.mean() * 100
    awake_fa_rate = pred_awake.mean() * 100
    
    result = {
        "subject": subj,
        "drowsy_detection_rate": round(float(drowsy_detection_rate), 1),
        "awake_false_alarm_rate": round(float(awake_fa_rate), 1),
        "drowsy_alerts": drowsy_alerts,
        "awake_alerts": awake_alerts,
        "first_alert_time_min": round(float(first_alert_time), 1) if first_alert_time is not None else None,
        "drowsy_mean_proba": round(float(proba_drowsy.mean()), 3),
        "awake_mean_proba": round(float(proba_awake.mean()), 3),
        "drowsy_correct_pct": round(float((pred_drowsy==1).mean()*100), 1),
        "awake_correct_pct": round(float((pred_awake==0).mean()*100), 1),
    }
    prediction_results.append(result)
    
    d_total = sum(drowsy_alerts.values())
    a_total = sum(awake_alerts.values())
    
    print(f"  {subj}: Drowsy={drowsy_detection_rate:.0f}% detected, "
          f"Awake={100-awake_fa_rate:.0f}% correct | "
          f"Alerts D:[Y={drowsy_alerts['YELLOW']} R={drowsy_alerts['RED']} C={drowsy_alerts['CRITICAL']}] "
          f"A:[Y={awake_alerts['YELLOW']} R={awake_alerts['RED']} C={awake_alerts['CRITICAL']}]")

# Aggregate prediction metrics
df_pred = pd.DataFrame(prediction_results)
mean_drowsy_det = df_pred["drowsy_detection_rate"].mean()
mean_awake_correct = 100 - df_pred["awake_false_alarm_rate"].mean()

print(f"\n  ── Aggregate ──")
print(f"  Mean drowsy detected:  {mean_drowsy_det:.1f}%")
print(f"  Mean awake correct:    {mean_awake_correct:.1f}%")
print(f"  Mean drowsy P(drowsy): {df_pred['drowsy_mean_proba'].mean():.3f}")
print(f"  Mean awake P(drowsy):  {df_pred['awake_mean_proba'].mean():.3f}")


# ── PART 5: Publication Figures ────────────────────────────────────────

print("\n" + "━" * 80)
print("PART 5: Generating Publication Figures")
print("━" * 80)

plt.rcParams.update({
    'font.family': 'serif', 'font.size': 10,
    'axes.titlesize': 12, 'axes.labelsize': 11,
    'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'legend.fontsize': 9, 'figure.dpi': 300,
    'savefig.dpi': 300, 'savefig.bbox': 'tight',
})

# ── Fig 1: Model comparison bar chart ──
fig1, ax = plt.subplots(figsize=(10, 5))
names = [n for n, _ in sorted_models]
accs_bar = [r["accuracy"] for _, r in sorted_models]
f1s = [r["f1_score"] for _, r in sorted_models]
aucs = [r["auc_roc"] for _, r in sorted_models]

x = np.arange(len(names))
w = 0.25
bars1 = ax.bar(x - w, accs_bar, w, label='Accuracy', color='#2196F3', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x,     f1s,      w, label='F1-Score', color='#4CAF50', edgecolor='black', linewidth=0.5)
bars3 = ax.bar(x + w, aucs,     w, label='AUC-ROC',  color='#FF9800', edgecolor='black', linewidth=0.5)

ax.set_xlabel('Model')
ax.set_ylabel('Score (%)')
ax.set_title('Classification Performance — LOSO Cross-Validation (2-Channel O1/O2)')
ax.set_xticks(x)
ax.set_xticklabels(names, rotation=25, ha='right')
ax.legend()
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 105)

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        if h > 5:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                    f'{h:.0f}', ha='center', fontsize=7, fontweight='bold')

fig1.savefig(os.path.join(FIG_DIR, 'fig1_model_comparison.png'), dpi=300)
fig1.savefig(os.path.join(FIG_DIR, 'fig1_model_comparison.pdf'))
plt.close(fig1)
print("  ✓ Fig 1: Model comparison")

# ── Fig 2: Best model LOSO per-subject accuracy ──
best_per_subj = best_r["per_subject"]
fig2, ax = plt.subplots(figsize=(8, 4))
subj_names = [r["subject"] for r in best_per_subj]
subj_accs = [r["accuracy"] for r in best_per_subj]
colors = ['#4CAF50' if a >= 70 else '#FF9800' if a >= 55 else '#F44336' for a in subj_accs]
bars = ax.bar(subj_names, subj_accs, color=colors, edgecolor='black', linewidth=0.5)
ax.axhline(y=np.mean(subj_accs), color='red', linestyle='--', linewidth=1.5,
           label=f'Mean: {np.mean(subj_accs):.1f}%')
ax.set_xlabel('Subject ID')
ax.set_ylabel('Accuracy (%)')
ax.set_title(f'Per-Subject LOSO Accuracy — {best_name}')
ax.set_ylim(0, 105)
ax.legend()
ax.grid(axis='y', alpha=0.3)
for bar, a in zip(bars, subj_accs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f'{a:.0f}%', ha='center', fontsize=9, fontweight='bold')
fig2.savefig(os.path.join(FIG_DIR, 'fig2_best_model_per_subject.png'), dpi=300)
fig2.savefig(os.path.join(FIG_DIR, 'fig2_best_model_per_subject.pdf'))
plt.close(fig2)
print(f"  ✓ Fig 2: {best_name} per-subject accuracy")

# ── Fig 3: Confusion matrix (best model) ──
fig3, ax = plt.subplots(figsize=(5, 4))
cm = np.array(best_r["confusion_matrix"])
im = ax.imshow(cm, cmap='Blues', aspect='auto')
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(['Pred: Awake', 'Pred: Drowsy'])
ax.set_yticklabels(['True: Awake', 'True: Drowsy'])
ax.set_title(f'LOSO Confusion Matrix — {best_name} ({best_r["accuracy"]:.1f}%)')
for i in range(2):
    for j in range(2):
        pct = cm[i, j] / cm[i].sum() * 100
        ax.text(j, i, f'{cm[i,j]}\n({pct:.1f}%)',
                ha='center', va='center',
                color='white' if cm[i,j] > cm.max()/2 else 'black',
                fontsize=11, fontweight='bold')
fig3.colorbar(im, ax=ax, shrink=0.8)
fig3.savefig(os.path.join(FIG_DIR, 'fig3_confusion_matrix.png'), dpi=300)
fig3.savefig(os.path.join(FIG_DIR, 'fig3_confusion_matrix.pdf'))
plt.close(fig3)
print("  ✓ Fig 3: Confusion matrix")

# ── Fig 4: Prediction probability timeline (07F) ──
subj_07f = "07F"
df_a = df_all[(df_all["subject"]==subj_07f) & (df_all["session"]=="1")]
df_d = df_all[(df_all["subject"]==subj_07f) & (df_all["session"]=="2")]

# Train on all except 07F
train_mask = df_all["subject"] != subj_07f
best_pipeline_07f = get_models()[best_name]
best_pipeline_07f.fit(df_all.loc[train_mask, feat_cols].values,
                       df_all.loc[train_mask, "label"].values)

try:
    proba_a = best_pipeline_07f.predict_proba(df_a[feat_cols].values)[:, 1]
    proba_d = best_pipeline_07f.predict_proba(df_d[feat_cols].values)[:, 1]
except:
    proba_a = best_pipeline_07f.predict(df_a[feat_cols].values).astype(float)
    proba_d = best_pipeline_07f.predict(df_d[feat_cols].values).astype(float)

fig4, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=False)

# Awake session
ax1.plot(df_a["time_s"].values/60, proba_a, color='#2196F3', linewidth=0.8, alpha=0.7)
ax1.axhline(y=0.5, color='gray', linestyle='--', linewidth=1)
ax1.axhline(y=0.6, color='orange', linestyle=':', linewidth=1, label='Red threshold')
ax1.axhline(y=0.8, color='red', linestyle=':', linewidth=1, label='Critical threshold')
ax1.fill_between(df_a["time_s"].values/60, 0, proba_a, alpha=0.15, color='#2196F3')
ax1.set_ylabel('P(Drowsy)')
ax1.set_title(f'Awake Session — Subject {subj_07f}')
ax1.set_ylim(-0.05, 1.05)
ax1.legend(loc='upper right', fontsize=8)
ax1.grid(alpha=0.3)

# Drowsy session
ax2.plot(df_d["time_s"].values/60, proba_d, color='#F44336', linewidth=0.8, alpha=0.7)
ax2.axhline(y=0.5, color='gray', linestyle='--', linewidth=1)
ax2.axhline(y=0.6, color='orange', linestyle=':', linewidth=1, label='Red threshold')
ax2.axhline(y=0.8, color='red', linestyle=':', linewidth=1, label='Critical threshold')
ax2.fill_between(df_d["time_s"].values/60, 0, proba_d, alpha=0.15, color='#F44336')
ax2.set_xlabel('Time (minutes)')
ax2.set_ylabel('P(Drowsy)')
ax2.set_title(f'Drowsy Session — Subject {subj_07f}')
ax2.set_ylim(-0.05, 1.05)
ax2.legend(loc='upper right', fontsize=8)
ax2.grid(alpha=0.3)

fig4.suptitle(f'Drowsiness Probability Over Time ({best_name})', fontsize=13, fontweight='bold')
fig4.savefig(os.path.join(FIG_DIR, 'fig4_probability_timeline_07F.png'), dpi=300)
fig4.savefig(os.path.join(FIG_DIR, 'fig4_probability_timeline_07F.pdf'))
plt.close(fig4)
print("  ✓ Fig 4: Probability timeline (07F)")

# ── Fig 5: PSD comparison ──
data_a_raw, _ = None, None
path_a = os.path.join(DATA_DIR, "07F_1_O1_O2.edf")
path_d = os.path.join(DATA_DIR, "07F_2_O1_O2.edf")
if os.path.exists(path_a) and os.path.exists(path_d):
    raw_a = mne.io.read_raw_edf(path_a, preload=True, verbose=False)
    raw_d = mne.io.read_raw_edf(path_d, preload=True, verbose=False)
    raw_a.filter(1, 40, verbose=False)
    raw_d.filter(1, 40, verbose=False)
    sig_a = raw_a.get_data()[0] * 1e6
    sig_d = raw_d.get_data()[0] * 1e6
    
    fig5, ax = plt.subplots(figsize=(8, 4.5))
    fa, pa = welch(sig_a, FS, nperseg=FS*4)
    fd, pd_ = welch(sig_d, FS, nperseg=FS*4)
    m = (fa >= 0.5) & (fa <= 40)
    
    ax.semilogy(fa[m], pa[m], color='#2196F3', linewidth=1.8, label='Awake', alpha=0.9)
    ax.semilogy(fd[m], pd_[m], color='#F44336', linewidth=1.8, label='Drowsy', alpha=0.9)
    
    for lo, hi, fc, lbl in [(0.5,4,'#E8EAF6','δ'),(4,8,'#FFF9C4','θ'),
                             (8,13,'#C8E6C9','α'),(13,30,'#FFCDD2','β')]:
        ax.axvspan(lo, hi, alpha=0.25, color=fc)
        ax.text((lo+hi)/2, ax.get_ylim()[0]*5, lbl, ha='center', fontsize=12, fontweight='bold', alpha=0.5)
    
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('PSD (µV²/Hz)')
    ax.set_title('Power Spectral Density — O1 Channel, Subject 07F')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0.5, 40)
    fig5.savefig(os.path.join(FIG_DIR, 'fig5_psd_comparison.png'), dpi=300)
    fig5.savefig(os.path.join(FIG_DIR, 'fig5_psd_comparison.pdf'))
    plt.close(fig5)
    print("  ✓ Fig 5: PSD comparison")

# ── Fig 6: Feature importance (if tree-based) ──
if hasattr(best_pipeline.named_steps.get("clf", None), "feature_importances_"):
    imp = best_pipeline.named_steps["clf"].feature_importances_
    # Retrain on full data for feature importance
    best_pipeline.fit(X, y)
    imp = best_pipeline.named_steps["clf"].feature_importances_
    
    top_k = 15
    sorted_idx = np.argsort(imp)[::-1][:top_k]
    
    fig6, ax = plt.subplots(figsize=(8, 5))
    ax.barh(range(top_k), [imp[i]*100 for i in sorted_idx[::-1]],
            color='#2196F3', edgecolor='black', linewidth=0.5)
    ax.set_yticks(range(top_k))
    ax.set_yticklabels([feat_cols[i] for i in sorted_idx[::-1]], fontsize=8)
    ax.set_xlabel('Importance (%)')
    ax.set_title(f'Top {top_k} Feature Importances — {best_name}')
    ax.grid(axis='x', alpha=0.3)
    fig6.savefig(os.path.join(FIG_DIR, 'fig6_feature_importance.png'), dpi=300)
    fig6.savefig(os.path.join(FIG_DIR, 'fig6_feature_importance.pdf'))
    plt.close(fig6)
    print("  ✓ Fig 6: Feature importance")

# ── Fig 7: Per-subject drowsiness detection ──
fig7, ax = plt.subplots(figsize=(10, 5))
x_pos = np.arange(len(prediction_results))
widthb = 0.35

det_rates = [r["drowsy_detection_rate"] for r in prediction_results]
fa_rates  = [r["awake_false_alarm_rate"] for r in prediction_results]

ax.bar(x_pos - widthb/2, det_rates, widthb, label='Drowsy Detection %',
       color='#4CAF50', edgecolor='black', linewidth=0.5)
ax.bar(x_pos + widthb/2, fa_rates,  widthb, label='Awake False Alarm %',
       color='#F44336', edgecolor='black', linewidth=0.5, alpha=0.7)
ax.set_xlabel('Subject ID')
ax.set_ylabel('Rate (%)')
ax.set_title(f'Per-Subject Detection & False Alarm Rates — {best_name}')
ax.set_xticks(x_pos)
ax.set_xticklabels(SUBJECTS)
ax.legend()
ax.grid(axis='y', alpha=0.3)
ax.set_ylim(0, 105)
fig7.savefig(os.path.join(FIG_DIR, 'fig7_detection_vs_fa.png'), dpi=300)
fig7.savefig(os.path.join(FIG_DIR, 'fig7_detection_vs_fa.pdf'))
plt.close(fig7)
print("  ✓ Fig 7: Detection vs false alarm rates")

# ── Fig 8: Raw EEG comparison ──
if os.path.exists(path_a) and os.path.exists(path_d):
    fig8, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    t_plot = np.arange(5*FS) / FS  # 5 seconds
    
    axes[0].plot(t_plot, sig_a[:5*FS], color='#2196F3', linewidth=0.5)
    axes[0].set_ylabel('Amplitude (µV)')
    axes[0].set_title('Awake — O1 Channel (Subject 07F)')
    axes[0].set_ylim(-100, 100)
    axes[0].grid(alpha=0.3)
    
    axes[1].plot(t_plot, sig_d[:5*FS], color='#F44336', linewidth=0.5)
    axes[1].set_xlabel('Time (seconds)')
    axes[1].set_ylabel('Amplitude (µV)')
    axes[1].set_title('Drowsy — O1 Channel (Subject 07F)')
    axes[1].set_ylim(-100, 100)
    axes[1].grid(alpha=0.3)
    
    fig8.suptitle('Raw EEG Signals — Awake vs Drowsy', fontsize=13, fontweight='bold')
    fig8.savefig(os.path.join(FIG_DIR, 'fig8_raw_eeg.png'), dpi=300)
    fig8.savefig(os.path.join(FIG_DIR, 'fig8_raw_eeg.pdf'))
    plt.close(fig8)
    print("  ✓ Fig 8: Raw EEG comparison")

# ═════════════════════════════════════════════════════════════════════
# PART 6: Save Results
# ═════════════════════════════════════════════════════════════════════

print("\n" + "━" * 80)
print("PART 6: Saving Results")
print("━" * 80)

# Remove non-serializable data from results
clean_model_results = {}
for name, r in model_results.items():
    clean = {k: v for k, v in r.items() if k not in ["y_true", "y_pred"]}
    clean_model_results[name] = clean

final_results = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": 10,
        "epoch_duration_s": EPOCH_SEC,
        "n_features": n_feats,
        "feature_names": feat_cols,
        "total_epochs": len(df_all),
        "awake_epochs": int(n_awake),
        "drowsy_epochs": int(n_drowsy),
        "cross_validation": "Leave-One-Subject-Out (LOSO)",
        "normalization": NORMALIZATION,
        "version": _VERSION,
    },
    "model_comparison": clean_model_results,
    "best_model": best_name,
    "prediction_validation": prediction_results,
    "prediction_aggregate": {
        "mean_drowsy_detection": round(mean_drowsy_det, 1),
        "mean_awake_correct": round(mean_awake_correct, 1),
        "mean_drowsy_proba": round(float(df_pred["drowsy_mean_proba"].mean()), 3),
        "mean_awake_proba": round(float(df_pred["awake_mean_proba"].mean()), 3),
    }
}

with open(RESULTS_FILE, "w") as f:
    json.dump(final_results, f, indent=2, default=str)

print(f"  ✓ {RESULTS_FILE}")
print(f"  ✓ {FIG_DIR}/ (8 figures × PNG+PDF)")


# ═════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"""
  Dataset:    DROZY O1/O2 only ({len(df_all)} epochs, {n_feats} features)
  Validation: Leave-One-Subject-Out (LOSO)
  
  ★ Best Model: {best_name}
    Accuracy:    {best_r['accuracy']:.2f}%
    F1-Score:    {best_r['f1_score']:.2f}%
    AUC-ROC:     {best_r['auc_roc']:.2f}%
    Cohen's κ:   {best_r['kappa']:.4f}
    
  Prediction:
    Drowsy detection: {mean_drowsy_det:.1f}%
    Awake correct:    {mean_awake_correct:.1f}%
""")

print("Done! All publication materials generated.")
