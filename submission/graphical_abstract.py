"""
Graphical abstract for IEEE Sensors Journal submission.
Single self-contained figure summarising the complete pipeline:
  raw EEG (O1, O2)  ->  10 features  ->  shrinkage LDA  ->  causal EMA
  ->  per-driver percentile threshold  ->  monitoring + pro-active outputs
plus the two headline numbers (F1=76.79 monitoring, +31.7 min advance lead).

Aspect ratio is ~2:1 (wide), as Sensors expects ~7 cm tall when printed.
"""
import os, sys, io
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "figures", "graphical_abstract.png")

fig, ax = plt.subplots(figsize=(11.5, 5.5))
ax.set_xlim(0, 100); ax.set_ylim(0, 100)
ax.axis("off")

# colour palette (keep colour-blind-friendly)
C_INPUT  = "#1f3b6e"
C_PROC   = "#3d6e9c"
C_LOGIC  = "#c75f1e"
C_OUT_M  = "#1a7f3d"
C_OUT_P  = "#a02a2a"
C_BOX_BG = "#f4f4f4"
C_TXT    = "#222222"

def box(x, y, w, h, label, color, fontsize=10, weight="normal"):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0.4",
                       linewidth=1.2, edgecolor=color,
                       facecolor=C_BOX_BG)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, label,
            ha="center", va="center", fontsize=fontsize,
            color=C_TXT, weight=weight, wrap=True)

def arrow(x1, y1, x2, y2, color="#444"):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle="-|>", mutation_scale=14,
                        linewidth=1.5, color=color)
    ax.add_patch(a)

# ── Top row: pipeline ──────────────────────────────────────────────────
y_top = 60
box(2,  y_top, 14, 16, "Raw EEG\n$O_1$, $O_2$\n128 Hz, 10-s epochs", C_INPUT, fontsize=10)
arrow(16, y_top + 8, 22, y_top + 8)
box(22, y_top, 16, 16, "10 lean features\nentropy + 1/f slope\n+ $O_1$-$O_2$ coherence", C_PROC, fontsize=10)
arrow(38, y_top + 8, 44, y_top + 8)
box(44, y_top, 14, 16, "Shrinkage LDA\nLOSO trained\n$p_t$(drowsy)", C_PROC, fontsize=10)
arrow(58, y_top + 8, 64, y_top + 8)
box(64, y_top, 14, 16, "Causal EMA\n$\\tau\\!=\\!600$ s\n(monitoring)", C_LOGIC, fontsize=10)
arrow(78, y_top + 8, 84, y_top + 8)
box(84, y_top, 14, 16, "Per-driver\n99-pct threshold\n5-min calibration", C_LOGIC, fontsize=10)

# ── Outputs split ──────────────────────────────────────────────────────
# Decision diamond / split symbol from the threshold box
arrow(91, y_top, 80, 38, color=C_OUT_M)
arrow(91, y_top, 92, 38, color=C_OUT_P)

# Monitoring output (left lower)
box(50, 22, 30, 16,
    "MONITORING\nDROZY LOSO  F1 = 76.79\nAUC = 76.62  $\\kappa$ = 0.539\nPooled (31 subj) F1 = 66.13",
    C_OUT_M, fontsize=10, weight="bold")

# Pro-active output (right lower)
box(82, 22, 16, 16,
    "PRO-ACTIVE\n+8.83 min\nat PERCLOS 0.30\n0.0% session FA",
    C_OUT_P, fontsize=9.5, weight="bold")

# ── Footer banner: target form factor & deployment ────────────────────
box(2, 4, 96, 10,
    "  Two-channel occipital headrest EEG  •  56 ms / epoch on Cortex-M4 envelope  •  "
    "validated under strict subject-out LOSO on DROZY (10) + SEED-VIG (21) + pooled (31)  ",
    "#777777", fontsize=10)

# ── Title ──────────────────────────────────────────────────────────────
ax.text(50, 92,
        "Pro-Active Driver Drowsiness Monitoring Using Two-Channel Occipital EEG",
        ha="center", va="center", fontsize=13, weight="bold", color=C_TXT)
ax.text(50, 86,
        "Lean LDA + causal smoothing + per-driver calibration  →  "
        "76.79 F1 monitoring  &  median +31.67 min advance prediction at 9.5 % session false-alert rate",
        ha="center", va="center", fontsize=10, color=C_TXT)

fig.savefig(OUT_PATH, dpi=240, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"  graphical abstract -> {OUT_PATH}")
