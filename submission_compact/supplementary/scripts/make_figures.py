"""
Publication figures v5 (Phase 6a)
=================================
Builds 300-DPI PNG/PDF figures from publication_results_v{3..11}.json
into ./publication_figures_v5/.

Headline pipeline = v11 lean (10 features: ENT+SLOPE+COH) → F1=62.08
"""

import os, sys, io, json
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "figure.dpi": 150,
})

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, "publication_figures_v5")
os.makedirs(OUT, exist_ok=True)
SUBJECTS = ["01M","02F","03F","04M","05M","06M","07F","08M","09M","10M"]


def load(v):
    p = os.path.join(ROOT, f"publication_results_{v}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def save(fig, name):
    fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight", dpi=300)
    fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.png/.pdf")


def ci95(a):
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 2:
        return float(a.mean()), 0.0
    half = stats.t.ppf(0.975, df=n-1) * a.std(ddof=1) / np.sqrt(n)
    return float(a.mean()), float(half)


# ─── Fig 1: Headline F1 progression v3 → v11 ────────────────────────────
def fig1_progression():
    rows = [
        ("v14 EEGNet",   47.32, "#d9d9d9"),
        ("v3 GB",        51.42, "#bdbdbd"),
        ("v4 LDA·both",  53.68, "#bdbdbd"),
        ("v5 LDA·awake", 53.27, "#bdbdbd"),
        ("v8 LDA·cal60", 54.32, "#9ecae1"),
        ("v6 Riem TS+LR",57.12, "#6baed6"),
        ("v7 Riem TS+LDA",57.69,"#3182bd"),
        ("v9 50-feat LDA",61.13,"#fdae6b"),
        ("v11 lean·LDA", 62.08, "#e6550d"),
    ]
    labels = [r[0] for r in rows]
    vals   = [r[1] for r in rows]
    cols   = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    bars = ax.bar(labels, vals, color=cols, edgecolor="black", linewidth=0.6)
    ax.axhline(50, color="grey", ls="--", lw=0.8, label="Chance (balanced)")
    ax.set_ylabel("Weighted F1 (%, LOSO)")
    ax.set_ylim(44, 66)
    ax.set_title("Pipeline progression on DROZY (10 subjects, O1/O2 only)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.25, f"{v:.1f}",
                ha="center", va="bottom", fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "fig1_pipeline_progression")


# ─── Fig 2: Feature-family ablation (v11) ───────────────────────────────
def fig2_ablation():
    v11 = load("v11")
    if v11 is None: return
    abl = v11["ablations"]
    order = [
        "ALL (50)", "NEW FAMILIES (20)", "ONLY ENT+SLOPE+COH (10)",
        "DROP COH (46)", "DROP DWT (40)", "DROP ENT (46)", "DROP SLOPE (48)",
        "ONLY DWT (10)", "BASE only (30)",
    ]
    f1   = [abl[k]["f1_score"] for k in order]
    nfeat= [abl[k]["n_features_used"] for k in order]
    cols = ["#3182bd", "#6baed6", "#e6550d",
            "#d62728", "#9ecae1", "#9ecae1", "#9ecae1",
            "#bdbdbd", "#bdbdbd"]

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    y = np.arange(len(order))
    bars = ax.barh(y, f1, color=cols, edgecolor="black", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{k}  (n={n})" for k, n in zip(order, nfeat)])
    ax.invert_yaxis()
    ax.axvline(50, color="grey", ls="--", lw=0.8)
    ax.axvline(62.08, color="#e6550d", ls=":", lw=1.0,
               label="v11 lean = 62.08")
    ax.set_xlabel("Weighted F1 (%, LOSO)")
    ax.set_xlim(48, 66)
    ax.set_title("Feature-family ablation (Phase 3a)")
    for b, v in zip(bars, f1):
        ax.text(v+0.2, b.get_y()+b.get_height()/2, f"{v:.1f}",
                va="center", fontsize=8)
    ax.legend(loc="lower right", frameon=False)
    save(fig, "fig2_feature_family_ablation")


# ─── Fig 3: Per-subject accuracy of v11 lean ────────────────────────────
def fig3_per_subject():
    v11 = load("v11")
    if v11 is None: return
    ps = v11["ablations"]["ONLY ENT+SLOPE+COH (10)"]["per_subject"]
    accs = {r["subject"]: r["accuracy"] for r in ps}
    order = SUBJECTS
    vals = [accs[s] for s in order]
    mu, half = ci95(vals)

    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    cols = ["#e6550d" if v >= 50 else "#9ecae1" for v in vals]
    bars = ax.bar(order, vals, color=cols, edgecolor="black", linewidth=0.5)
    ax.axhline(50, color="grey", ls="--", lw=0.8, label="Chance")
    ax.axhline(mu, color="#e6550d", ls=":", lw=1.0,
               label=f"Mean = {mu:.2f}")
    ax.axhspan(mu-half, mu+half, color="#e6550d", alpha=0.10,
               label=f"95% CI ±{half:.2f}")
    ax.set_ylabel("Per-subject accuracy (%, LOSO)")
    ax.set_ylim(40, 80)
    ax.set_title("v11 lean (10 features) — per-subject LOSO accuracy")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.5, f"{v:.1f}",
                ha="center", fontsize=8)
    ax.legend(loc="upper right", frameon=False, ncol=3)
    save(fig, "fig3_per_subject_accuracy")


# ─── Fig 4: Confusion matrix (v9 LDA, proxy for lean) ────────────────────
def fig4_cm():
    v9 = load("v9")
    if v9 is None: return
    cm = np.array(v9["model_comparison"]["LDA (shrinkage=auto)"]["confusion_matrix"])
    cm_n = cm / cm.sum(axis=1, keepdims=True)

    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    im = ax.imshow(cm_n, cmap="Oranges", vmin=0, vmax=1)
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Awake", "Drowsy"])
    ax.set_yticklabels(["Awake", "Drowsy"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Confusion matrix\n(v9 LDA, normalized by row)")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm_n[i,j]*100:.1f}%\n(n={cm[i,j]})",
                    ha="center", va="center",
                    color="white" if cm_n[i,j] > 0.55 else "black",
                    fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save(fig, "fig4_confusion_matrix")


# ─── Fig 5: Calibration window sweep (v8) ───────────────────────────────
def fig5_cal_sweep():
    v8 = load("v8")
    if v8 is None: return
    cals = [30, 60, 120, 180, 300]
    f1_lda = [v8["sweeps"][f"cal_{c}s"]["LDA"]["f1_score"]    for c in cals]
    f1_lr  = [v8["sweeps"][f"cal_{c}s"]["LogReg"]["f1_score"] for c in cals]

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.plot(cals, f1_lda, "-o", color="#3182bd", label="LDA")
    ax.plot(cals, f1_lr,  "-s", color="#e6550d", label="LogReg")
    ax.axvline(60, color="grey", ls=":", lw=0.8)
    ax.set_xlabel("Calibration window (s of session-1 awake EEG)")
    ax.set_ylabel("Weighted F1 (%, LOSO)")
    ax.set_title("Phase 2c: per-subject calibration window sweep (v8)")
    ax.set_xticks(cals)
    ax.legend(frameon=False)
    save(fig, "fig5_calibration_sweep")


# ─── Fig 6: Forest plot of paired Δ vs v11 lean ─────────────────────────
def fig6_forest():
    v10 = load("v10")
    if v10 is None: return
    rows = v10["paired_vs_reference"]
    keep = [r for r in rows if not r["comparator"].startswith("v11 LDA [")]
    keep += [r for r in rows if r["comparator"] == "v11 LDA [DROP COH (46)]"]
    keep += [r for r in rows if r["comparator"] == "v11 LDA [BASE only (30)]"]
    keep.sort(key=lambda r: r["delta_mean"])
    labels = [r["comparator"].replace("v11 LDA [", "v11 ").replace("]", "")
              for r in keep]
    deltas = [r["delta_mean"] for r in keep]
    pvals  = [r["wilcoxon_p_ref_greater"] for r in keep]

    fig, ax = plt.subplots(figsize=(7.0, max(4.0, 0.28*len(keep))))
    y = np.arange(len(keep))
    cols = ["#2ca02c" if p < 0.05 else "#bdbdbd" for p in pvals]
    ax.barh(y, deltas, color=cols, edgecolor="black", linewidth=0.4)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Δ mean per-subject accuracy  (v11 lean − comparator)")
    ax.set_title("Paired comparisons (Wilcoxon, one-sided, n=10 subjects)")
    for i, (d, p) in enumerate(zip(deltas, pvals)):
        marker = "*" if p < 0.05 else ""
        ax.text(d + 0.15, i, f"p={p:.3f}{marker}", va="center", fontsize=7)
    save(fig, "fig6_paired_forest")


# ─── Fig 7: Top features by ablation impact ─────────────────────────────
def fig7_family_impact():
    v11 = load("v11")
    if v11 is None: return
    base_f1 = v11["ablations"]["ALL (50)"]["f1_score"]
    drops = {
        "DWT energies (10)": base_f1 - v11["ablations"]["DROP DWT (40)"]["f1_score"],
        "Entropy (4)":       base_f1 - v11["ablations"]["DROP ENT (46)"]["f1_score"],
        "1/f slope (2)":     base_f1 - v11["ablations"]["DROP SLOPE (48)"]["f1_score"],
        "Coherence + PAF (4)": base_f1 - v11["ablations"]["DROP COH (46)"]["f1_score"],
    }
    keys = list(drops.keys())
    vals = list(drops.values())
    cols = ["#9ecae1", "#6baed6", "#3182bd", "#e6550d"]

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    bars = ax.bar(keys, vals, color=cols, edgecolor="black", linewidth=0.5)
    ax.set_ylabel("ΔF1 when family is removed\n(positive ⇒ family was helpful)")
    ax.set_title("Marginal contribution of each feature family")
    ax.axhline(0, color="black", lw=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v + 0.1*np.sign(v) if v != 0 else 0.05,
                f"{v:+.2f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=9)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    save(fig, "fig7_family_marginal_contribution")


# ─── Fig 8: SEED-VIG cross-dataset (transfer + LOSO) ────────────────────
def fig8_seed_vig():
    v12 = load("v12")
    if v12 is None: return
    tr = v12["drozy_to_seed_transfer"]
    lo = v12["seed_vig_loso"]
    metrics = ["accuracy", "f1_score", "auc_roc", "kappa"]
    metric_labels = ["Accuracy %", "Weighted F1 %", "AUC %", "κ × 100"]
    drozy_internal = [62.10, 62.08, 64.55, 0.242 * 100]   # v11 lean LDA on DROZY LOSO
    transfer       = [tr["overall"][k] if k != "kappa" else tr["overall"][k]*100
                       for k in metrics]
    seed_loso      = [lo["overall"][k] if k != "kappa" else lo["overall"][k]*100
                       for k in metrics]

    x = np.arange(len(metrics))
    w = 0.27
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    ax.bar(x - w, drozy_internal, w, label="DROZY-internal LOSO (v11 lean)",
           color="#bdbdbd", edgecolor="black", linewidth=0.4)
    ax.bar(x,     transfer,       w, label="DROZY → SEED-VIG transfer",
           color="#fdae6b", edgecolor="black", linewidth=0.4)
    ax.bar(x + w, seed_loso,      w, label="SEED-VIG-internal LOSO",
           color="#e6550d", edgecolor="black", linewidth=0.4)
    ax.set_xticks(x); ax.set_xticklabels(metric_labels)
    ax.set_ylabel("Score")
    ax.set_title("Cross-dataset validation (v11 lean LDA on O1/O2)")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    for xi, vals in zip([-w, 0, w], [drozy_internal, transfer, seed_loso]):
        for j, v in enumerate(vals):
            ax.text(j + xi, v + 0.6, f"{v:.1f}", ha="center", fontsize=7)
    save(fig, "fig8_seed_vig_cross_dataset")


# ─── Fig 9: Advance-prediction lead-time distribution ───────────────────
def fig9_advance():
    v13 = load("v13")
    if v13 is None: return
    rows = v13["per_subject"]
    leads = [r["lead_time_s"] / 60.0 for r in rows
             if r["lead_time_s"] is not None]
    if not leads: return

    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    ax.axhline(0, color="black", lw=0.5)
    ax.boxplot(leads, vert=False, widths=0.5,
               boxprops=dict(facecolor="#fdd0a2", edgecolor="black"),
               medianprops=dict(color="#e6550d", lw=2),
               patch_artist=True)
    jitter = (np.random.RandomState(0).rand(len(leads)) - 0.5) * 0.2 + 1
    ax.scatter(leads, jitter, color="#3182bd", s=22, zorder=3,
               edgecolor="black", linewidth=0.4)
    ax.axvline(0, color="grey", ls="--", lw=0.7,
               label="EEG and behavioural onset coincide")
    ax.set_xlabel("Lead time (min)  =  behavioural onset − EEG onset")
    ax.set_yticks([1]); ax.set_yticklabels([f"n={len(leads)} subjects"])
    ax.set_title("Advance-prediction lead time on SEED-VIG (LOSO)\n"
                 "median = +%.2f min,  IQR = [%.2f, %.2f]"
                 % (np.median(leads), np.percentile(leads, 25),
                    np.percentile(leads, 75)))
    ax.legend(loc="lower right", frameon=False, fontsize=8)
    save(fig, "fig9_advance_lead_distribution")


# ─── main ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Writing publication figures v5 → {OUT}")
    fig1_progression()
    fig2_ablation()
    fig3_per_subject()
    fig4_cm()
    fig5_cal_sweep()
    fig6_forest()
    fig7_family_impact()
    fig8_seed_vig()
    fig9_advance()
    print("Done.")
