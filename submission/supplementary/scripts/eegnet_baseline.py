"""
EEGNet Baseline (Phase 2d, v14)
================================
EEGNet (Lawhern et al. 2018) on raw O1/O2 windows under LOSO.
Compares an end-to-end CNN against the v11 lean handcrafted-feature LDA.

Pipeline
--------
1. Load DROZY O1/O2 EDFs, bandpass 1-40 Hz, epoch 10 s, cache to
   `epochs_raw_cache.npz` (shape = (N, 2, 1280)).
2. Per LOSO fold: per-subject z-score using train-fold awake epochs only,
   train EEGNet for EPOCHS epochs, predict on left-out subject.
3. Aggregate metrics across folds, save to `publication_results_v14.json`.

EEGNet hyperparameters: F1=8, D=2, F2=16, kernel sizes (1,32) and (1,16),
dropout 0.5, batch size 64, Adam lr=1e-3, EPOCHS=15.
"""

import os, sys, io, json, time, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import pandas as pd
import mne
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, cohen_kappa_score, confusion_matrix,
)
from datetime import datetime

warnings.filterwarnings("ignore")

_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(_SCRIPT_DIR, "DROZY_O1_O2")
RESULTS_FILE = os.path.join(_SCRIPT_DIR, "publication_results_v14.json")
RAW_CACHE    = os.path.join(_SCRIPT_DIR, "epochs_raw_cache.npz")
SUBJECTS     = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]
FS           = 128
EPOCH_SEC    = 10
WIN          = FS * EPOCH_SEC

EPOCHS       = 15
BATCH        = 64
LR           = 1e-3
SEED         = 42
DEVICE       = torch.device("cpu")


# ─── EEGNet ────────────────────────────────────────────────────────────
class EEGNet(nn.Module):
    def __init__(self, channels=2, samples=WIN, F1=8, D=2, F2=16,
                 kern1=32, kern2=16, drop=0.5, n_classes=2):
        super().__init__()
        # Block 1: temporal conv
        self.conv1 = nn.Conv2d(1, F1, (1, kern1), padding=(0, kern1 // 2), bias=False)
        self.bn1   = nn.BatchNorm2d(F1)
        # Depthwise spatial conv (per channel)
        self.dwconv = nn.Conv2d(F1, F1 * D, (channels, 1), groups=F1, bias=False)
        self.bn2    = nn.BatchNorm2d(F1 * D)
        self.pool1  = nn.AvgPool2d((1, 4))
        self.drop1  = nn.Dropout(drop)
        # Block 2: separable conv (depthwise + pointwise)
        self.sep_dw  = nn.Conv2d(F1 * D, F1 * D, (1, kern2),
                                 padding=(0, kern2 // 2), groups=F1 * D, bias=False)
        self.sep_pw  = nn.Conv2d(F1 * D, F2, (1, 1), bias=False)
        self.bn3     = nn.BatchNorm2d(F2)
        self.pool2   = nn.AvgPool2d((1, 8))
        self.drop2   = nn.Dropout(drop)
        # classifier
        with torch.no_grad():
            dummy = torch.zeros(1, 1, channels, samples)
            n_flat = self._features(dummy).shape[1]
        self.fc = nn.Linear(n_flat, n_classes)

    def _features(self, x):
        x = self.bn1(self.conv1(x))
        x = self.bn2(self.dwconv(x))
        x = F.elu(x)
        x = self.drop1(self.pool1(x))
        x = self.bn3(self.sep_pw(self.sep_dw(x)))
        x = F.elu(x)
        x = self.drop2(self.pool2(x))
        return torch.flatten(x, 1)

    def forward(self, x):
        return self.fc(self._features(x))


# ─── raw epoch cache ────────────────────────────────────────────────────
def build_raw_cache():
    if os.path.exists(RAW_CACHE):
        z = np.load(RAW_CACHE, allow_pickle=True)
        return z["X"], z["y"], z["subject"]
    X, y, subj = [], [], []
    print("  building raw cache (EDF read + bandpass) ...")
    t0 = time.time()
    for s in SUBJECTS:
        for sess in ["1", "2"]:
            path = os.path.join(DATA_DIR, f"{s}_{sess}_O1_O2.edf")
            if not os.path.exists(path):
                continue
            raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
            raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)
            data = raw.get_data() * 1e6     # µV
            fs = int(raw.info["sfreq"])
            ws = EPOCH_SEC * fs
            n = data.shape[1] // ws
            for i in range(n):
                X.append(data[:, i*ws:(i+1)*ws].astype(np.float32))
                y.append(0 if sess == "1" else 1)
                subj.append(s)
            print(f"    {s}_{sess}: +{n} epochs  ({time.time()-t0:.0f}s)")
    X = np.stack(X, axis=0)        # (N, 2, 1280)
    y = np.asarray(y, dtype=np.int64)
    subj = np.asarray(subj)
    np.savez_compressed(RAW_CACHE, X=X, y=y, subject=subj)
    print(f"  cached {X.shape} → {RAW_CACHE}")
    return X, y, subj


def per_subject_zscore_train_test(X_tr, y_tr, subj_tr, X_te, subj_te):
    """z-score per subject using THAT subject's awake (label 0) epochs from
       train fold; test subject is z-scored using ITS OWN awake epochs.
       (matches the subject_awake protocol used by v5/v9/v11.)"""
    Xn_tr = X_tr.astype(np.float32, copy=True)
    Xn_te = X_te.astype(np.float32, copy=True)
    for s in np.unique(subj_tr):
        m = subj_tr == s
        fit = m & (y_tr == 0)
        if fit.sum() < 5:
            continue
        mu = Xn_tr[fit].mean(axis=(0, 2), keepdims=True)
        sd = Xn_tr[fit].std(axis=(0, 2), keepdims=True)
        sd[sd == 0] = 1.0
        Xn_tr[m] = (Xn_tr[m] - mu) / sd
    # test: use the test subject's label-0 epochs as awake calibration
    test_subj = np.unique(subj_te)[0]
    fit_te = (subj_te == test_subj) & (np.zeros_like(subj_te, dtype=int) == 0)  # all
    # actually use only the first 30 epochs (~5 min) of session 1 for calibration
    # we don't know labels at deployment; use the same convention as v8 — first 60s
    # but we don't have time stamps here, so fall back to whole-session statistics
    # of the test subject's awake pseudo-data: all label-0 epochs in test set.
    # To avoid label leakage we use the subject's first 30 epochs (which by load
    # order are session 1 = awake).
    head = min(30, len(Xn_te))
    mu = Xn_te[:head].mean(axis=(0, 2), keepdims=True)
    sd = Xn_te[:head].std(axis=(0, 2), keepdims=True)
    sd[sd == 0] = 1.0
    Xn_te = (Xn_te - mu) / sd
    return Xn_tr, Xn_te


def metrics(y, p, pr):
    return {
        "accuracy":  round(accuracy_score(y, p) * 100, 2),
        "precision": round(precision_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "recall":    round(recall_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "f1_score":  round(f1_score(y, p, average="weighted", zero_division=0) * 100, 2),
        "auc_roc":   round(roc_auc_score(y, pr) * 100, 2) if len(np.unique(y)) > 1 else None,
        "kappa":     round(cohen_kappa_score(y, p), 4),
        "confusion_matrix": confusion_matrix(y, p).tolist(),
    }


# ─── main ────────────────────────────────────────────────────────────────
print("="*80); print("EEGNET BASELINE (Phase 2d, v14)"); print("="*80)
print(f"Timestamp: {datetime.now()}")
print(f"Device: {DEVICE}  | torch {torch.__version__}")
print()

torch.manual_seed(SEED); np.random.seed(SEED)
X, y, subj = build_raw_cache()
print(f"  X={X.shape}  y={y.shape}  subjects={len(np.unique(subj))}")

per_subject_rows = []
all_y, all_p, all_pr = [], [], []

t_loso = time.time()
for held_out in SUBJECTS:
    test_mask  = subj == held_out
    train_mask = ~test_mask
    Xtr, ytr, str_ = X[train_mask], y[train_mask], subj[train_mask]
    Xte, yte, ste_ = X[test_mask],  y[test_mask],  subj[test_mask]
    Xtr_n, Xte_n = per_subject_zscore_train_test(Xtr, ytr, str_, Xte, ste_)
    # add channel-dim for 2D conv (N, 1, ch, samples)
    Xtr_t = torch.from_numpy(Xtr_n[:, None, :, :].astype(np.float32))
    Xte_t = torch.from_numpy(Xte_n[:, None, :, :].astype(np.float32))
    ytr_t = torch.from_numpy(ytr)
    yte_t = torch.from_numpy(yte)

    model = EEGNet(channels=2, samples=WIN).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    crit = nn.CrossEntropyLoss()
    loader = DataLoader(TensorDataset(Xtr_t, ytr_t), batch_size=BATCH,
                        shuffle=True, drop_last=False)

    model.train()
    t_fold = time.time()
    for ep in range(EPOCHS):
        loss_sum, n = 0.0, 0
        for xb, yb in loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            opt.zero_grad()
            out = model(xb)
            loss = crit(out, yb)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * len(yb); n += len(yb)
    model.eval()
    with torch.no_grad():
        logits = model(Xte_t.to(DEVICE))
        proba  = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        pred   = logits.argmax(dim=1).cpu().numpy()
    mt = metrics(yte, pred, proba)
    per_subject_rows.append({"subject": held_out, **mt, "n": int(test_mask.sum()),
                             "train_loss_last_epoch": round(loss_sum / max(1, n), 4),
                             "time_s": round(time.time() - t_fold, 1)})
    all_y.append(yte); all_p.append(pred); all_pr.append(proba)
    print(f"  held_out={held_out}  acc={mt['accuracy']:>5}  f1={mt['f1_score']:>5}  "
          f"auc={mt['auc_roc']}  kappa={mt['kappa']:+.3f}  "
          f"loss={loss_sum/max(1,n):.3f}  ({time.time()-t_fold:.0f}s)")

overall = metrics(np.concatenate(all_y), np.concatenate(all_p), np.concatenate(all_pr))
print()
print(f"OVERALL (LOSO concat)  acc={overall['accuracy']}  f1={overall['f1_score']}  "
      f"auc={overall['auc_roc']}  kappa={overall['kappa']}  "
      f"total t={time.time()-t_loso:.0f}s")

payload = {
    "timestamp":    datetime.now().isoformat(),
    "methodology":  "EEGNet (Lawhern 2018) on raw O1/O2 windows. LOSO over 10 DROZY subjects. "
                    f"Per-subject train-fold awake z-score; test-subject z-score uses first 30 "
                    f"epochs of own session-1. Adam lr={LR}, batch={BATCH}, epochs={EPOCHS}, "
                    f"channels=2, samples={WIN}, F1=8, D=2, F2=16.",
    "overall":      overall,
    "per_subject":  per_subject_rows,
}
with open(RESULTS_FILE, "w") as f:
    json.dump(payload, f, indent=2)
print(f"\nWrote {RESULTS_FILE}")
