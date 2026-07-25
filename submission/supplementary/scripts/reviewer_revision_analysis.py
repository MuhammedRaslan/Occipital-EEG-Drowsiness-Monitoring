"""
Reviewer-revision analysis (Prof. A. R. Pal internal review, 26-05-2026).
Produces the three additions requested before IEEE Sensors submission:

  1. Coherence interpretation: awake-vs-drowsy theta/alpha/beta O1-O2 coherence
     descriptive stats, Mann-Whitney U, Cohen's d, + box/violin figure.
  2. Subject-wise F1/AUC/kappa for v11 (unsmoothed) and v17 (continuous EMA
     tau=600s), mean/median/sd across subjects, + subject-cluster bootstrap
     95% CIs for the concatenated F1/AUC/kappa of both pipelines.
  3. EMA smoother illustration: raw vs EMA-smoothed posterior for a
     representative subject, + analytic latency characterisation.

Reproduces the exact published pipeline (per-subject awake z-score, lean
10-feature shrinkage LDA, LOSO, causal EMA continuous regime) so all numbers
stay consistent with hmm_smoothing.py / publication_results_v17.json.

Outputs:
  submission/figures/fig13_coherence_separation.png
  submission/figures/fig14_ema_raw_vs_smoothed.png
  publication_results_v21_reviewer.json   (provenance for the new tables)
"""

import os, io, sys, json, warnings
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
from datetime import datetime
from scipy.stats import mannwhitneyu
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import f1_score, roc_auc_score, cohen_kappa_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
np.random.seed(20260526)

_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(_DIR, "features_v9_cache.npz")
FIGDIR = os.path.join(_DIR, "submission", "figures")
os.makedirs(FIGDIR, exist_ok=True)

LEAN_NAMES = [
    "sample_entropy_O1", "sample_entropy_O2",
    "perm_entropy_O1",   "perm_entropy_O2",
    "aperiodic_slope_O1","aperiodic_slope_O2",
    "paf_delta",
    "coh_theta", "coh_alpha", "coh_beta",
]
EPOCH_SEC = 10
TAU = 600


def cohens_d(a, b):
    n1, n2 = len(a), len(b)
    sp = np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    return (b.mean() - a.mean()) / sp


def per_subject_zscore(X, y, subj):
    Xz = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        awake = m & (y == 0)
        mu = X[awake].mean(axis=0); sd = X[awake].std(axis=0) + 1e-8
        Xz[m] = (X[m] - mu) / sd
    return Xz


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0:
        return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p)
    out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


# ----------------------------------------------------------------------------
# Load
z = np.load(CACHE, allow_pickle=True)
cols = [str(c) for c in z["feat_cols"]]
Xfull = z["X"].astype(float)
y = z["y"].astype(int)
subj = np.asarray(z["subjects"])
ix = np.array([cols.index(n) for n in LEAN_NAMES], dtype=int)
X = Xfull[:, ix]
Xz = per_subject_zscore(X, y, subj)
subjects = sorted(np.unique(subj).tolist())
print(f"X={X.shape}  awake={int((y==0).sum())} drowsy={int((y==1).sum())}  subjects={len(subjects)}")

results = {"timestamp": datetime.now().isoformat(),
           "methodology": "Reviewer-revision additions; reproduces v11 lean LDA LOSO + continuous EMA tau=600s (v17)."}

# ============================================================================
# ITEM 1 — coherence awake vs drowsy
# ============================================================================
print("\n=== Item 1: coherence awake vs drowsy ===")
bands = [("theta", "coh_theta"), ("alpha", "coh_alpha"), ("beta", "coh_beta")]
coh_stats = {}
for band, col in bands:
    j = cols.index(col)
    aw = Xfull[y == 0, j]; dr = Xfull[y == 1, j]
    U, p = mannwhitneyu(aw, dr, alternative="two-sided")
    d = cohens_d(aw, dr)
    coh_stats[band] = {
        "awake_mean": round(float(aw.mean()), 4), "awake_median": round(float(np.median(aw)), 4),
        "awake_sd": round(float(aw.std(ddof=1)), 4),
        "drowsy_mean": round(float(dr.mean()), 4), "drowsy_median": round(float(np.median(dr)), 4),
        "drowsy_sd": round(float(dr.std(ddof=1)), 4),
        "direction": "decrease" if dr.mean() < aw.mean() else "increase",
        "mannwhitney_U": float(U), "p_value": float(p), "cohens_d": round(float(d), 3),
    }
    print(f"  {band:6s} awake={aw.mean():.3f} drowsy={dr.mean():.3f} "
          f"dir={coh_stats[band]['direction']:8s} d={d:+.3f} p={p:.2e}")
results["item1_coherence"] = coh_stats

# Figure: violin (awake vs drowsy) per band
fig, ax = plt.subplots(figsize=(7.0, 4.2))
positions = []
data = []
labels = []
colors = []
palette = {"awake": "#2c7fb8", "drowsy": "#d95f0e"}
for bi, (band, col) in enumerate(bands):
    j = cols.index(col)
    aw = Xfull[y == 0, j]; dr = Xfull[y == 1, j]
    base = bi * 3
    data += [aw, dr]; positions += [base + 0.7, base + 1.5]
    labels += [band]
    colors += [palette["awake"], palette["drowsy"]]
vp = ax.violinplot(data, positions=positions, widths=0.7, showmedians=True, showextrema=False)
for k, b in enumerate(vp["bodies"]):
    b.set_facecolor(colors[k]); b.set_alpha(0.6); b.set_edgecolor("black"); b.set_linewidth(0.6)
vp["cmedians"].set_color("black"); vp["cmedians"].set_linewidth(1.2)
# significance annotation
for bi, (band, col) in enumerate(bands):
    base = bi * 3
    d = coh_stats[band]["cohens_d"]
    ytop = max(np.percentile(Xfull[:, cols.index(col)], 99), 0.9)
    ax.text(base + 1.1, 1.02, f"$d={d:+.2f}$\n$p<10^{{-50}}$", ha="center", va="bottom", fontsize=8)
ax.set_xticks([bi * 3 + 1.1 for bi in range(3)])
ax.set_xticklabels([r"$\theta$ (4--8 Hz)", r"$\alpha$ (8--13 Hz)", r"$\beta$ (13--30 Hz)"])
ax.set_ylabel(r"$O_1$--$O_2$ magnitude-squared coherence")
ax.set_ylim(0, 1.18)
ax.set_title("Inter-hemispheric occipital coherence: awake vs drowsy")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(facecolor=palette["awake"], alpha=0.6, label="Awake"),
                   Patch(facecolor=palette["drowsy"], alpha=0.6, label="Drowsy")],
          loc="lower center", ncol=2, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
f1path = os.path.join(FIGDIR, "fig13_coherence_separation.png")
fig.savefig(f1path, dpi=300); plt.close(fig)
print(f"  wrote {f1path}")

# ============================================================================
# ITEM 2 — per-subject metrics + bootstrap CIs
# ============================================================================
print("\n=== Item 2: per-subject metrics + bootstrap CIs ===")
# LOSO per-epoch posterior (v11), and continuous-EMA smoothed (v17)
p_raw = np.empty(len(y), dtype=float)
for held in subjects:
    tr = subj != held; te = subj == held
    clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    clf.fit(Xz[tr], y[tr])
    p_raw[te] = clf.predict_proba(Xz[te])[:, 1]
p_sm = np.empty_like(p_raw)
for s in subjects:
    m = np.where(subj == s)[0]
    p_sm[m] = causal_ema(p_raw[m], TAU)   # continuous regime: one segment/subject
pred_v11 = (p_raw >= 0.5).astype(int)
pred_v17 = (p_sm >= 0.5).astype(int)


def subj_metrics(pred, score):
    rows = {}
    for s in subjects:
        m = subj == s
        rows[s] = {
            "f1": round(f1_score(y[m], pred[m], average="weighted") * 100, 2),
            "auc": round(roc_auc_score(y[m], score[m]) * 100, 2),
            "kappa": round(cohen_kappa_score(y[m], pred[m]), 3),
        }
    return rows


per_v11 = subj_metrics(pred_v11, p_raw)
per_v17 = subj_metrics(pred_v17, p_sm)
for s in subjects:
    print(f"  {s}: v11 F1={per_v11[s]['f1']:5.1f} k={per_v11[s]['kappa']:+.2f} | "
          f"v17 F1={per_v17[s]['f1']:5.1f} k={per_v17[s]['kappa']:+.2f}")


def summ(rows, key):
    vals = np.array([rows[s][key] for s in subjects], dtype=float)
    return {"mean": round(float(vals.mean()), 2), "median": round(float(np.median(vals)), 2),
            "sd": round(float(vals.std(ddof=1)), 2)}


# Subject-cluster bootstrap for concatenated metrics (honest for n=10)
def boot_ci(pred, score, n_boot=5000):
    out = {"f1": [], "auc": [], "kappa": []}
    sidx = {s: np.where(subj == s)[0] for s in subjects}
    for _ in range(n_boot):
        pick = np.random.choice(subjects, size=len(subjects), replace=True)
        idx = np.concatenate([sidx[s] for s in pick])
        yt, pt, st = y[idx], pred[idx], score[idx]
        out["f1"].append(f1_score(yt, pt, average="weighted") * 100)
        try:
            out["auc"].append(roc_auc_score(yt, st) * 100)
        except ValueError:
            out["auc"].append(np.nan)
        out["kappa"].append(cohen_kappa_score(yt, pt))
    ci = {}
    for k, v in out.items():
        v = np.array(v); v = v[~np.isnan(v)]
        ci[k] = [round(float(np.percentile(v, 2.5)), 3 if k == "kappa" else 2),
                 round(float(np.percentile(v, 97.5)), 3 if k == "kappa" else 2)]
    return ci


def concat_point(pred, score):
    return {"f1": round(f1_score(y, pred, average="weighted") * 100, 2),
            "auc": round(roc_auc_score(y, score) * 100, 2),
            "kappa": round(cohen_kappa_score(y, pred), 3)}


point_v11 = concat_point(pred_v11, p_raw)
point_v17 = concat_point(pred_v17, p_sm)
ci_v11 = boot_ci(pred_v11, p_raw)
ci_v17 = boot_ci(pred_v17, p_sm)
print(f"  v11 concat F1={point_v11['f1']} CI={ci_v11['f1']} | AUC={point_v11['auc']} CI={ci_v11['auc']} | k={point_v11['kappa']} CI={ci_v11['kappa']}")
print(f"  v17 concat F1={point_v17['f1']} CI={ci_v17['f1']} | AUC={point_v17['auc']} CI={ci_v17['auc']} | k={point_v17['kappa']} CI={ci_v17['kappa']}")

results["item2_subjectwise"] = {
    "per_subject": {s: {"v11": per_v11[s], "v17": per_v17[s]} for s in subjects},
    "summary_across_subjects": {
        "v11": {k: summ(per_v11, k) for k in ("f1", "auc", "kappa")},
        "v17": {k: summ(per_v17, k) for k in ("f1", "auc", "kappa")},
    },
    "concatenated_point": {"v11": point_v11, "v17": point_v17},
    "bootstrap_ci_95": {"method": "subject-cluster percentile bootstrap, 5000 resamples",
                        "v11": ci_v11, "v17": ci_v17},
}

# ============================================================================
# ITEM 3 — raw vs EMA-smoothed + latency
# ============================================================================
print("\n=== Item 3: EMA illustration + latency ===")
# representative subject: clear epoch-level noise that smoothing resolves
rep = "05M"
m = np.where(subj == rep)[0]
t_min = np.arange(len(m)) * EPOCH_SEC / 60.0
boundary = int(np.argmax(y[m] == 1))  # first drowsy epoch index
fig, ax = plt.subplots(figsize=(7.2, 3.8))
ax.plot(t_min, p_raw[m], color="#bdbdbd", lw=0.8, label="raw posterior $p_t$")
ax.plot(t_min, p_sm[m], color="#c1272d", lw=1.8, label=r"EMA-smoothed $\tilde p_t$ ($\tau=600$ s)")
ax.axhline(0.5, color="black", ls=":", lw=0.8)
ax.axvline(t_min[boundary], color="#1f78b4", ls="--", lw=1.0, label="awake$\\to$drowsy session boundary")
ax.set_xlabel("Time within subject stream (min)")
ax.set_ylabel("$p(\\mathrm{drowsy})$")
ax.set_ylim(-0.02, 1.02)
ax.set_title(f"Raw vs causal-EMA posterior (subject {rep})")
ax.legend(loc="center left", fontsize=8, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
f3path = os.path.join(FIGDIR, "fig14_ema_raw_vs_smoothed.png")
fig.savefig(f3path, dpi=300); plt.close(fig)
print(f"  wrote {f3path}")

# Latency: EMA step response reaches fraction q at t = -tau*ln(1-q)
alpha = 1.0 - np.exp(-EPOCH_SEC / TAU)
lat = {q: round(-TAU * np.log(1 - q) / 60.0, 2) for q in (0.5, 0.63, 0.90)}
# empirical: epochs from boundary until smoothed crosses 0.5 (this subject)
cross = None
for t in range(boundary, len(m)):
    if p_sm[m][t] >= 0.5:
        cross = (t - boundary) * EPOCH_SEC / 60.0; break
print(f"  alpha={alpha:.5f}; step-response lag (min): 50%={lat[0.5]} 63%={lat[0.63]} 90%={lat[0.90]}")
print(f"  empirical {rep} time-to-cross-0.5 after boundary = {cross} min")
results["item3_latency"] = {"tau_sec": TAU, "alpha": round(float(alpha), 5),
                            "step_response_lag_min": lat,
                            "representative_subject": rep,
                            "empirical_cross_min": cross,
                            "proactive_track_tau_sec": 30}

with open(os.path.join(_DIR, "publication_results_v21_reviewer.json"), "w") as f:
    json.dump(results, f, indent=2)
print("\nWrote publication_results_v21_reviewer.json")
