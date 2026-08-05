r"""Re-lay-out the live-demo figure from three stacked panels to three
side-by-side panels.

Why: as a full-width float, this figure is the single most expensive object in
the manuscript. Full-width floats are charged TWICE their height in
column-inches, and stacking three panels makes it tall -- 5.75 in, i.e. 12.2
column-inches, or 66 % of a page for one figure. Placing the same three
subjects side by side takes the height to ~2.6 in and the cost to ~6 col-in.

Nothing is removed: same three subjects, same traces, same onsets, same
thresholds. Only the arrangement changes.

Layout notes:
  * y-axis labels appear once each -- p(drowsy) on the leftmost panel,
    PERCLOS on the rightmost -- rather than three times over. With 2.39 in
    per panel there is no room for repeated axis furniture.
  * panel titles are two lines so they do not set wider than the panel.
  * fonts are authored at 9 pt so that after the 7.16/9.0 = 0.796 scale to
    \textwidth they land at ~7.2 pt, above the 6 pt legibility floor.

Writes to submission_compact/figures/ only. The canonical figure under
submission/ is left alone.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import live_demo_figure as L

# Named for the figure number it prints as (Fig. 5), not the legacy analysis
# tag it used to carry (fig12).
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "figures", "fig5_live_demo.png")

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
})


def panel(ax, s, a, title, first, last):
    t_min = a["t"] / 60.0
    ax.plot(t_min, a["p_raw"], "-", color="#9fb8d9", lw=0.6, alpha=0.6,
            label="p(drowsy) raw")
    ax.plot(t_min, a["p_smooth"], "-", color="#1f3b6e", lw=1.4,
            label=f"p(drowsy) EMA tau={L.V20_TAU}s")
    ax.axhline(a["thr_eeg"], color="#c75f1e", ls="--", lw=1.0,
               label="per-subject threshold")

    # Onset markers. Labels are staggered in y and boxed so they can neither
    # overprint each other nor the traces -- the defect this figure shipped
    # with when both onsets fell close together in time.
    def onset(t_sec, text, colour, y, ls):
        if t_sec is None:
            return
        x = t_sec / 60.0
        ax.axvline(x, color=colour, lw=1.3, ls=ls, alpha=0.9)
        span = t_min[-1] - t_min[0]
        frac = (x - t_min[0]) / span if span > 0 else 0.5
        ha, dx = ("left", 0.02 * span) if frac < 0.5 else ("right", -0.02 * span)
        ax.text(x + dx, y, text, color=colour, fontsize=7, ha=ha, va="top",
                transform=ax.get_xaxis_transform(), zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          edgecolor="none", alpha=0.85))

    onset(a["eeg_t"], "EEG", "#c75f1e", 0.97, "-")
    onset(a["behav_t"], "PERCLOS", "#a02a2a", 0.80, ":")

    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Session time (min)")
    ax.grid(alpha=0.25)
    if first:
        ax.set_ylabel("p(drowsy)")
    else:
        ax.set_yticklabels([])

    ax2 = ax.twinx()
    ax2.plot(t_min, a["pc_smooth"], "-", color="#567d46", lw=1.0, alpha=0.85,
             label="PERCLOS (30 s smoothed)")
    ax2.axhline(L.PERCLOS_BEH, color="#567d46", ls=":", lw=0.9, alpha=0.6)
    ax2.set_ylim(0, 1.0)
    if last:
        ax2.set_ylabel("PERCLOS", color="#567d46")
        ax2.tick_params(axis="y", labelcolor="#567d46")
    else:
        ax2.set_yticklabels([])

    lead = a["lead_min"]
    ax.set_title(f"{title}\n(subj {s})  lead = {lead:+.2f} min", fontsize=9)
    return ax2


def main():
    tl = L.build_timelines()
    analyses = {s: L.analyse(v) for s, v in tl.items()}
    picks = L.pick_representative_subjects(analyses)
    labels = ["Strong lead", "Median lead", "Marginal lead"]

    fig, axes = plt.subplots(1, len(picks), figsize=(9.0, 3.30))
    sec = []
    for i, (ax, (s, a), lbl) in enumerate(zip(axes, picks, labels)):
        sec.append(panel(ax, s, a, lbl, i == 0, i == len(picks) - 1))

    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = sec[-1].get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, 0.995),
               ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    # The figure is authored 9.0 in wide but placed at \textwidth = 7.16 in, so
    # the effective print resolution is dpi * 9.0/7.16. dpi=200 gave only
    # 251 dpi at placement, under IEEE's 300 dpi minimum for colour figures.
    # 300 * 9.0/7.16 = 377, so anything from 240 up clears 2148 px of width;
    # 250 leaves margin. Point sizes are unaffected -- dpi does not change how
    # large the type is relative to the figure.
    fig.savefig(OUT, dpi=250)
    plt.close(fig)

    from PIL import Image
    im = Image.open(OUT)
    d = im.info.get("dpi", (250,))[0]
    w, h = im.size[0] / d, im.size[1] / d
    placed_h = 7.16 / (w / h)
    eff_dpi = im.size[0] / 7.16
    print(f"  {OUT}")
    print(f"  authored {w:.2f} x {h:.2f} in  (aspect {w/h:.2f})")
    print(f"  at \\textwidth: height {placed_h:.2f} in -> cost {2*(placed_h+0.35):.2f} col-in"
          f"  (was 12.20)")
    print(f"  {im.size[0]}x{im.size[1]} px -> {eff_dpi:.0f} dpi at 7.16 in "
          f"({'OK' if eff_dpi >= 300 else 'UNDER 300 dpi'})")


if __name__ == "__main__":
    main()
