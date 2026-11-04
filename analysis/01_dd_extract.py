"""Extract features from the ORIGINAL DD-Database recordings.

The earlier pipeline read the original EDFs through MNE, whose reader does not
recognise the files' unit label "uV." and returns the microvolt numbers as if
they were volts. The old export step then wrote them with a +/-3200 uV range,
saturating 99.7 % of samples (three distinct values). This script reads the
originals directly, establishes the scale explicitly, refuses clipped input,
and computes:

  * the published 50-feature set on 1-40 Hz band-passed O1/O2 (primary);
  * the 10 lean features on unfiltered O1/O2 (sensitivity analysis S4);
  * band-passed O1/O2 epochs for the Riemannian and EEGNet baselines.

Outputs (caches/, not tracked): dd_features_v2.npz, dd_epochs_v2.npz
Result: results/dd_extract.json
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

CHANNELS = ["O1-Ref", "O2-Ref"]


def edf_units(path):
    with open(path, "rb") as f:
        h = f.read(256)
        ns = int(h[252:256].decode().strip())
        rest = f.read(ns * 256)
    labels = [rest[i * 16:(i + 1) * 16].decode("latin-1").strip() for i in range(ns)]
    off = 16 * ns + 80 * ns
    dims = [rest[off + i * 8: off + (i + 1) * 8].decode("latin-1").strip() for i in range(ns)]
    return dict(zip(labels, dims))


def load_uv(path, filtered=True):
    import mne
    mne.set_log_level("ERROR")
    raw = mne.io.read_raw_edf(path, preload=True)
    raw.pick(CHANNELS)
    if filtered:
        raw.filter(1.0, 40.0, fir_design="firwin")
    x = raw.get_data()
    med = float(np.median(np.abs(x)))
    if 0.05 < med < 5000:          # MNE returned the file's microvolt numbers as "volts"
        scale = 1.0
    elif 5e-8 < med < 5e-3:        # genuinely volts
        scale = 1e6
    else:
        raise ValueError(f"cannot establish units for {path}: median |x| = {med}")
    return x * scale, scale, int(raw.info["sfreq"])


def one_trial(args):
    subj, trial = args
    path = os.path.join(C.DD_DIR, f"{subj}_{trial}.edf")
    units = edf_units(path)
    xf, scale, fs = load_uv(path, filtered=True)
    assert fs == C.FS, fs
    distinct = len(np.unique(np.round(xf[0, :200000], 6)))
    if distinct < 1000:
        raise ValueError(f"{path}: only {distinct} distinct values - clipped input")
    xr, _, _ = load_uv(path, filtered=False)
    n = xf.shape[1] // C.EPOCH
    rows50, rows10u, epochs = [], [], []
    for i in range(n):
        sl = slice(i * C.EPOCH, (i + 1) * C.EPOCH)
        f50 = C.feats_epoch_50(xf[0, sl], xf[1, sl])
        rows50.append(f50)
        fu = C.feats_epoch_50(xr[0, sl], xr[1, sl])
        rows10u.append([fu[k] for k in C.LEAN])
        epochs.append(xf[:, sl].astype(np.float32))
    cols = list(rows50[0].keys())
    return {"subj": subj, "trial": int(trial), "n": n, "cols": cols,
            "X50": np.array([[r[c] for c in cols] for r in rows50]),
            "X10u": np.array(rows10u), "E": np.stack(epochs),
            "unit_field": units.get("O1-Ref"), "scale": scale, "distinct_values": distinct,
            "median_abs_uV": float(np.median(np.abs(xf[0])))}


# theta and beta O1-O2 coherence of subject 01M, trial 1, epochs 0-4, computed
# independently from the original recording on 14 Oct 2026 (gap analysis F6).
SPOT_CHECK = {"coh_theta": [0.9296, 0.7936, 0.6329, 0.7914, 0.7145],
              "coh_beta": [0.6691, 0.4909, 0.4687, 0.5573, 0.4312]}


def spot_check(X50, cols, subj, trial):
    m = (subj == "01M") & (trial == 1)
    worst = 0.0
    for name, ref in SPOT_CHECK.items():
        got = X50[m][:5, cols.index(name)]
        worst = max(worst, float(np.max(np.abs(got - np.array(ref)))))
    assert worst < 1e-4, f"spot check failed: max deviation {worst}"
    return worst


def main():
    t0 = time.time()
    path = os.path.join(C.CACHES, "dd_features_v2.npz")
    if "--check-only" in sys.argv:
        z = np.load(path, allow_pickle=True)
        print("spot check max deviation:", spot_check(z["X50"], [str(c) for c in z["cols"]], z["subject"], z["trial"]))
        return
    jobs = [(s, t) for s in C.DD_SUBJECTS for t in ("1", "2")]
    with Pool(min(8, os.cpu_count() or 2)) as pool:
        parts = pool.map(one_trial, jobs)
    cols = parts[0]["cols"]
    assert all(p["cols"] == cols for p in parts)
    X50 = np.vstack([p["X50"] for p in parts])
    X10u = np.vstack([p["X10u"] for p in parts])
    E = np.concatenate([p["E"] for p in parts])
    subj = np.concatenate([[p["subj"]] * p["n"] for p in parts])
    trial = np.concatenate([[p["trial"]] * p["n"] for p in parts])
    t = np.concatenate([np.arange(p["n"]) * C.EPOCH_SEC for p in parts]).astype(float)
    rec = np.array([f"{s}_{tr}" for s, tr in zip(subj, trial)])
    np.savez_compressed(path, X50=X50, cols=np.array(cols),
                        X10u=X10u, subject=subj, trial=trial, t=t, recording=rec)
    np.savez_compressed(os.path.join(C.CACHES, "dd_epochs_v2.npz"), E=E, subject=subj, trial=trial, t=t)
    repro = spot_check(X50, cols, subj, trial)
    C.write_result("dd_extract", {
        "source": C.shown_path(C.DD_DIR), "n_epochs": int(len(t)), "n_trials": len(parts),
        "epochs_per_trial": {f"{p['subj']}_{p['trial']}": p["n"] for p in parts},
        "unit_field_in_edf": sorted({p["unit_field"] for p in parts}),
        "scale_applied": sorted({p["scale"] for p in parts}),
        "min_distinct_values_first_200k_samples": min(p["distinct_values"] for p in parts),
        "median_abs_uV_range": [min(p["median_abs_uV"] for p in parts), max(p["median_abs_uV"] for p in parts)],
        "spot_check_max_deviation": repro,
        "elapsed_s": time.time() - t0,
    }, __file__)


if __name__ == "__main__":
    main()
