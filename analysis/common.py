"""Shared definitions for every analysis step.

Every number in the resubmitted manuscript comes from a script in this
folder, through a JSON file in ../results/. Conventions:

* Subject-independent evaluation is leave-one-subject-out (LOSO).
* Calibration is label-free: each recording is z-scored on its own opening
  window (SEED-VIG: first 60 s of the recording; DD-Database: first 300 s of
  the trial). Labels are never used to choose normalisation epochs.
* No hyperparameter is tuned on a test fold. Where a choice is data-driven
  (the smoothing constant tau), it is made by an inner LOSO on the training
  subjects only.
* AUC is the primary metric; weighted F1, balanced accuracy and Cohen's
  kappa are reported alongside.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess

import numpy as np
from scipy.signal import coherence, welch
from scipy.stats import entropy as sp_entropy, linregress, skew, wilcoxon
from scipy.integrate import trapezoid
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import (balanced_accuracy_score, cohen_kappa_score, f1_score,
                             precision_score, recall_score, roc_auc_score)

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
REPO = os.path.dirname(R1)
RESULTS = os.path.join(R1, "results")
CACHES = os.path.join(R1, "caches")
# Data are not redistributed; see data/README.md. Each location can be set
# through the environment variable of the same name.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(R1, "data"))
DD_DIR = os.environ.get("DD_DIR", os.path.join(DATA_DIR, "DD-Database"))
SEED_CACHE = os.environ.get("SEED_CACHE", os.path.join(DATA_DIR, "features_seed_vig_cache.npz"))
os.makedirs(RESULTS, exist_ok=True)
os.makedirs(CACHES, exist_ok=True)

FS = 128
EPOCH_SEC = 10
EPOCH = FS * EPOCH_SEC
DD_SUBJECTS = ["01M", "02F", "03F", "04M", "05M", "06M", "07F", "08M", "09M", "10M"]
DD_CAL_SEC = 300
SEED_CAL_SEC = 60
SEED_DIR_NOTE = ("SEED-VIG features come from features_seed_vig_cache.npz (built from the distributed "
                 "200-Hz recordings, resampled to 128 Hz, no additional band-pass filter); the raw "
                 "recordings are not on this machine.")

BANDS = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
LEAN = ["sample_entropy_O1", "sample_entropy_O2", "perm_entropy_O1", "perm_entropy_O2",
        "aperiodic_slope_O1", "aperiodic_slope_O2", "paf_delta", "coh_theta", "coh_alpha", "coh_beta"]
FAMILIES = {  # indices into LEAN
    "ENT": [0, 1, 2, 3],
    "SLOPE": [4, 5],
    "PAF": [6],
    "COH": [7, 8, 9],
}
LEAN10 = list(range(10))
LEAN7 = [0, 1, 2, 3, 4, 5, 6]  # lean set without coherence


# --------------------------------------------------------------------------
# Feature functions: unchanged from the pipeline of the original submission,
# so that only the input signals and labels change.
# --------------------------------------------------------------------------
def band_power(sig, fs, band):
    f, p = welch(sig, fs, nperseg=min(int(fs * 2), len(sig)))
    m = (f >= band[0]) & (f <= band[1])
    return float(trapezoid(p[m], f[m])) if m.sum() > 0 else 0.0


def spectral_entropy(sig, fs, fmin=0.5, fmax=40):
    f, p = welch(sig, fs, nperseg=min(int(fs * 2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    p_norm = p[m] / (p[m].sum() + 1e-12)
    return float(sp_entropy(p_norm + 1e-12))


def hjorth_params(sig):
    d1 = np.diff(sig)
    d2 = np.diff(d1)
    activity = np.var(sig)
    mobility = np.sqrt(np.var(d1) / (activity + 1e-12))
    complexity = np.sqrt(np.var(d2) / (np.var(d1) + 1e-12)) / (mobility + 1e-12)
    return activity, mobility, complexity


def zcr(sig):
    return float(np.sum(np.diff(np.sign(sig)) != 0)) / len(sig)


def dwt_energies(sig):
    import pywt
    coeffs = pywt.wavedec(sig, "db4", level=5)
    return [float(np.sum(c ** 2)) for c in coeffs[:5]]


def aperiodic_slope(sig, fs, fmin=2.0, fmax=40.0):
    f, p = welch(sig, fs, nperseg=min(int(fs * 2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    if m.sum() < 5:
        return 0.0
    return float(linregress(np.log10(f[m] + 1e-12), np.log10(p[m] + 1e-12)).slope)


def peak_alpha_freq(sig, fs, fmin=8.0, fmax=13.0):
    f, p = welch(sig, fs, nperseg=min(int(fs * 2), len(sig)))
    m = (f >= fmin) & (f <= fmax)
    return float(f[m][np.argmax(p[m])]) if m.any() else 0.0


def band_coherence(o1, o2, fs, band):
    f, cxy = coherence(o1, o2, fs=fs, nperseg=min(int(fs * 2), len(o1)))
    m = (f >= band[0]) & (f <= band[1])
    return float(np.mean(cxy[m])) if m.any() else 0.0


def feats_epoch_50(o1, o2, fs=FS):
    """The 50-feature extended set (30 baseline + 20 extended), as published."""
    import antropy as ant
    feats = {}
    for ch_name, sig in (("O1", o1), ("O2", o2)):
        for bname, brand in BANDS.items():
            feats[f"{bname}_{ch_name}"] = band_power(sig, fs, brand)
        th, al, be = feats[f"theta_{ch_name}"], feats[f"alpha_{ch_name}"], feats[f"beta_{ch_name}"]
        feats[f"theta_alpha_ratio_{ch_name}"] = th / (al + 1e-12)
        feats[f"slow_fast_ratio_{ch_name}"] = (th + al) / (al + be + 1e-12)
        feats[f"spectral_entropy_{ch_name}"] = spectral_entropy(sig, fs)
        a, mob, c = hjorth_params(sig)
        feats[f"hjorth_activity_{ch_name}"] = a
        feats[f"hjorth_mobility_{ch_name}"] = mob
        feats[f"hjorth_complexity_{ch_name}"] = c
        feats[f"zcr_{ch_name}"] = zcr(sig)
        feats[f"skewness_{ch_name}"] = float(skew(sig))
        for k, e in enumerate(dwt_energies(sig)):
            feats[f"dwt_{k}_{ch_name}"] = e
        feats[f"sample_entropy_{ch_name}"] = float(ant.sample_entropy(sig, order=2))
        feats[f"perm_entropy_{ch_name}"] = float(ant.perm_entropy(sig, order=3, normalize=True))
        feats[f"aperiodic_slope_{ch_name}"] = aperiodic_slope(sig, fs)
    for bname in ("theta", "alpha", "beta"):
        p1, p2 = feats[f"{bname}_O1"], feats[f"{bname}_O2"]
        feats[f"asymmetry_{bname}"] = (p1 - p2) / (p1 + p2 + 1e-12)
    feats["mean_theta_alpha_ratio"] = (feats["theta_alpha_ratio_O1"] + feats["theta_alpha_ratio_O2"]) / 2
    feats["total_theta"] = feats["theta_O1"] + feats["theta_O2"]
    feats["total_alpha"] = feats["alpha_O1"] + feats["alpha_O2"]
    feats["paf_delta"] = abs(peak_alpha_freq(o1, fs) - peak_alpha_freq(o2, fs))
    feats["coh_theta"] = band_coherence(o1, o2, fs, BANDS["theta"])
    feats["coh_alpha"] = band_coherence(o1, o2, fs, BANDS["alpha"])
    feats["coh_beta"] = band_coherence(o1, o2, fs, BANDS["beta"])
    return feats


# --------------------------------------------------------------------------
# Calibration, classification, smoothing
# --------------------------------------------------------------------------
def zscore_by_recording(X, recording, t, cal_sec):
    """Label-free calibration: z-score each recording on its opening window."""
    Xn = np.empty_like(X, dtype=float)
    for r in np.unique(recording):
        m = recording == r
        fit = m & (t < t[m].min() + cal_sec)
        if fit.sum() < 3:
            idx = np.where(m)[0][np.argsort(t[m])[:3]]
            fit = np.zeros_like(m)
            fit[idx] = True
        mu = X[fit].mean(0)
        sd = X[fit].std(0)
        sd[sd == 0] = 1.0
        Xn[m] = (X[m] - mu) / sd
    return Xn


def lda():
    return LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")


def loso_scores(Xn, y, subject, labelled=None, make_model=lda, test_subjects=None):
    """Posterior p(drowsy) for every epoch of each held-out subject.

    Training uses only labelled epochs (y >= 0) of the other subjects; scores
    are produced for all epochs of the held-out subject (labelled or not), so
    a smoother can run over the continuous stream.
    """
    labelled = (y >= 0) if labelled is None else labelled
    p = np.full(len(y), np.nan)
    subs = np.unique(subject) if test_subjects is None else test_subjects
    for s in subs:
        tr = labelled & (subject != s)
        te = subject == s
        if len(np.unique(y[tr])) < 2:
            continue
        p[te] = make_model().fit(Xn[tr], y[tr]).predict_proba(Xn[te])[:, 1]
    return p


def ema_time(p, t, tau):
    """Causal EMA with the true time step between consecutive epochs.

    lambda_k = 1 - exp(-(t_k - t_{k-1}) / tau); tau <= 0 returns p unchanged.
    Gaps (epochs removed by labelling) therefore decay the memory correctly.
    """
    if tau <= 0:
        return p.copy()
    out = np.empty_like(p, dtype=float)
    out[0] = p[0]
    for k in range(1, len(p)):
        lam = 1.0 - np.exp(-max(t[k] - t[k - 1], EPOCH_SEC) / tau)
        out[k] = lam * p[k] + (1 - lam) * out[k - 1]
    return out


def smooth_by_recording(p, t, recording, tau):
    out = p.copy()
    for r in np.unique(recording):
        idx = np.where(recording == r)[0]
        idx = idx[np.argsort(t[idx], kind="stable")]
        ok = ~np.isnan(p[idx])
        if ok.sum() == 0:
            continue
        sub = idx[ok]
        out[sub] = ema_time(p[sub], t[sub], tau)
    return out


# --------------------------------------------------------------------------
# Metrics and statistics
# --------------------------------------------------------------------------
def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    return {
        "AUC": 100 * roc_auc_score(y, p),
        "F1w": 100 * f1_score(y, pred, average="weighted"),
        "BalAcc": 100 * balanced_accuracy_score(y, pred),
        "kappa": cohen_kappa_score(y, pred),
        "n": int(len(y)), "n_pos": int(y.sum()),
    }


def per_subject(y, p, subject, thr=0.5):
    rows = {}
    for s in np.unique(subject):
        m = subject == s
        if m.sum() == 0 or len(np.unique(y[m])) < 2:
            continue
        pred = (p[m] >= thr).astype(int)
        rows[str(s)] = {
            "AUC": 100 * roc_auc_score(y[m], p[m]),
            "F1w": 100 * f1_score(y[m], pred, average="weighted"),
            "precision_drowsy": 100 * precision_score(y[m], pred, pos_label=1, zero_division=0),
            "recall_drowsy": 100 * recall_score(y[m], pred, pos_label=1, zero_division=0),
            "precision_alert": 100 * precision_score(y[m], pred, pos_label=0, zero_division=0),
            "recall_alert": 100 * recall_score(y[m], pred, pos_label=0, zero_division=0),
            "kappa": cohen_kappa_score(y[m], pred),
            "n": int(m.sum()), "n_drowsy": int(y[m].sum()),
        }
    return rows


def subject_bootstrap(y, p, subject, n_boot=5000, seed=0):
    """95 % CI of pooled AUC and F1w, resampling subjects (the unit of independence)."""
    rng = np.random.default_rng(seed)
    subs = np.unique(subject)
    idx_by = {s: np.where(subject == s)[0] for s in subs}
    aucs, f1s = [], []
    for _ in range(n_boot):
        pick = rng.choice(subs, size=len(subs), replace=True)
        idx = np.concatenate([idx_by[s] for s in pick])
        if len(np.unique(y[idx])) < 2:
            continue
        aucs.append(100 * roc_auc_score(y[idx], p[idx]))
        f1s.append(100 * f1_score(y[idx], (p[idx] >= .5).astype(int), average="weighted"))
    q = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return {"AUC_CI95": q(aucs), "F1w_CI95": q(f1s), "n_boot": len(aucs)}


def paired_wilcoxon(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    res = wilcoxon(b, a) if np.any(d != 0) else None
    return {"n": int(len(d)), "mean_diff": float(d.mean()), "median_diff": float(np.median(d)),
            "n_increase": int((d > 0).sum()), "n_decrease": int((d < 0).sum()),
            "p_two_sided": float(res.pvalue) if res is not None else 1.0,
            "paired_d": float(d.mean() / d.std(ddof=1)) if d.std(ddof=1) > 0 else 0.0}


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, same order as input."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


# --------------------------------------------------------------------------
# Dataset loaders (after 01-03 have run)
# --------------------------------------------------------------------------
class Dataset:
    """X: features (lean-10 unless stated), y: 0/1 or -1 (unlabelled), subject,
    recording, t (s from recording start), test_subjects, cal_sec."""

    def __init__(self, name, X, y, subject, recording, t, test_subjects, cal_sec, X_ext=None, ext_cols=None):
        self.name, self.X, self.y = name, X, y
        self.subject, self.recording, self.t = subject, recording, t
        self.test_subjects, self.cal_sec = test_subjects, cal_sec
        self.X_ext, self.ext_cols = X_ext, ext_cols

    def calibrated(self, cols=None, ext=False, cal_sec=None):
        base = self.X_ext if ext else self.X
        Xs = base if cols is None else base[:, cols]
        return zscore_by_recording(Xs, self.recording, self.t, cal_sec or self.cal_sec)


def load_seed():
    z = np.load(os.path.join(CACHES, "seed_v2.npz"), allow_pickle=True)
    y, subj = z["y"].astype(int), z["subject"].astype(str)
    both = [s for s in np.unique(subj) if len(np.unique(y[subj == s])) == 2]
    return Dataset("SEED-VIG", z["X"], y, subj, z["recording"].astype(str), z["t"].astype(float),
                   both, SEED_CAL_SEC)


def load_dd(label_key="y"):
    z = np.load(os.path.join(CACHES, "dd_features_v2.npz"), allow_pickle=True)
    lab = np.load(os.path.join(CACHES, "dd_labels_v2.npz"), allow_pickle=True)
    cols = [str(c) for c in z["cols"]]
    X50 = z["X50"].astype(float)
    X = X50[:, [cols.index(n) for n in LEAN]]
    return Dataset("DD-Database", X, lab[label_key].astype(int), z["subject"].astype(str),
                   z["recording"].astype(str), z["t"].astype(float), list(DD_SUBJECTS), DD_CAL_SEC,
                   X_ext=X50, ext_cols=cols)


def evaluate(ds, p):
    """Pooled metrics, per-subject metrics and subject bootstrap on labelled test epochs."""
    m = (ds.y >= 0) & np.isin(ds.subject, ds.test_subjects) & ~np.isnan(p)
    ps = per_subject(ds.y[m], p[m], ds.subject[m])
    aucs = [v["AUC"] for v in ps.values()]
    return {"pooled": metrics(ds.y[m], p[m]), "per_subject": ps,
            "subject_AUC_median": float(np.median(aucs)), "subject_AUC_IQR": [float(np.percentile(aucs, 25)), float(np.percentile(aucs, 75))],
            "subjects_AUC_above_50": int(sum(a > 50 for a in aucs)), "n_subjects": len(aucs),
            "bootstrap": subject_bootstrap(ds.y[m], p[m], ds.subject[m])}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def shown_path(path):
    """A data location as recorded in a result file: relative to the code root
    when it lies inside it, otherwise only its folder name."""
    try:
        rel = os.path.relpath(path, R1)
    except ValueError:  # another drive
        rel = ".."
    if rel.startswith(".."):
        return os.path.basename(os.path.normpath(path))
    return rel.replace(os.sep, "/")


def _git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=R1, capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        return "unknown"


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def write_result(name, payload, script):
    payload = {"script": os.path.basename(script), "git_commit": _git_commit(),
               "timestamp": _dt.datetime.now().isoformat(timespec="seconds"), **payload}
    path = os.path.join(RESULTS, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(payload), f, indent=1)
    print(f"wrote {os.path.relpath(path, R1)}")
    return path
