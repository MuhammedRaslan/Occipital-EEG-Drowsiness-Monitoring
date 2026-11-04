"""Coherence at the subject level.

For each subject and band (theta, alpha, beta), the mean O1-O2 magnitude-
squared coherence over drowsy epochs is compared with the mean over alert
epochs: paired Wilcoxon signed-rank across subjects (DD-Database n = 10,
self-report labels; SEED-VIG n = 19, PERCLOS labels), Holm-adjusted over the
six tests. For contrast, the epoch-level Mann-Whitney test that the reviewed
paper used is recomputed on the same data, and the lag-1 autocorrelation of
the features within recordings is reported.

Output: results/coherence_stats.json (incl. per-subject means for Fig. 1)
"""
import os
import sys

import numpy as np
from scipy.stats import mannwhitneyu, norm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BANDS = {"theta": 7, "alpha": 8, "beta": 9}  # columns in the lean-10 matrix


def mw_log10p(a, b):
    """log10 of the two-sided Mann-Whitney p-value from the normal approximation.

    scipy's p-value underflows to 0.0 at these sample sizes; the z statistic does not.
    Ties are ignored, which is immaterial for continuous coherence values.
    """
    u = mannwhitneyu(a, b, alternative="two-sided").statistic
    n1, n2 = len(a), len(b)
    z = (u - n1 * n2 / 2) / np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    return float(z), float((np.log(2) + norm.logsf(abs(z))) / np.log(10))


def lag1(ds, col):
    rs = []
    for r in np.unique(ds.recording):
        idx = np.where(ds.recording == r)[0]
        idx = idx[np.argsort(ds.t[idx])]
        x, t = ds.X[idx, col], ds.t[idx]
        consecutive = np.diff(t) == C.EPOCH_SEC
        if consecutive.sum() < 10:
            continue
        a, b = x[:-1][consecutive], x[1:][consecutive]
        rs.append(np.corrcoef(a, b)[0, 1])
    return float(np.mean(rs)), [float(np.min(rs)), float(np.max(rs))]


def analyse(ds):
    out = {}
    lab = ds.y >= 0
    for band, col in BANDS.items():
        alert, drowsy, subs = [], [], []
        for s in ds.test_subjects:
            m0 = lab & (ds.subject == s) & (ds.y == 0)
            m1 = lab & (ds.subject == s) & (ds.y == 1)
            if m0.sum() < 5 or m1.sum() < 5:
                continue
            alert.append(float(ds.X[m0, col].mean()))
            drowsy.append(float(ds.X[m1, col].mean()))
            subs.append(s)
        test = C.paired_wilcoxon(alert, drowsy)
        a0, a1 = ds.X[lab & (ds.y == 0), col], ds.X[lab & (ds.y == 1), col]
        mw = mannwhitneyu(a0, a1, alternative="two-sided")
        z, log10p = mw_log10p(a0, a1)
        r_mean, r_range = lag1(ds, col)
        out[band] = {"subjects": subs, "alert_mean": alert, "drowsy_mean": drowsy, "subject_level": test,
                     "epoch_level_mannwhitney_p": float(mw.pvalue), "epoch_level_mannwhitney_z": z,
                     "epoch_level_mannwhitney_log10p": log10p, "n_epochs": int(lab.sum()),
                     "lag1_autocorr_mean": r_mean, "lag1_autocorr_range": r_range}
    return out


def main():
    res = {}
    for ds in (C.load_dd(), C.load_seed()):
        res[ds.name] = analyse(ds)
    keys = [(d, b) for d in res for b in BANDS]
    adj = C.holm([res[d][b]["subject_level"]["p_two_sided"] for d, b in keys])
    for (d, b), a in zip(keys, adj):
        res[d][b]["subject_level"]["p_holm"] = a
        t = res[d][b]["subject_level"]
        print(f"{d:12} {b:5}: drowsy-alert mean diff {t['mean_diff']:+.4f}, up {t['n_increase']} / down {t['n_decrease']} "
              f"of {t['n']}, p {t['p_two_sided']:.4f} (Holm {a:.4f}) | epoch-level MW log10 p {res[d][b]['epoch_level_mannwhitney_log10p']:.1f}")
    C.write_result("coherence_stats", {"labels": {"DD-Database": "self-report (button presses)", "SEED-VIG": "PERCLOS"},
                                       "test": "paired Wilcoxon on per-subject means (drowsy vs alert), Holm over 6 tests",
                                       "results": res}, __file__)


if __name__ == "__main__":
    main()
