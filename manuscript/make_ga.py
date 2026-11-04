"""Graphical abstract of the article.

Draws the abstract-box figure on a 6.72 x 4.56 in canvas and writes
  figures/gagraphic.png              2016 x 1368 px (300 dpi), placed at 3 in
                                     wide inside the abstract box of main.tex
  ../dist/gagraphic_portal.png       672 x 456 px, palette PNG for the
                                     submission portal (target < 45 kB)
Every number is read from ../results/*.json; nothing is typed in.

Fonts: Times New Roman and Arial (metric equivalents of the Nimbus Roman and
Nimbus Sans used by the original figure); DejaVu is the fallback.

    python -I manuscript/make_ga.py
"""
import json
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrow, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
R1 = os.path.dirname(HERE)
RESULTS = os.path.join(R1, "results")
OUT_MAIN = os.path.join(HERE, "figures", "gagraphic.png")
OUT_PORTAL = os.path.join(R1, "dist", "gagraphic_portal.png")

W, H = 672.0, 456.0
BLUE = "#658CD0"
BLUE_DK = "#2F5BA8"
ORANGE = "#C8641E"
BG = "#F9FBFD"
BORDER = "#C9D8EE"
CARD_BORDER = "#DCE5F2"
INK = "#33261C"
INK_SOFT = "#6B5A50"
GREY_PILL = "#C3CEE1"
WAVE = "#4472C4"

_available = {f.name for f in font_manager.fontManager.ttflist}
SERIF = "Times New Roman" if "Times New Roman" in _available else "DejaVu Serif"
SANS = "Arial" if "Arial" in _available else "DejaVu Sans"


def load(name):
    with open(os.path.join(RESULTS, f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)


mon = load("monitoring")["results"]
seed = mon["SEED-VIG"]["configs"]["LDA | lean10"]
dd = mon["DD-Database"]["configs"]["LDA | lean10"]
nested = load("tau_sweep")["results"]
seed_p = nested["SEED-VIG"]["nested"]["result"]  # primary pipeline: lean-10, LDA, EMA
dd_p = nested["DD-Database"]["nested"]["result"]
xfer = load("cross_dataset")["results"]["lean10: DD-Database -> SEED-VIG"]
rt = load("runtime")["per_epoch"]["lean10_feature_extraction"]["median_ms"]
n_drivers = seed["n_subjects"] + dd["n_subjects"]

fig = plt.figure(figsize=(W / 100.0, (H + 0.01) / 100.0), dpi=300)  # +0.01: 4.56 in x dpi rounds down
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.add_patch(Rectangle((0, 0), W, H, fc=BG, ec="none", zorder=0))


def round_box(x0, y0, x1, y1, r=6, fc="white", ec=BORDER, lw=0.9, z=2):
    ax.add_patch(FancyBboxPatch((x0 + r, y0 + r), x1 - x0 - 2 * r, y1 - y0 - 2 * r,
                                boxstyle=f"round,pad={r}", fc=fc, ec=ec, lw=lw, zorder=z))


def txt(x, y, s, size=8, color=INK, weight="normal", family=None, ha="center", va="center", z=5):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, fontfamily=family or SANS,
            ha=ha, va=va, zorder=z)


def down_arrow(x, ytop, ybot):
    ax.add_patch(FancyArrow(x, ytop, 0, ybot - ytop, width=5, head_width=13, head_length=8,
                            length_includes_head=True, fc=BLUE, ec="none", zorder=4))


def right_arrow(xl, xr, y):
    ax.add_patch(FancyArrow(xl, y, xr - xl, 0, width=5, head_width=13, head_length=8,
                            length_includes_head=True, fc=BLUE, ec="none", zorder=4))


# ---------------------------------------------------------------- header band
ax.add_patch(Rectangle((0, H - 64), W, 64, fc=BLUE, ec="none", zorder=1))
txt(W / 2, H - 25, "Subject-Independent Driver Drowsiness Monitoring", size=14, color="white", weight="bold",
    family=SERIF)
txt(W / 2, H - 46, "Two occipital EEG electrodes, a placement compatible with a vehicle headrest", size=7.4,
    color="#E8EFFA", family=SERIF)

for cx, label in ((118, "SENSING"), (330, "PIPELINE"), (543, "RESULTS")):
    round_box(cx - 69, 353, cx + 69, 376, r=11, fc=BLUE, ec="none", z=3)
    txt(cx, 364.5, label, size=8.2, color="white", weight="bold", family=SERIF, z=6)

round_box(23, 72, 212, 340, r=6, ec=CARD_BORDER)
round_box(234, 72, 425, 340, r=6, ec=CARD_BORDER)
round_box(448, 72, 637, 340, r=6, ec=CARD_BORDER)
right_arrow(215, 231, 206)
right_arrow(428, 445, 206)

# ============================================================ SENSING column
ax.add_patch(Ellipse((118, 308), 47, 56, fc="white", ec=INK, lw=1.1, zorder=5))
ax.add_patch(Polygon([[113, 335], [118, 343], [123, 335]], closed=True, fc="white", ec=INK, lw=1.1, zorder=5))
ax.plot([102, 134], [287, 287], "o", color=BLUE_DK, ms=4.5, zorder=7)
txt(101, 275, "O1", size=7.5, color=BLUE_DK, weight="bold")
txt(137, 275, "O2", size=7.5, color=BLUE_DK, weight="bold")
round_box(71, 245, 165, 262, r=7, fc=GREY_PILL, ec="none", z=3)
txt(118, 253.5, "headrest", size=7.5, z=6)


def wave(y, amp, freq, seed_, x0=36, x1=200, smooth=False):
    rng = np.random.default_rng(seed_)
    t = np.linspace(0, 1, 1400)
    if smooth:
        s = np.convolve(rng.normal(0, 1, 1400), np.ones(90) / 90.0, mode="same")
    else:
        s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2.3 * t + 1.0)
    ax.plot(x0 + t * (x1 - x0), y + amp * s / (np.abs(s).max() + 1e-9), color=WAVE, lw=0.8, zorder=5)


txt(36, 231, "alert", size=7.5, weight="bold", ha="left")
wave(216, 4.5, 26, 1)
wave(201, 4.5, 29, 2)
txt(36, 184, "drowsy", size=7.5, weight="bold", ha="left")
wave(165, 9.5, 0, 11, smooth=True)
wave(137, 9.5, 0, 12, smooth=True)
txt(118, 106, "10-s epochs, no cap", size=7.5, color=BLUE_DK, weight="bold")
txt(118, 91, "labels: eyelid closure or self-report", size=6.6, color=INK_SOFT)

# =========================================================== PIPELINE column
round_box(248, 261, 413, 327, r=5, lw=0.8)
txt(330, 313, "10 features", size=7.6, weight="bold")
txt(330, 297, "entropy, aperiodic slope,", size=7.2)
txt(330, 282, "peak-alpha asymmetry, coherence", size=7.2)
down_arrow(330, 259, 246)
round_box(248, 171, 413, 244, r=5, lw=0.8)
txt(330, 222, "label-free calibration", size=7.6, weight="bold")
txt(330, 206, "opening minutes of each drive", size=7.0)
txt(330, 188, "shrinkage LDA", size=7.6, weight="bold")
down_arrow(330, 169, 152)
round_box(248, 81, 413, 150, r=5, lw=0.8)
txt(330, 131, "short causal smoother", size=7.6, weight="bold")
txt(330, 115, "time constant chosen by", size=7.0)
txt(330, 100, "nested cross-validation", size=7.0)

# ============================================================ RESULTS column
txt(543, 318, "leave-one-subject-out", size=8.2, weight="bold")
txt(543, 303, "drivers excluded from training", size=6.8, color=INK_SOFT)
tiles = ((485.5, seed_p["pooled"]["AUC"], "SEED-VIG", "AUC", BLUE_DK),
         (543, seed_p["subject_AUC_median"], "SEED-VIG", "per driver", BLUE_DK),
         (600, dd_p["subject_AUC_median"], "DD-Database", "per driver", ORANGE))
for cx, val, ds, lab, col in tiles:
    round_box(cx - 26, 230, cx + 26, 285, r=4, lw=0.8)
    txt(cx, 268, f"{val:.1f}%", size=10.5, color=col, weight="bold")
    txt(cx, 252, ds, size=5.8, color=INK_SOFT)
    txt(cx, 241, lab, size=5.8, color=INK_SOFT)
txt(543, 219, "AUC; per driver: median per-driver AUC", size=5.8, color=INK_SOFT)

round_box(460, 100, 625, 205, r=5, ec="#9C7A63", lw=1.0)
txt(543, 176, f"{xfer['pooled']['AUC']:.1f}% AUC", size=17, color=INK, weight="bold")
txt(543, 148, "trained on DD-Database,", size=7.2)
txt(543, 135, "tested on SEED-VIG,", size=7.2)
txt(543, 122, "no retraining", size=7.2)

# ------------------------------------------------------------- footer strip
round_box(23, 34, 637, 61, r=5, lw=0.8, ec=CARD_BORDER)
txt(330, 47.5, f"{n_drivers} test drivers, two public datasets     |     "
               f"coherence tested per driver and per reference     |     {rt:.0f} ms per epoch", size=7.6)

os.makedirs(os.path.dirname(OUT_MAIN), exist_ok=True)
fig.savefig(OUT_MAIN, dpi=300, facecolor=BG)
os.makedirs(os.path.dirname(OUT_PORTAL), exist_ok=True)
fig.savefig(OUT_PORTAL, dpi=100, facecolor=BG)
plt.close(fig)

from PIL import Image  # noqa: E402  (matplotlib already depends on Pillow)

Image.open(OUT_PORTAL).convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(OUT_PORTAL,
                                                                                               optimize=True)
for p in (OUT_MAIN, OUT_PORTAL):
    with Image.open(p) as im:
        print(f"{os.path.relpath(p, R1)}: {im.size[0]} x {im.size[1]} px, {os.path.getsize(p) / 1024:.0f} kB")
