"""
Programmatic live-demo figure + MP4 (Tier-1 #4 substitute)
==========================================================
Rather than a manually-captured Streamlit screen recording (which is
non-reproducible and cannot be re-built from the reproducer), we produce
a fully-programmatic demonstration of the v20 algorithm running on
representative SEED-VIG subjects. Two artefacts:

  1. `publication_figures_v5/fig12_live_demo.png` — three subjects laid
     out side-by-side: a strong-lead case, a median-lead case, and a
     marginal case. For each, we show the raw p(drowsy), the causal-EMA
     smoothed posterior, the per-subject percentile threshold, the
     PERCLOS trace on a secondary axis, and the two onset markers.
     This is the paper's live-system figure.

  2. `demo_v20.mp4` — optional animated playback of the median-lead
     subject. Scrubs time from session start to end so a reviewer can
     see the alert fire before the camera onset.

Requires ffmpeg on PATH for the MP4 write; the PNG figure is produced
unconditionally. If ffmpeg is missing the MP4 step is skipped with a
warning.
"""

import os, sys, io, warnings, shutil
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import numpy as np
import scipy.io as sio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

warnings.filterwarnings("ignore")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_CACHE  = os.path.join(_SCRIPT_DIR, "features_seed_vig_cache.npz")
SEED_DIR    = r"c:/Users/muham/OneDrive/Documents/#1_DMS/SEED-VIG"
LBL_DIR     = os.path.join(SEED_DIR, "perclos_labels")
FIG_DIR     = os.path.join(_SCRIPT_DIR, "publication_figures_v5")
FIG_PATH    = os.path.join(FIG_DIR, "fig12_live_demo.png")
MP4_PATH    = os.path.join(_SCRIPT_DIR, "demo_v20.mp4")
GIF_PATH    = os.path.join(_SCRIPT_DIR, "demo_v20.gif")
os.makedirs(FIG_DIR, exist_ok=True)

EPOCH_SEC      = 10
BASELINE_SEC   = 60
CONTINUOUS_SEC = 60
V20_THR_PCT    = 99
V20_BASELINE   = 300
V20_DWELL      = 10
V20_TAU        = 30
PERCLOS_BEH    = 0.70


def causal_ema(p, tau_sec, dt_sec=EPOCH_SEC):
    if tau_sec <= 0: return p.copy()
    alpha = 1.0 - np.exp(-dt_sec / tau_sec)
    out = np.empty_like(p, dtype=float); out[0] = p[0]
    for t in range(1, len(p)):
        out[t] = alpha * p[t] + (1 - alpha) * out[t - 1]
    return out


def first_sustained_crossing(values, thr, sustain_steps):
    if sustain_steps <= 0: sustain_steps = 1
    n = len(values)
    if n < sustain_steps: return None
    for i in range(n - sustain_steps + 1):
        if np.all(values[i:i+sustain_steps] > thr):
            return i
    return None


def find_session_file_for_subject(subj_id):
    files = sorted(f for f in os.listdir(LBL_DIR) if f.endswith(".mat"))
    matches = [f for f in files if f.startswith(f"{subj_id}_")]
    return matches[0][:-4] if matches else None


def perclos_for_subject(file_basename):
    p = sio.loadmat(os.path.join(LBL_DIR, file_basename + ".mat"))["perclos"]
    return np.asarray(p).ravel()


def zscore_seed_cal(X, subj_arr, ts_arr, cal_sec=BASELINE_SEC):
    Xn = X.astype(float).copy()
    for s in np.unique(subj_arr):
        m = subj_arr == s
        fit = m & (ts_arr < cal_sec)
        if not fit.any():
            fit = m & (ts_arr < ts_arr[m].min() + cal_sec)
        mu = Xn[fit].mean(0); sd = Xn[fit].std(0); sd[sd == 0] = 1.0
        Xn[m] = (Xn[m] - mu) / sd
    return Xn


def build_timelines():
    z = np.load(SEED_CACHE, allow_pickle=True)
    X = z["X"]; y = z["y"]; subj = z["subject"]; ts = z["time_s"]
    subjects = sorted(np.unique(subj), key=lambda x: int(x))
    tl = {}
    for s in subjects:
        te = subj == s; tr = ~te
        if te.sum() < 10 or len(np.unique(y[tr])) < 2: continue
        Xtr = zscore_seed_cal(X[tr], subj[tr], ts[tr])
        Xte = zscore_seed_cal(X[te], subj[te], ts[te])
        clf = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        clf.fit(Xtr, y[tr])
        proba = clf.predict_proba(Xte)[:, 1]
        times = ts[te]; order = np.argsort(times)
        fbase = find_session_file_for_subject(s)
        if fbase is None: continue
        perclos = perclos_for_subject(fbase)
        perclos_t = np.arange(len(perclos)) * 8 + 4
        tl[str(s)] = {
            "t":       times[order],
            "p":       proba[order],
            "perclos": np.interp(times[order], perclos_t, perclos),
        }
    return tl


def analyse(tl):
    t, p, pc = tl["t"], tl["p"], tl["perclos"]
    p_sm = causal_ema(p, tau_sec=V20_TAU)
    pc_sm = causal_ema(pc, tau_sec=30)
    bl = p_sm[t < V20_BASELINE]
    if len(bl) < 3: bl = p_sm[:3]
    thr = min(float(np.percentile(bl, V20_THR_PCT)), 0.98)
    dwell = max(1, V20_DWELL // EPOCH_SEC)
    perc_dwell = max(1, CONTINUOUS_SEC // EPOCH_SEC)
    eeg_idx   = first_sustained_crossing(p_sm, thr, dwell)
    behav_idx = first_sustained_crossing(pc_sm, PERCLOS_BEH, perc_dwell)
    eeg_t   = float(t[eeg_idx])   if eeg_idx   is not None else None
    behav_t = float(t[behav_idx]) if behav_idx is not None else None
    lead    = (behav_t - eeg_t) / 60.0 if (eeg_t is not None and behav_t is not None) else None
    return {
        "t": t, "p_raw": p, "p_smooth": p_sm, "pc_raw": pc, "pc_smooth": pc_sm,
        "thr_eeg": thr, "eeg_t": eeg_t, "behav_t": behav_t, "lead_min": lead,
    }


def pick_representative_subjects(analyses):
    # Candidate = subjects with both onsets detected.
    both = [(s, a) for s, a in analyses.items()
            if a["eeg_t"] is not None and a["behav_t"] is not None]
    both.sort(key=lambda kv: kv[1]["lead_min"])
    if not both:
        return []
    strong = both[-1]           # largest positive lead
    # median is the middle subject; marginal is the smallest (possibly negative) positive
    marginal_pool = [b for b in both if b[1]["lead_min"] <= 5]
    marginal = marginal_pool[-1] if marginal_pool else both[0]
    median_idx = len(both) // 2
    median = both[median_idx]
    # Dedup
    picks = []
    for p in (strong, median, marginal):
        if p[0] not in [q[0] for q in picks]:
            picks.append(p)
    return picks


def plot_panel(ax, s, a, title_prefix):
    t_min = a["t"] / 60.0
    ax.plot(t_min, a["p_raw"],    "-", color="#9fb8d9", lw=0.7, alpha=0.6, label="p(drowsy) raw")
    ax.plot(t_min, a["p_smooth"], "-", color="#1f3b6e", lw=1.6, label=f"p(drowsy) EMA tau={V20_TAU}s")
    ax.axhline(a["thr_eeg"], color="#c75f1e", ls="--", lw=1.0,
               label=f"per-subj thr = {a['thr_eeg']:.2f}")
    if a["eeg_t"] is not None:
        ax.axvline(a["eeg_t"]/60.0, color="#c75f1e", lw=1.4, alpha=0.9)
        ax.text(a["eeg_t"]/60.0, 1.02, "EEG onset", color="#c75f1e",
                fontsize=8, ha="center", va="bottom", transform=ax.get_xaxis_transform())
    if a["behav_t"] is not None:
        ax.axvline(a["behav_t"]/60.0, color="#a02a2a", lw=1.4, ls=":")
        ax.text(a["behav_t"]/60.0, 1.02, "PERCLOS onset", color="#a02a2a",
                fontsize=8, ha="center", va="bottom", transform=ax.get_xaxis_transform())
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("p(drowsy)")
    ax.grid(alpha=0.25)

    # PERCLOS on secondary axis
    ax2 = ax.twinx()
    ax2.plot(t_min, a["pc_smooth"], "-", color="#567d46", lw=1.1, alpha=0.8,
             label=f"PERCLOS (30 s smoothed)")
    ax2.axhline(PERCLOS_BEH, color="#567d46", ls=":", lw=0.9, alpha=0.6)
    ax2.set_ylim(0, 1.0)
    ax2.set_ylabel("PERCLOS", color="#567d46")
    ax2.tick_params(axis="y", labelcolor="#567d46")

    lead_txt = f"lead = {a['lead_min']:+.2f} min" if a["lead_min"] is not None else "lead = n/a"
    ax.set_title(f"{title_prefix}  (subj {s})  —  {lead_txt}", fontsize=10)

    return ax2


def build_static_figure(picks, path):
    fig, axes = plt.subplots(len(picks), 1, figsize=(9.0, 2.4 * len(picks)), sharex=False)
    if len(picks) == 1:
        axes = [axes]
    labels = ["Strong-lead case", "Median-lead case", "Marginal-lead case"]
    sec_axes = []
    for ax, (s, a), lbl in zip(axes, picks, labels):
        sec_axes.append(plot_panel(ax, s, a, lbl))
    axes[-1].set_xlabel("Session time (min)")
    # Combined legend on the top panel
    h1, l1 = axes[0].get_legend_handles_labels()
    h2, l2 = sec_axes[0].get_legend_handles_labels()
    axes[0].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, framealpha=0.9)
    fig.suptitle("v20 Pro-Active algorithm running on three representative SEED-VIG subjects\n"
                 "(lean LDA posterior → causal EMA → per-subject 99th-pctile of first 5 min → first sustained crossing)",
                 fontsize=10, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(path, dpi=200)
    plt.close(fig)


def build_animation(pick, path_mp4, path_gif):
    s, a = pick
    t_min = a["t"] / 60.0
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    ax2 = ax.twinx()

    (raw_line,)    = ax.plot([], [], "-", color="#9fb8d9", lw=0.7, alpha=0.6)
    (smooth_line,) = ax.plot([], [], "-", color="#1f3b6e", lw=1.8)
    (pc_line,)     = ax2.plot([], [], "-", color="#567d46", lw=1.2, alpha=0.85)
    ax.axhline(a["thr_eeg"], color="#c75f1e", ls="--", lw=1.0)
    ax2.axhline(PERCLOS_BEH, color="#567d46", ls=":", lw=0.9, alpha=0.6)
    cursor = ax.axvline(t_min[0], color="k", lw=0.7, alpha=0.4)

    eeg_marker = ax.axvline(a["eeg_t"]/60.0, color="#c75f1e", lw=0.0, visible=False)
    behav_marker = ax.axvline(a["behav_t"]/60.0, color="#a02a2a", lw=0.0, ls=":", visible=False)

    ax.set_xlim(t_min.min(), t_min.max())
    ax.set_ylim(0, 1.0); ax2.set_ylim(0, 1.0)
    ax.set_xlabel("Session time (min)")
    ax.set_ylabel("p(drowsy)")
    ax2.set_ylabel("PERCLOS", color="#567d46")
    ax2.tick_params(axis="y", labelcolor="#567d46")
    ax.grid(alpha=0.25)
    status_txt = ax.text(0.02, 0.93, "", transform=ax.transAxes, fontsize=10,
                         bbox=dict(boxstyle="round,pad=0.3", fc="w", ec="0.5", alpha=0.85))
    fig.suptitle(f"v20 Pro-Active algorithm — live playback, subject {s} "
                 f"(lead = {a['lead_min']:+.2f} min)", fontsize=11)

    eeg_step   = int((a["eeg_t"] or 1e9) / EPOCH_SEC)
    behav_step = int((a["behav_t"] or 1e9) / EPOCH_SEC)
    n_steps    = len(t_min)
    frame_stride = max(1, n_steps // 200)   # cap at ~200 frames

    def update(k):
        k = min(k * frame_stride, n_steps - 1)
        raw_line.set_data(t_min[:k+1], a["p_raw"][:k+1])
        smooth_line.set_data(t_min[:k+1], a["p_smooth"][:k+1])
        pc_line.set_data(t_min[:k+1], a["pc_smooth"][:k+1])
        cursor.set_xdata([t_min[k]])
        if k >= eeg_step:
            eeg_marker.set_linewidth(1.5); eeg_marker.set_visible(True)
        if k >= behav_step:
            behav_marker.set_linewidth(1.5); behav_marker.set_visible(True)
        state = "ALERT" if a["p_smooth"][k] > a["thr_eeg"] else "monitoring"
        status_txt.set_text(f"t = {t_min[k]:5.1f} min   p = {a['p_smooth'][k]:.2f}   state = {state}")
        return raw_line, smooth_line, pc_line, cursor, eeg_marker, behav_marker, status_txt

    n_frames = (n_steps + frame_stride - 1) // frame_stride
    ani = FuncAnimation(fig, update, frames=n_frames, blit=False, interval=30)

    writers_tried = []
    if shutil.which("ffmpeg"):
        try:
            ani.save(path_mp4, writer=FFMpegWriter(fps=30, bitrate=1600), dpi=150)
            writers_tried.append(("mp4", True, path_mp4))
            print(f"  MP4 animation -> {path_mp4}")
        except Exception as e:
            writers_tried.append(("mp4", False, str(e)))
            print(f"  MP4 write failed: {e}")
    else:
        print("  ffmpeg not on PATH — skipping MP4; will attempt GIF with Pillow instead.")
    # Also save a GIF as a fallback — Pillow is a pure-Python writer, no external dep.
    try:
        ani.save(path_gif, writer=PillowWriter(fps=15), dpi=110)
        writers_tried.append(("gif", True, path_gif))
        print(f"  GIF animation -> {path_gif}")
    except Exception as e:
        writers_tried.append(("gif", False, str(e)))
        print(f"  GIF write failed: {e}")
    plt.close(fig)
    return writers_tried


def main():
    print("Building LOSO timelines...")
    tl = build_timelines()
    analyses = {s: analyse(t) for s, t in tl.items()}
    picks = pick_representative_subjects(analyses)
    for lbl, (s, a) in zip(("strong", "median", "marginal"), picks):
        print(f"  {lbl:<9} subj {s}  lead = {a['lead_min']:+.2f} min  thr = {a['thr_eeg']:.3f}")

    print()
    print("Writing static figure ...")
    build_static_figure(picks, FIG_PATH)
    print(f"  figure -> {FIG_PATH}")

    print()
    print("Writing animation of the median-lead subject ...")
    build_animation(picks[1], MP4_PATH, GIF_PATH)


if __name__ == "__main__":
    main()
