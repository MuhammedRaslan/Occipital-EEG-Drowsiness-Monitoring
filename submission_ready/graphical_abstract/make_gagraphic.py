"""
Graphical abstract for the IEEE Sensors Journal submission.

Visual language follows the group's conference-poster style: a blue title band,
rounded blue pill section headers, a left-to-right flow with real recorded data
on the input side, and a metric-evaluation panel on the output side.

It is held to the IEEE Sensors Council "Graphical Abstract Instructions" spec,
which the poster style is compressed to fit:
    dimensions   672 x 456 px  (3.5 in x 2.38 in @ 192 dpi)
    file size    < 45 kB  (enforced below by palette quantisation)
    file name    gagraphic.png
    caption      <= 30 words, supplied separately in gagraphic_caption.txt

Two deliberate departures from the poster, both forced by the 3.5 in width:

  * The band carries a shortened descriptive header, not the 108-character
    paper title. At this width the full title renders at about 4 pt, which is
    below anything IEEE will accept, and Xplore already prints the real title
    directly beside the graphic.
  * Section text is cut to pill labels and short box captions. Too much text is
    the most common reason a graphical abstract is sent back.

Every number and every waveform here is real:
  * EEG traces        one awake and one drowsy 10-s epoch from subject 05M,
                      via ga_trace_cache.npz (see extract_trace_cache.py)
  * monitoring bars   publication_results_v17_roc.json, v16 pooled LOSO
  * advance warning   publication_results_v20_severity.json

Run:  python make_gagraphic.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.abspath(os.path.join(HERE, "..", "..", "submission",
                                       "supplementary", "results"))
OUT = os.path.join(HERE, "gagraphic.png")

W_IN, H_IN, DPI = 3.5, 2.375, 192          # -> 672 x 456 px exactly
TARGET_PX = (672, 456)
MAX_BYTES = 45 * 1024

# Poster palette.
C_BAND = "#6C8FD8"      # title band and pill headers
C_BAND_D = "#4E6FB4"    # pill edge / arrow
C_INK = "#1A1A1A"
C_MUTE = "#6B7785"
C_O1 = "#0072B2"        # channel O1 / primary result  (Okabe-Ito blue)
C_O2 = "#009E73"        # channel O2                   (Okabe-Ito green)
C_HOT = "#D55E00"       # behavioural onset            (Okabe-Ito vermilion)
C_PANEL = "#F3F6FB"
C_EDGE = "#C3D0E6"

# ----------------------------------------------------------------------
# Real data
# ----------------------------------------------------------------------
tr = np.load(os.path.join(HERE, "ga_trace_cache.npz"), allow_pickle=True)
awake, drowsy, fs = tr["awake"], tr["drowsy"], float(tr["fs"])

roc = json.load(open(os.path.join(RESULTS, "publication_results_v17_roc.json")))
f1 = roc["operating_points"]["default_thr050"]["f1_score"]        # 76.79
auc = roc["auc_roc_smoothed"]                                     # 76.62

pooled_f1 = json.load(open(os.path.join(
    RESULTS, "publication_results_v16.json")))["overall_concat"]["f1_score"]   # 66.13

sev = json.load(open(os.path.join(RESULTS,
                                  "publication_results_v20_severity.json")))["severity_sweep"]["0.7"]
leads = np.asarray(sev["paired_leads"], dtype=float)
median_lead = sev["median_lead_min"]
proactive_rate = sev["proactive_rate"]

plt.rcParams.update({"axes.linewidth": 0.5})
SERIF = {"family": "DejaVu Serif"}
SANS = {"family": "DejaVu Sans"}

fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI)
fig.patch.set_facecolor("white")


def pill(x_centre, y, text, width, fontsize=6.2):
    """Rounded blue section header, as on the poster."""
    fig.patches.append(FancyBboxPatch(
        (x_centre - width / 2, y), width, 0.062,
        boxstyle="round,pad=0.002,rounding_size=0.030",
        transform=fig.transFigure, linewidth=0,
        facecolor=C_BAND, zorder=3))
    fig.text(x_centre, y + 0.031, text, ha="center", va="center",
             fontsize=fontsize, weight="bold", color="white", zorder=4,
             **SERIF)


def panel(x0, x1, y0, y1):
    # zorder below zero: figure-level patches are drawn after Axes at equal
    # zorder, which would hide every plot inside the panel.
    fig.patches.append(FancyBboxPatch(
        (x0, y0), x1 - x0, y1 - y0,
        boxstyle="round,pad=0.003,rounding_size=0.014",
        transform=fig.transFigure, linewidth=0.6,
        edgecolor=C_EDGE, facecolor=C_PANEL, zorder=-5))


def flow_arrow(x0, x1, y):
    fig.patches.append(FancyArrowPatch(
        (x0, y), (x1, y), transform=fig.transFigure,
        arrowstyle="-|>", mutation_scale=9, linewidth=1.6,
        color=C_BAND_D, zorder=5))


# ======================================================================
# Title band
# ======================================================================
fig.patches.append(FancyBboxPatch(
    (0, 0.858), 1.0, 0.142, boxstyle="square,pad=0",
    transform=fig.transFigure, linewidth=0, facecolor=C_BAND, zorder=2))
fig.text(0.5, 0.955, "Pro-Active Driver Drowsiness Monitoring",
         ha="center", va="center", fontsize=9.2, weight="bold",
         color="white", zorder=3, **SERIF)
fig.text(0.5, 0.892, "Inter-hemispheric occipital coherence from two headrest electrodes",
         ha="center", va="center", fontsize=5.9, color="#EAF0FC",
         zorder=3, **SERIF)

# Column geometry
AX0, AX1 = 0.015, 0.350
BX0, BX1 = 0.388, 0.612
CX0, CX1 = 0.650, 0.985
PY0, PY1 = 0.125, 0.775          # panel body
PILL_Y = 0.788

panel(AX0, AX1, PY0, PY1)
panel(BX0, BX1, PY0, PY1)
panel(CX0, CX1, PY0, PY1)
pill((AX0 + AX1) / 2, PILL_Y, "SENSING", AX1 - AX0)
pill((BX0 + BX1) / 2, PILL_Y, "PIPELINE", BX1 - BX0)
pill((CX0 + CX1) / 2, PILL_Y, "RESULTS", CX1 - CX0)
flow_arrow(AX1 + 0.006, BX0 - 0.006, 0.45)
flow_arrow(BX1 + 0.006, CX0 - 0.006, 0.45)

# ======================================================================
# A -- SENSING: headrest schematic above two real EEG epochs
# ======================================================================
axH = fig.add_axes([AX0 + 0.012, 0.545, (AX1 - AX0) - 0.024, 0.205])
axH.set_aspect("equal")
axH.set_xlim(0, 1)
axH.set_ylim(0, 0.205 * H_IN / (((AX1 - AX0) - 0.024) * W_IN))
axH.axis("off")
axH.patch.set_alpha(0)
YT = axH.get_ylim()[1]

axH.add_patch(FancyBboxPatch((0.20, 0.03 * YT), 0.60, 0.26 * YT,
                             boxstyle="round,pad=0.008,rounding_size=0.05",
                             linewidth=0.6, edgecolor=C_MUTE,
                             facecolor="#D8DEE8", zorder=1))
axH.text(0.50, 0.145 * YT, "headrest", ha="center", va="center",
         fontsize=4.6, color="#5A6675", zorder=4, **SANS)

HC, HR = (0.50, 0.560 * YT), 0.335 * YT
axH.add_patch(Circle(HC, HR, linewidth=0.9, edgecolor="#3A4A5C",
                     facecolor="white", zorder=2))
axH.add_patch(Polygon([[0.462, HC[1] + HR - 0.004],
                       [0.50, HC[1] + HR + 0.055],
                       [0.538, HC[1] + HR - 0.004]],
                      closed=True, linewidth=0.9, edgecolor="#3A4A5C",
                      facecolor="white", zorder=2))
epos = []
for ang, lab, dx, ha, col in ((234.0, "O$_1$", -0.045, "right", C_O1),
                              (306.0, "O$_2$", 0.045, "left", C_O2)):
    x = HC[0] + HR * np.cos(np.radians(ang))
    yy = HC[1] + HR * np.sin(np.radians(ang))
    epos.append((x, yy))
    axH.add_patch(Circle((x, yy), 0.030, linewidth=0.7, edgecolor="white",
                         facecolor=col, zorder=6))
    axH.text(x + dx, yy, lab, ha=ha, va="center", fontsize=5.6,
             weight="bold", color=col, zorder=6, **SANS)
# Plain dashed chord between the electrodes. An arrowed arc was tried first:
# at this size the two arrowheads swamp the curve and read as a blob.
axH.plot([epos[0][0] + 0.030, epos[1][0] - 0.030],
         [epos[0][1] + 0.010, epos[1][1] + 0.010],
         color=C_BAND_D, linewidth=0.9, linestyle=(0, (2.2, 1.4)), zorder=5)

# two real 10-second epochs, O1 and O2 overlaid
t = np.arange(awake.shape[1]) / fs
scale = float(np.percentile(np.abs(np.concatenate([awake, drowsy], axis=1)), 99))
for k, (sig, name) in enumerate(((awake, "awake"), (drowsy, "drowsy"))):
    ax = fig.add_axes([AX0 + 0.020, 0.365 - k * 0.155, (AX1 - AX0) - 0.038, 0.115])
    ax.plot(t, sig[0] / scale, color=C_O1, linewidth=0.35)
    ax.plot(t, sig[1] / scale - 2.1, color=C_O2, linewidth=0.35)
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(-4.0, 2.0)
    ax.axis("off")
    ax.patch.set_alpha(0)
    ax.text(0.0, 1.02, name, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=5.0, weight="bold",
            color=C_INK if name == "awake" else C_HOT, **SANS)

fig.text((AX0 + AX1) / 2, 0.150, "$O_1$–$O_2$ coherence falls",
         ha="center", va="center", fontsize=5.4, weight="bold",
         color=C_BAND_D, **SANS)

# ======================================================================
# B -- PIPELINE
# ======================================================================
steps = ("10 lean features\nentropy · 1/f slope\n$O_1$–$O_2$ coherence",
         "shrinkage LDA\n$p_t$(drowsy)",
         "causal EMA\n+ per-driver\nthreshold")
box_h, gap = 0.150, 0.062
top = 0.735
for i, s in enumerate(steps):
    y0 = top - box_h - i * (box_h + gap)
    fig.patches.append(FancyBboxPatch(
        (BX0 + 0.016, y0), (BX1 - BX0) - 0.032, box_h,
        boxstyle="round,pad=0.003,rounding_size=0.012",
        transform=fig.transFigure, linewidth=0.7,
        edgecolor=C_BAND_D, facecolor="white", zorder=3))
    fig.text((BX0 + BX1) / 2, y0 + box_h / 2, s, ha="center", va="center",
             fontsize=5.0, color=C_INK, linespacing=1.35, zorder=4, **SANS)
    if i < len(steps) - 1:
        fig.patches.append(FancyArrowPatch(
            ((BX0 + BX1) / 2, y0 - 0.006),
            ((BX0 + BX1) / 2, y0 - gap + 0.006),
            transform=fig.transFigure, arrowstyle="-|>", mutation_scale=6,
            linewidth=1.0, color=C_BAND_D, zorder=4))

# ======================================================================
# C -- RESULTS: metric bars, then the advance-warning result
# ======================================================================
axM = fig.add_axes([CX0 + 0.052, 0.505, (CX1 - CX0) - 0.075, 0.185])
names = ("F1", "AUC", "pooled\nF1")
vals = (f1, auc, pooled_f1)
bars = axM.bar(range(3), vals, width=0.60,
               color=[C_O1, "#4C9FD4", C_O2], edgecolor="white", linewidth=0.4)
for b, v in zip(bars, vals):
    axM.text(b.get_x() + b.get_width() / 2, v + 3.5, f"{v:.1f}",
             ha="center", va="bottom", fontsize=5.0, weight="bold",
             color=C_INK, **SANS)
axM.set_ylim(0, 100)
axM.set_xticks(range(3))
axM.set_xticklabels(names, fontsize=4.6, color=C_INK, linespacing=1.1, **SANS)
axM.set_yticks([0, 50, 100])
axM.set_yticklabels(["0", "50", "100"], fontsize=4.6, color=C_MUTE, **SANS)
axM.tick_params(length=1.5, pad=1.0)
for s in ("top", "right"):
    axM.spines[s].set_visible(False)
for s in ("left", "bottom"):
    axM.spines[s].set_color(C_MUTE)
axM.patch.set_alpha(0)
fig.text((CX0 + CX1) / 2, 0.718, "subject-independent LOSO  (%)",
         ha="center", va="center", fontsize=5.0, weight="bold",
         color=C_INK, **SANS)

fig.text((CX0 + CX1) / 2, 0.352,
         f"advance warning, {leads.size} sessions",
         ha="center", va="center", fontsize=5.0, weight="bold",
         color=C_O1, **SANS)

axL = fig.add_axes([CX0 + 0.032, 0.190, (CX1 - CX0) - 0.056, 0.128])
rng = np.random.default_rng(20260805)
axL.scatter(-leads, rng.uniform(0.13, 0.66, size=leads.size), s=4.0,
            facecolor=C_O1, edgecolor="white", linewidth=0.2, zorder=4)
axL.axvline(0.0, color=C_HOT, linewidth=1.1, zorder=3)
axL.axvline(-median_lead, color=C_O1, linewidth=0.8,
            linestyle=(0, (2.4, 1.4)), zorder=3)
axL.annotate("", xy=(0.0, 0.80), xytext=(-median_lead, 0.80),
             arrowprops=dict(arrowstyle="<->", linewidth=0.7, color=C_INK))
axL.text(-95, 0.93, f"median {median_lead:.1f} min", ha="left",
         va="center", fontsize=5.2, weight="bold", color=C_INK, **SANS)
axL.set_xlim(-97, 12)
axL.set_ylim(0, 1)
axL.set_yticks([])
axL.set_xticks([-90, -60, -30, 0])
axL.set_xticklabels(["90", "60", "30", "0"], fontsize=4.6, color=C_INK, **SANS)
# tie the orange onset line to the axis instead of spending a text label on it
axL.get_xticklabels()[-1].set_color(C_HOT)
axL.get_xticklabels()[-1].set_weight("bold")
axL.tick_params(axis="x", length=1.5, pad=1.0)
axL.set_xlabel("min before behavioural onset", fontsize=4.8, color=C_INK,
               labelpad=0.8, **SANS)
for s in ("top", "right", "left"):
    axL.spines[s].set_visible(False)
axL.spines["bottom"].set_color(C_MUTE)
axL.patch.set_alpha(0)

# ======================================================================
# Footer
# ======================================================================
fig.patches.append(FancyBboxPatch(
    (0.015, 0.012), 0.970, 0.092,
    boxstyle="round,pad=0.003,rounding_size=0.012",
    transform=fig.transFigure, linewidth=0.6,
    edgecolor=C_EDGE, facecolor=C_PANEL, zorder=-5))
fig.text(0.5, 0.058,
         f"31 subjects   ·   {proactive_rate * 100:.1f} % of sessions warned "
         "early   ·   56 ms/epoch, ~100 B model",
         ha="center", va="center", fontsize=5.4, color=C_INK, zorder=2, **SANS)

fig.savefig(OUT, dpi=DPI, facecolor="white")
plt.close(fig)

# ----------------------------------------------------------------------
# Enforce the spec: exact pixel size, no alpha channel, < 45 kB
# ----------------------------------------------------------------------
im = Image.open(OUT).convert("RGB")
if im.size != TARGET_PX:
    im = im.resize(TARGET_PX, Image.LANCZOS)
im.save(OUT, format="PNG", optimize=True, dpi=(DPI, DPI))

size = os.path.getsize(OUT)
if size > MAX_BYTES:
    for colors in (256, 192, 128, 96, 64):
        im.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT) \
          .save(OUT, format="PNG", optimize=True, dpi=(DPI, DPI))
        size = os.path.getsize(OUT)
        if size <= MAX_BYTES:
            break

final = Image.open(OUT)
print(f"{OUT}\n  {final.size[0]}x{final.size[1]} px, mode={final.mode}, "
      f"{size / 1024:.1f} kB  (limit {MAX_BYTES / 1024:.0f} kB)")
