"""Manuscript figures (vector PDF + PNG twin), from results/*.json.

  fig1_coherence_subjects  per-subject mean O1-O2 coherence, alert vs drowsy,
                           three bands x two datasets
  fig2_tau_sweep           AUC versus EMA time constant, both datasets
  fig3_roc_subjects        per-subject ROC curves with the pooled curve
  figS1_roc_panels         one ROC panel per driver, supplementary Fig. S1

Authored at the two-column \\columnwidth (3.45 in) and placed 1:1, with
TrueType fonts embedded (Type 3 fonts are an IEEE production reject).
"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

FIG_DIR = os.path.join(C.R1, "manuscript", "figures")
SUPP_DIR = os.path.join(C.R1, "supplementary", "figures")
COL_W = 3.45
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "pdf.fonttype": 42, "ps.fonttype": 42,
                     "font.family": "DejaVu Sans", "axes.linewidth": 0.6})
BLUE, ORANGE, GREY = "#2F5BA8", "#C8641E", "#9A9A9A"


def load(name):
    with open(os.path.join(C.RESULTS, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


def save(fig, stem, folder=FIG_DIR):
    os.makedirs(folder, exist_ok=True)
    fig.savefig(os.path.join(folder, stem + ".pdf"))
    fig.savefig(os.path.join(folder, stem + ".png"), dpi=400)
    plt.close(fig)
    print("wrote", stem)


SYM = {"theta": "θ", "alpha": "α", "beta": "β"}


def fig1():
    r = load("coherence_stats")["results"]
    fig, axes = plt.subplots(2, 3, figsize=(COL_W, 2.75), sharex=True)
    for row, ds in enumerate(("SEED-VIG", "DD-Database")):
        for col, band in enumerate(("theta", "alpha", "beta")):
            ax = axes[row, col]
            d = r[ds][band]
            for a, b in zip(d["alert_mean"], d["drowsy_mean"]):
                ax.plot([0, 1], [a, b], color=ORANGE if b > a else BLUE, lw=0.7, alpha=0.85,
                        ls="-" if b > a else "--", marker="o", ms=1.8)
            t = d["subject_level"]
            ax.set_title(f"{SYM[band]}: {t['n_increase']}↑ {t['n_decrease']}↓, p={t['p_holm']:.2f}",
                         fontsize=6.5, pad=2.5)
            ax.set_xticks([0, 1])
            ax.set_xticklabels(["alert", "drowsy"])
            ax.set_xlim(-0.25, 1.25)
            ax.tick_params(length=2, pad=1.5)
            if col == 0:
                ax.set_ylabel(f"{ds}\nO$_1$–O$_2$ coherence", fontsize=6.5)
    fig.tight_layout(pad=0.3, h_pad=0.7, w_pad=0.3)
    save(fig, "fig1_coherence_subjects")


def fig2():
    r = load("tau_sweep")
    taus = r["taus_s"]
    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    x = np.arange(len(taus))
    for ds, color, mk in (("SEED-VIG", BLUE, "o"), ("DD-Database", ORANGE, "s")):
        sw = r["results"][ds]["fixed_tau_sweep"]
        pooled = [sw[str(t)]["pooled"]["AUC"] for t in taus]
        med = [sw[str(t)]["subject_AUC_median"] for t in taus]
        short = "SEED" if ds == "SEED-VIG" else "DD"
        ax.plot(x, pooled, color=color, marker=mk, ms=2.5, lw=1.0, label=f"{short}, pooled")
        ax.plot(x, med, color=color, marker=mk, ms=2.5, lw=1.0, ls="--", mfc="white", label=f"{short}, per-driver median")
        chosen = r["results"][ds]["nested"]["chosen_tau_per_outer_subject"]
        for tval in sorted({v["tau"] for v in chosen.values()}):
            k = taus.index(tval)
            ax.annotate("", xy=(k, pooled[k] - 0.6), xytext=(k, pooled[k] - 2.4),
                        arrowprops=dict(arrowstyle="->", color=color, lw=0.7))
    ax.axhline(50, color=GREY, lw=0.6, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels(["none" if t == 0 else str(t) for t in taus])
    ax.set_xlabel("EMA time constant τ (s)")
    ax.set_ylabel("AUC (%)")
    ax.legend(ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), handlelength=1.8,
              columnspacing=1.0, borderaxespad=0.2)
    ax.tick_params(length=2)
    fig.tight_layout(pad=0.3)
    save(fig, "fig2_tau_sweep")


def fig3():
    r = load("per_subject")["results"]
    fig, axes = plt.subplots(1, 2, figsize=(COL_W, 2.0), sharey=True)
    for ax, ds in zip(axes, ("SEED-VIG", "DD-Database")):
        d = r[ds]["lean10"]
        for s, c in d["subject_curves"].items():
            ax.plot(c["fpr"], c["tpr"], color=GREY, lw=0.5, alpha=0.8)
        pc = d["pooled_curve"]
        ax.plot(pc["fpr"], pc["tpr"], color=BLUE if ds == "SEED-VIG" else ORANGE, lw=1.4, label="pooled")
        ax.plot([0, 1], [0, 1], color="black", lw=0.5, ls=":")
        aucs = [v["AUC"] for v in d["per_subject"].values()]
        ax.set_title(ds, fontsize=7, pad=2.5)
        ax.text(0.97, 0.05, f"{len(aucs)} drivers\nmedian AUC {np.median(aucs):.1f}", ha="right", va="bottom",
                transform=ax.transAxes, fontsize=6.5)
        ax.set_xlabel("False-positive rate")
        ax.set_aspect("equal")
        ax.tick_params(length=2)
    axes[0].set_ylabel("True-positive rate")
    fig.tight_layout(pad=0.4, w_pad=0.8)
    save(fig, "fig3_roc_subjects")


def figS1():
    """One ROC panel per test driver (lean-10 LDA, no smoothing), with the
    unsmoothed and nested-smoothed per-driver AUC in each panel."""
    r = load("per_subject")["results"]
    nested = load("tau_sweep")["results"]
    order = {"SEED-VIG": lambda s: int(s), "DD-Database": lambda s: s}
    panels = [(ds, s) for ds in ("SEED-VIG", "DD-Database")
              for s in sorted(r[ds]["lean10"]["subject_curves"], key=order[ds])]
    ncol = 6
    nrow = -(-len(panels) // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.5, 1.12 * nrow), sharex=True, sharey=True)
    for ax in axes.flat[len(panels):]:
        ax.axis("off")
    for ax, (ds, s) in zip(axes.flat, panels):
        c = r[ds]["lean10"]["subject_curves"][s]
        auc = r[ds]["lean10"]["per_subject"][s]["AUC"]
        nauc = nested[ds]["nested"]["result"]["per_subject"][s]["AUC"]
        ax.plot(c["fpr"], c["tpr"], color=BLUE if ds == "SEED-VIG" else ORANGE, lw=0.9)
        ax.plot([0, 1], [0, 1], color="black", lw=0.4, ls=":")
        tag = f"SEED {s}" if ds == "SEED-VIG" else f"DD {s}"
        ax.set_title(tag, fontsize=6.5, pad=1.5)
        ax.text(0.97, 0.04, f"AUC {auc:.1f}\nEMA {nauc:.1f}", ha="right", va="bottom", transform=ax.transAxes,
                fontsize=6.5)
        ax.set_aspect("equal")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.tick_params(length=1.5, labelsize=6.5)
    fig.supxlabel("False-positive rate", fontsize=7)
    fig.supylabel("True-positive rate", fontsize=7, x=0.005)
    fig.tight_layout(pad=0.4, h_pad=0.4, w_pad=0.3, rect=(0.015, 0, 1, 1))
    save(fig, "figS1_roc_panels", SUPP_DIR)


if __name__ == "__main__":
    which = sys.argv[1:] or ["fig1", "fig2", "fig3"]
    for name in which:
        globals()[name]()
