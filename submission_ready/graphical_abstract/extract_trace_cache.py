"""
Pull two real O1/O2 epochs out of epochs_raw_cache.npz and cache them next to
the graphical-abstract script.

The full cache is 133 MB, which is not something make_gagraphic.py should have
to load. This writes a ~25 kB npz holding one awake and one drowsy 10-second
epoch, so the traces drawn in the graphical abstract are real recorded EEG
rather than a hand-drawn squiggle.

Run once:  python extract_trace_cache.py
"""

import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(REPO, "epochs_raw_cache.npz")
OUT = os.path.join(HERE, "ga_trace_cache.npz")

z = np.load(SRC, allow_pickle=True)
X, y, subject = z["X"], z["y"], z["subject"]
print(f"cache: X={X.shape}, labels={np.unique(y)}, subjects={np.unique(subject)}")

# 05M is the representative subject used for the raw-vs-EMA figure in the
# manuscript, so keep the graphical abstract on the same subject.
subj = "05M" if "05M" in set(np.asarray(subject).tolist()) else np.unique(subject)[0]
mask = np.asarray(subject) == subj


def pick(label):
    """Median-amplitude epoch of this class: representative, not cherry-picked."""
    idx = np.flatnonzero(mask & (np.asarray(y) == label))
    amp = X[idx].std(axis=(1, 2))
    return idx[np.argsort(amp)[len(idx) // 2]]


i_awake, i_drowsy = pick(0), pick(1)
np.savez_compressed(OUT,
                    awake=X[i_awake].astype(np.float32),
                    drowsy=X[i_drowsy].astype(np.float32),
                    subject=str(subj), fs=128.0)

print(f"subject {subj}: awake epoch {i_awake}, drowsy epoch {i_drowsy}")
print(f"wrote {OUT}  ({os.path.getsize(OUT) / 1024:.1f} kB)")
