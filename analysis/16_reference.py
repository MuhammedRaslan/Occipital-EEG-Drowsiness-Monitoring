"""Reference-electrode analysis on the DD-Database.

O1, O2, C3 and C4 in the DD-Database share one reference (A1/A2). A signal on
the reference appears identically in every channel and inflates zero-lag
coherence between any pair. This script measures, per epoch:

  * magnitude-squared coherence (MSC) for O1-O2, C3-C4 and the four
    occipital-central pairs;
  * O1-O2 MSC after re-referencing to the average of the four EEG channels;
  * the zero-lag share of O1-O2 coherency, Re(C)^2 / |C|^2;
  * two measures insensitive to zero-lag coupling: |Im(C)| and the weighted
    phase-lag index (wPLI).

Welch estimate as in the feature code: 2-s Hann segments, 50 % overlap,
segment-mean removed. Drowsy versus alert (self-report labels) is tested per
subject with paired Wilcoxon, Holm-adjusted within each measure family.
SEED-VIG cannot be re-referenced (raw recordings unavailable; the dataset
paper does not report the reference).

Output: results/reference.json
"""
import os
import sys

import mne
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

mne.set_log_level("ERROR")
CH = ["O1-Ref", "O2-Ref", "C3-Ref", "C4-Ref"]
IX = {"O1": 0, "O2": 1, "C3": 2, "C4": 3}
PAIRS = [("O1", "O2"), ("C3", "C4"), ("O1", "C3"), ("O2", "C4"), ("O1", "C4"), ("O2", "C3")]
BANDS = {"theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
NPER, HOP = 256, 128
FREQS = np.fft.rfftfreq(NPER, 1 / C.FS)
WIN = np.hanning(NPER + 1)[:-1]  # periodic Hann, as scipy's default 'hann'


def segment_spectra(x):
    """x: (channels, n_epochs, 1280) -> (channels, n_epochs, n_seg, n_freq) complex."""
    starts = range(0, C.EPOCH - NPER + 1, HOP)
    segs = np.stack([x[..., s:s + NPER] for s in starts], axis=2)
    segs = segs - segs.mean(axis=-1, keepdims=True)
    return np.fft.rfft(segs * WIN, axis=-1)


def band_mean(v, band):
    lo, hi = BANDS[band]
    m = (FREQS >= lo) & (FREQS <= hi)
    return v[..., m].mean(axis=-1)


def epoch_measures(X):
    out = {}
    S = {i: (np.abs(X[i]) ** 2).mean(axis=1) for i in range(4)}
    for a, b in PAIRS:
        cs = (X[IX[a]] * np.conj(X[IX[b]])).mean(axis=1)
        msc = np.abs(cs) ** 2 / (S[IX[a]] * S[IX[b]])
        for band in BANDS:
            out[f"MSC {a}-{b} {band}"] = band_mean(msc, band)
        if (a, b) == ("O1", "O2"):
            coh = cs / np.sqrt(S[0] * S[1])
            im_cs = (X[0] * np.conj(X[1])).imag
            wpli = np.abs(im_cs.mean(axis=1)) / (np.abs(im_cs).mean(axis=1) + 1e-20)
            for band in BANDS:
                lo, hi = BANDS[band]
                m = (FREQS >= lo) & (FREQS <= hi)
                re2, ab2 = (coh.real[..., m] ** 2).mean(-1), (np.abs(coh[..., m]) ** 2).mean(-1)
                out[f"zero-lag share O1-O2 {band}"] = re2 / ab2
                out[f"ImCoh O1-O2 {band}"] = band_mean(np.abs(coh.imag), band)
                out[f"wPLI O1-O2 {band}"] = band_mean(wpli, band)
    return out


def main():
    ds = C.load_dd()
    feats = {}
    for s in C.DD_SUBJECTS:
        for tr in (1, 2):
            raw = mne.io.read_raw_edf(os.path.join(C.DD_DIR, f"{s}_{tr}.edf"), preload=True)
            raw.pick(CH)
            raw.filter(1.0, 40.0, fir_design="firwin")
            d = raw.get_data()
            n = d.shape[1] // C.EPOCH
            x = d[:, :n * C.EPOCH].reshape(4, n, C.EPOCH)
            X = segment_spectra(x)
            meas = epoch_measures(X)
            car = x - x.mean(axis=0, keepdims=True)
            Xc = segment_spectra(car)
            Sc0, Sc1 = (np.abs(Xc[0]) ** 2).mean(1), (np.abs(Xc[1]) ** 2).mean(1)
            msc_car = np.abs((Xc[0] * np.conj(Xc[1])).mean(1)) ** 2 / (Sc0 * Sc1)
            for band in BANDS:
                meas[f"MSC O1-O2 (common-average ref) {band}"] = band_mean(msc_car, band)
            for k, v in meas.items():
                feats.setdefault(k, []).append(v)
        print(f"{s} done", flush=True)
    feats = {k: np.concatenate(v) for k, v in feats.items()}
    assert len(feats["MSC O1-O2 beta"]) == len(ds.y)

    # Consistency with the feature cache (same epochs, same Welch settings).
    check = {b: float(np.max(np.abs(feats[f"MSC O1-O2 {b}"] - ds.X[:, C.LEAN.index(f"coh_{b}")]))) for b in BANDS}
    assert max(check.values()) < 1e-3, check

    lab = ds.y >= 0
    res = {}
    for k, v in feats.items():
        alert, drowsy = [], []
        for s in ds.test_subjects:
            m0, m1 = lab & (ds.subject == s) & (ds.y == 0), lab & (ds.subject == s) & (ds.y == 1)
            alert.append(float(v[m0].mean()))
            drowsy.append(float(v[m1].mean()))
        res[k] = {"mean_all_labelled": float(v[lab].mean()), "alert_mean": float(np.mean(alert)),
                  "drowsy_mean": float(np.mean(drowsy)), "subject_level": C.paired_wilcoxon(alert, drowsy)}
    # Two corrections, both reported: across the three bands of each
    # measure-and-pair (the unit of interpretation), and across all tests.
    families = {}
    for k in res:
        families.setdefault(k.rsplit(" ", 1)[0], []).append(k)
    for fam, ks in families.items():
        for k, a in zip(ks, C.holm([res[k]["subject_level"]["p_two_sided"] for k in ks])):
            res[k]["subject_level"]["p_holm_bands"] = a
    allk = list(res)
    for k, a in zip(allk, C.holm([res[k]["subject_level"]["p_two_sided"] for k in allk])):
        res[k]["subject_level"]["p_holm_all"] = a
    for k in sorted(res):
        t = res[k]["subject_level"]
        print(f"{k:44} mean {res[k]['mean_all_labelled']:.3f}  drowsy-alert {t['mean_diff']:+.4f}  "
              f"up {t['n_increase']}/{t['n']}  p {t['p_two_sided']:.3f}  Holm(bands) {t['p_holm_bands']:.3f}  "
              f"Holm(all {len(allk)}) {t['p_holm_all']:.3f}")
    C.write_result("reference", {"dataset": "DD-Database (original recordings, self-report labels)",
                                 "reference_electrode": "A1 or A2 (per the dataset README); shared by all EEG channels",
                                 "seed_vig_reference": "not reported by the dataset authors (Zheng & Lu 2017)",
                                 "consistency_with_feature_cache_max_abs": check,
                                 "results": res}, __file__)


if __name__ == "__main__":
    main()
