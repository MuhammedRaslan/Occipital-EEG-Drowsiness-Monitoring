"""
Riemannian Geometry Baseline (Phase 1c, v6)
============================================
Trains Riemannian-geometry classifiers on raw EEG covariance matrices and
evaluates them under Leave-One-Subject-Out (LOSO) — matching the protocol
used by publication_analysis.py so that results are directly comparable
against v3/v4/v5 on the same epoch grid.

Pipelines:
  - MDM                         : Minimum Distance to Riemannian Mean
  - TS + LDA                    : Tangent space vectorization -> LDA
  - TS + Logistic Regression    : Tangent space vectorization -> LR
  - TS + SVM (linear)           : Tangent space vectorization -> linear SVM

Dataset: DROZY (O1/O2, 128 Hz, 10 subjects x 2 sessions).
Output : publication_results_v6.json, publication_figures_v6/

Author: Muhammad | April 2026
"""

import os, sys, io, json, time, warnings
# Force UTF-8 so box-drawing chars print on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import mne
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, cohen_kappa_score,
)
from pyriemann.estimation import Covariances
from pyriemann.tangentspace import TangentSpace
from pyriemann.classification import MDM
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")
FIG_DIR      = os.path.join(_SCRIPT_DIR, "publication_figures_v6")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v6.json")
os.makedirs(FIG_DIR, exist_ok=True)

SUBJECTS   = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS         = 128
EPOCH_SEC  = 10
COV_EST    = "oas"   # Oracle Approximating Shrinkage — robust for small n_samples


def load_raw_epochs(subject, session):
    """Load the subject-session EDF, band-pass filter, window into (n_epochs, 2, n_samples)."""
    path = os.path.join(DATA_DIR, f"{subject}_{session}_O1_O2.edf")
    if not os.path.exists(path):
        return None
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)
    data = raw.get_data() * 1e6  # µV
    fs = int(raw.info["sfreq"])
    ws = EPOCH_SEC * fs
    n_epochs = data.shape[1] // ws
    if n_epochs == 0:
        return None
    epochs = np.stack([data[:, i*ws:(i+1)*ws] for i in range(n_epochs)], axis=0)
    return epochs  # shape (n_epochs, 2, ws)


def get_pipelines():
    """Return dict of name -> sklearn-compatible Pipeline operating on (n, 2, ws) arrays."""
    cov = Covariances(estimator=COV_EST)
    return {
        "MDM (Riemann)": Pipeline([
            ("cov", Covariances(estimator=COV_EST)),
            ("clf", MDM(metric="riemann", n_jobs=-1)),
        ]),
        "TS + LDA (Riemann)": Pipeline([
            ("cov", Covariances(estimator=COV_EST)),
            ("ts",  TangentSpace(metric="riemann")),
            ("scaler", StandardScaler()),
            ("clf", LinearDiscriminantAnalysis()),
        ]),
        "TS + LogReg (Riemann)": Pipeline([
            ("cov", Covariances(estimator=COV_EST)),
            ("ts",  TangentSpace(metric="riemann")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=1.0, max_iter=2000, class_weight="balanced", random_state=42)),
        ]),
        "TS + SVM Linear (Riemann)": Pipeline([
            ("cov", Covariances(estimator=COV_EST)),
            ("ts",  TangentSpace(metric="riemann")),
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="linear", C=1.0,
                        class_weight="balanced", probability=True, random_state=42)),
        ]),
    }


print("=" * 80)
print("RIEMANNIAN BASELINE v6 — Covariance-based EEG Drowsiness Detection")
print("=" * 80)
print(f"Timestamp: {datetime.now()}")
print(f"Epoch: {EPOCH_SEC}s @ {FS}Hz | Channels: O1, O2 | Cov estimator: {COV_EST}")
print()

# ── PART 1: load raw epochs per subject-session ─────────────────────────
print("━" * 80)
print("PART 1: Raw-Epoch Loading")
print("━" * 80)

t0 = time.time()
X_list, y_list, subj_list = [], [], []
for subj in SUBJECTS:
    for sess in ["1", "2"]:
        ep = load_raw_epochs(subj, sess)
        if ep is None:
            print(f"  ⚠ missing: {subj}_{sess}")
            continue
        state = "Awake" if sess == "1" else "Drowsy"
        label = 0 if sess == "1" else 1
        X_list.append(ep)
        y_list.append(np.full(ep.shape[0], label, dtype=np.int64))
        subj_list.append(np.array([subj] * ep.shape[0]))
        print(f"  ✓ {subj}_{sess} ({state}): {ep.shape[0]} epochs, shape={ep.shape}")

X = np.concatenate(X_list, axis=0)            # (N, 2, ws)
y = np.concatenate(y_list, axis=0)            # (N,)
subjects = np.concatenate(subj_list, axis=0)  # (N,) string labels

print(f"\n  Total: {X.shape[0]} epochs | shape={X.shape} | "
      f"{int((y==0).sum())} awake / {int((y==1).sum())} drowsy")
print(f"  Load time: {time.time()-t0:.1f}s")


# ── PART 2: LOSO CV across Riemannian pipelines ─────────────────────────
print("\n" + "━" * 80)
print("PART 2: LOSO Cross-Validation — Riemannian Pipelines")
print("━" * 80)

pipelines = get_pipelines()
model_results = {}

for name, pipe in pipelines.items():
    print(f"\n  ▶ {name}")
    t_model = time.time()

    all_true, all_pred, all_proba = [], [], []
    per_subj = []

    for test_subj in SUBJECTS:
        tr = subjects != test_subj
        te = subjects == test_subj
        if not te.any():
            continue

        pipe.fit(X[tr], y[tr])
        y_pred = pipe.predict(X[te])

        try:
            y_proba = pipe.predict_proba(X[te])[:, 1]
        except Exception:
            # MDM: use negative distance to class-1 centroid as score
            try:
                dists = pipe.transform(X[te])   # (n, 2) distances
                y_proba = -dists[:, 1]
                y_proba = (y_proba - y_proba.min()) / (y_proba.ptp() + 1e-12)
            except Exception:
                y_proba = y_pred.astype(float)

        acc = accuracy_score(y[te], y_pred) * 100
        per_subj.append({"subject": test_subj, "accuracy": acc, "n": int(te.sum())})

        all_true.extend(y[te].tolist())
        all_pred.extend(y_pred.tolist())
        all_proba.extend(np.asarray(y_proba).tolist())

        print(f"    {test_subj}: {acc:.1f}%")

    all_true = np.array(all_true)
    all_pred = np.array(all_pred)
    all_proba = np.array(all_proba, dtype=float)

    acc_overall = accuracy_score(all_true, all_pred) * 100
    prec_w = precision_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    rec_w  = recall_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    f1_w   = f1_score(all_true, all_pred, average="weighted", zero_division=0) * 100
    kappa  = cohen_kappa_score(all_true, all_pred)
    cm     = confusion_matrix(all_true, all_pred)
    try:
        auc = roc_auc_score(all_true, all_proba) * 100
    except Exception:
        auc = 0.0

    accs = [r["accuracy"] for r in per_subj]
    model_results[name] = {
        "accuracy": round(acc_overall, 2),
        "accuracy_mean": round(float(np.mean(accs)), 2),
        "accuracy_std":  round(float(np.std(accs)),  2),
        "accuracy_min":  round(float(np.min(accs)),  2),
        "accuracy_max":  round(float(np.max(accs)),  2),
        "precision": round(prec_w, 2),
        "recall":    round(rec_w,  2),
        "f1_score":  round(f1_w,   2),
        "auc_roc":   round(auc,    2),
        "kappa":     round(float(kappa), 4),
        "confusion_matrix": cm.tolist(),
        "per_subject": per_subj,
        "fit_time_s": round(time.time() - t_model, 1),
    }

    print(f"    ▷ overall acc={acc_overall:.2f}%  f1={f1_w:.2f}  "
          f"auc={auc:.2f}  kappa={kappa:.4f}  t={time.time()-t_model:.1f}s")

# ── PART 3: persist ─────────────────────────────────────────────────────
best_model = max(model_results, key=lambda k: model_results[k]["f1_score"])
print(f"\n  Best (by weighted F1): {best_model} -> F1={model_results[best_model]['f1_score']}")

payload = {
    "timestamp": datetime.now().isoformat(),
    "methodology": {
        "dataset": "DROZY (O1/O2 only)",
        "subjects": len(SUBJECTS),
        "epoch_duration_s": EPOCH_SEC,
        "representation": "raw-signal covariance matrices (2x2 SPD)",
        "cov_estimator": COV_EST,
        "total_epochs": int(X.shape[0]),
        "awake_epochs": int((y == 0).sum()),
        "drowsy_epochs": int((y == 1).sum()),
        "cross_validation": "Leave-One-Subject-Out (LOSO)",
        "normalization": "none (Riemannian geometry is scale-equivariant)",
        "version": "v6",
    },
    "model_comparison": model_results,
    "best_model": best_model,
}

with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\n  Wrote {RESULTS_FILE}")
print(f"  Total elapsed: {time.time()-t0:.1f}s")
