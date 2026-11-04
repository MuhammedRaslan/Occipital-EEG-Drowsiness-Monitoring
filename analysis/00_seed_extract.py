"""Build the SEED-VIG lean-feature cache from the distributed recordings.

The same extraction as the earlier script that built the cache behind the
paper: O1 and O2 of the 17 channels, resampled from 200 to
128 Hz without further filtering; 10-s non-overlapping epochs; each epoch takes
the mean PERCLOS of the 8-s windows it overlaps; below 0.35 is alert (0), above
0.70 is drowsy (1), and intermediate epochs are dropped. That script cannot be
imported, because it runs its whole analysis on import, so the steps are here.

    SEED_VIG_DIR   folder holding Raw_Data/ and perclos_labels/ as distributed
    SEED_CACHE     output file (default: data/features_seed_vig_cache.npz,
                   where common.py looks for it)

If the cache already exists the script does nothing, so run_all.py can call it
unconditionally. The analyses in this folder start from the cache.

Output: features_seed_vig_cache.npz
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

O1_IDX, O2_IDX = 14, 16  # zero-based positions in the 17-channel recordings
PERCLOS_WINDOW_SEC = 8
ALERT_BELOW, DROWSY_ABOVE = 0.35, 0.70


def lean_features(o1, o2):
    import antropy as ant
    paf = abs(C.peak_alpha_freq(o1, C.FS) - C.peak_alpha_freq(o2, C.FS))
    return [float(ant.sample_entropy(o1, order=2)), float(ant.sample_entropy(o2, order=2)),
            float(ant.perm_entropy(o1, order=3, normalize=True)), float(ant.perm_entropy(o2, order=3, normalize=True)),
            C.aperiodic_slope(o1, C.FS), C.aperiodic_slope(o2, C.FS), paf,
            C.band_coherence(o1, o2, C.FS, C.BANDS["theta"]), C.band_coherence(o1, o2, C.FS, C.BANDS["alpha"]),
            C.band_coherence(o1, o2, C.FS, C.BANDS["beta"])]


def extract(seed_dir):
    import scipy.io as sio
    from scipy.signal import resample_poly

    raw_dir, label_dir = os.path.join(seed_dir, "Raw_Data"), os.path.join(seed_dir, "perclos_labels")
    X, y, subject, times = [], [], [], []
    for name in sorted(f for f in os.listdir(raw_dir) if f.endswith(".mat")):
        eeg = sio.loadmat(os.path.join(raw_dir, name))["EEG"][0, 0]
        data = eeg["data"]
        rate = int(np.asarray(eeg["sample_rate"]).ravel()[0])
        o1 = resample_poly(data[:, O1_IDX], C.FS, rate)
        o2 = resample_poly(data[:, O2_IDX], C.FS, rate)
        perclos = np.asarray(sio.loadmat(os.path.join(label_dir, name))["perclos"]).ravel()
        kept = 0
        for i in range(len(o1) // C.EPOCH):
            start, end = i * C.EPOCH_SEC, (i + 1) * C.EPOCH_SEC
            first = int(np.floor(start / PERCLOS_WINDOW_SEC))
            last = int(np.ceil(end / PERCLOS_WINDOW_SEC))
            if last > len(perclos):
                break
            value = float(np.mean(perclos[first:last]))
            if ALERT_BELOW <= value <= DROWSY_ABOVE:
                continue
            X.append(lean_features(o1[i * C.EPOCH:(i + 1) * C.EPOCH], o2[i * C.EPOCH:(i + 1) * C.EPOCH]))
            y.append(0 if value < ALERT_BELOW else 1)
            subject.append(name.split("_")[0])
            times.append(start)
            kept += 1
        print(f"{name}: kept {kept} epochs", flush=True)
    return (np.asarray(X, dtype=float), np.asarray(y, dtype=int), np.asarray(subject),
            np.asarray(times, dtype=int))


def main():
    if os.path.exists(C.SEED_CACHE):
        print(f"SEED-VIG cache present: {C.SEED_CACHE}")
        return
    seed_dir = os.environ.get("SEED_VIG_DIR")
    if not seed_dir:
        sys.exit("SEED-VIG cache not found; set SEED_VIG_DIR to the folder holding Raw_Data/ and perclos_labels/")
    X, y, subject, times = extract(seed_dir)
    np.savez_compressed(C.SEED_CACHE, X=X, y=y, subject=subject, time_s=times, feat_names=np.array(C.LEAN))
    print(f"wrote {C.SEED_CACHE}: {X.shape[0]} epochs, {int((y == 0).sum())} alert, {int((y == 1).sum())} drowsy")


if __name__ == "__main__":
    main()
